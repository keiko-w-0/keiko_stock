from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from .db import now_iso
from .history import AKSHARE_MARKET_PROVIDER, fetch_akshare_hist, is_a_share, upsert_latest_history_snapshot
from .providers.xueqiu import fetch_xueqiu_quote, xueqiu_quote_configured


def fetch_live_market_quote(symbol: str) -> dict[str, Any] | None:
    normalized = str(symbol or "").upper()
    if not is_a_share(normalized):
        return None

    if xueqiu_quote_configured():
        quote = fetch_xueqiu_quote(normalized)
        if quote:
            return quote

    end = date.today()
    start = end - timedelta(days=10)
    try:
        rows = fetch_akshare_hist(
            normalized,
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d"),
        )
    except Exception:
        return None
    if not rows:
        return None
    last = rows[-1]
    trade_date = str(last.get("date") or last.get("日期") or "")[:10]
    close = _number(last.get("close") or last.get("收盘"))
    if close is None:
        return None
    pre_close = _number(last.get("pre_close") or last.get("昨收"))
    change_pct = _number(last.get("change_pct") or last.get("涨跌幅"))
    if change_pct is None and pre_close not in (None, 0):
        change_pct = round((close / pre_close - 1) * 100, 4)
    return {
        "symbol": normalized,
        "name": "",
        "current_price": round(float(close), 4),
        "change_pct": change_pct,
        "currency": "CNY",
        "market_status": "",
        "price_source": AKSHARE_MARKET_PROVIDER,
        "price_as_of": trade_date,
        "fetched_at": now_iso(),
    }


def persist_live_quote_snapshot(conn: sqlite3.Connection, symbol: str, quote: dict[str, Any]) -> int:
    if not quote or quote.get("current_price") is None:
        return 0
    trade_date = str(quote.get("price_as_of") or date.today().isoformat())[:10]
    price = float(quote["current_price"])
    source = str(quote.get("price_source") or "live-quote")
    if source == AKSHARE_MARKET_PROVIDER:
        upsert_latest_history_snapshot(
            conn,
            symbol,
            {
                "date": trade_date,
                "close": price,
                "涨跌幅": quote.get("change_pct"),
            },
        )
        return 1
    conn.execute(
        """
        insert into market_snapshots (
          symbol, provider, as_of, fetched_at, price, volume, amount, turnover_rate,
          spread_bps, raw_json, freshness_status
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            symbol,
            source,
            f"{trade_date}T15:00:00+08:00",
            quote.get("fetched_at") or now_iso(),
            price,
            0,
            0,
            0,
            5,
            "{}",
            "fresh",
        ),
    )
    return 1


def apply_live_quote_to_summary(summary: dict[str, Any], quote: dict[str, Any]) -> dict[str, Any]:
    if not quote or quote.get("current_price") is None:
        return summary
    price = float(quote["current_price"])
    pre_close = summary.get("pre_close")
    change = summary.get("change")
    change_pct = quote.get("change_pct")
    if change_pct is None and pre_close not in (None, 0):
        change_pct = round((price / float(pre_close) - 1) * 100, 4)
    if change is None and pre_close is not None:
        change = round(price - float(pre_close), 4)
    patched = dict(summary)
    patched["price"] = price
    patched["change"] = change
    patched["change_pct"] = change_pct
    if quote.get("price_as_of"):
        patched["latest_trade_date"] = str(quote["price_as_of"])[:10]
    if quote.get("name"):
        patched["name"] = quote["name"]
    total_share = patched.get("total_share")
    float_share = patched.get("float_share")
    if total_share:
        patched["market_cap"] = price * float(total_share)
    if float_share:
        patched["float_market_cap"] = price * float(float_share)
    return patched


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
