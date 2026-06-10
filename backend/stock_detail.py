from __future__ import annotations

import json
import re
import sqlite3
from collections import OrderedDict
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException

from .db import row_to_dict
from .symbol_resolver import resolve_symbol


MARKET_PROVIDER_PRIORITY = {
    "tushare-market": 5,
    "akshare-market": 4,
    "baostock-market": 3,
    "finnhub-market": 2,
    "mock-market": 1,
}

FINANCIAL_PROVIDER_PRIORITY = {
    "baostock-financial": 5,
    "tushare-financial": 4,
    "finnhub-financial": 3,
    "mock-financial": 1,
}


def stock_detail_payload(
    conn: sqlite3.Connection,
    symbol: str,
    market: str = "all",
    limit: int = 520,
) -> dict[str, Any]:
    symbol_row = resolve_symbol(conn, symbol, market)
    if not symbol_row:
        raise HTTPException(status_code=404, detail="symbol not found")

    normalized = str(symbol_row["symbol"]).upper()
    daily_bars = preferred_daily_bars(conn, normalized, limit=limit)
    financials = financial_history(conn, normalized, limit=12)
    latest_financial = financials[0] if financials else None
    periods = {
        "daily": period_payload("daily", "日K", daily_bars),
        "weekly": period_payload("weekly", "周K", aggregate_bars(daily_bars, "weekly")),
        "monthly": period_payload("monthly", "月K", aggregate_bars(daily_bars, "monthly")),
        "quarterly": period_payload("quarterly", "季K", aggregate_bars(daily_bars, "quarterly")),
    }

    latest_bar = daily_bars[-1] if daily_bars else None
    previous_bar = daily_bars[-2] if len(daily_bars) > 1 else None
    return {
        "mode": "warehouse-stock-detail",
        "symbol": public_symbol(symbol_row),
        "summary": detail_summary(symbol_row, latest_bar, previous_bar, daily_bars, latest_financial),
        "market_data": {
            "source": "daily_bars",
            "preferred_adjust": latest_bar.get("adjust") if latest_bar else None,
            "latest_provider": latest_bar.get("provider") if latest_bar else None,
            "latest_trade_date": latest_bar.get("date") if latest_bar else None,
            "periods": periods,
        },
        "financials": {
            "source": "financial_metrics_history",
            "latest": latest_financial,
            "quarters": financials,
        },
        "data_status": {
            "has_daily_bars": bool(daily_bars),
            "has_financials": bool(financials),
            "daily_rows": len(daily_bars),
            "financial_rows": len(financials),
        },
    }


def preferred_daily_bars(conn: sqlite3.Connection, symbol: str, limit: int = 520) -> list[dict[str, Any]]:
    clean_limit = max(20, min(int(limit or 520), 1200))
    rows = select_preferred_daily_bars(conn, symbol, clean_limit, include_mock=False)
    if not rows:
        rows = select_preferred_daily_bars(conn, symbol, clean_limit, include_mock=True)
    return [normalize_daily_bar(row) for row in reversed(rows)]


def select_preferred_daily_bars(
    conn: sqlite3.Connection,
    symbol: str,
    limit: int,
    include_mock: bool,
) -> list[sqlite3.Row]:
    provider_filter = "" if include_mock else "and provider != 'mock-market'"
    return conn.execute(
        f"""
        with ranked_daily as (
          select
            *,
            row_number() over (
              partition by trade_date
              order by
                case lower(coalesce(adjust, ''))
                  when 'qfq' then 5
                  when 'hfq' then 4
                  when '' then 3
                  else 2
                end desc,
                case provider
                  when 'tushare-market' then 5
                  when 'akshare-market' then 4
                  when 'baostock-market' then 3
                  when 'finnhub-market' then 2
                  when 'mock-market' then 1
                  else 0
                end desc,
                fetched_at desc
            ) as rn
          from daily_bars
          where upper(symbol) = upper(?)
            {provider_filter}
        )
        select *
        from ranked_daily
        where rn = 1
        order by trade_date desc
        limit ?
        """,
        (symbol, limit),
    ).fetchall()


def normalize_daily_bar(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    close = number(item.get("close"))
    open_price = number(item.get("open"), close)
    high = number(item.get("high"), max_value(open_price, close))
    low = number(item.get("low"), min_value(open_price, close))
    pre_close = number(item.get("pre_close"))
    change_pct = number(item.get("change_pct"))
    if change_pct is None and pre_close not in (None, 0) and close is not None:
        change_pct = (close / pre_close - 1) * 100
    return {
        "date": item["trade_date"],
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "pre_close": pre_close,
        "change_pct": change_pct,
        "volume": number(item.get("volume")),
        "amount": number(item.get("amount")),
        "turnover_rate": number(item.get("turnover_rate")),
        "pe_ttm": number(item.get("pe_ttm")),
        "pb": number(item.get("pb")),
        "ps_ttm": number(item.get("ps_ttm")),
        "pcf_ncf_ttm": number(item.get("pcf_ncf_ttm")),
        "provider": item.get("provider"),
        "adjust": item.get("adjust") or "",
        "fetched_at": item.get("fetched_at"),
    }


def aggregate_bars(bars: list[dict[str, Any]], period: str) -> list[dict[str, Any]]:
    groups: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for bar in bars:
        key = bar_period_key(bar["date"], period)
        groups.setdefault(key, []).append(bar)

    aggregated: list[dict[str, Any]] = []
    previous_close: float | None = None
    for key, items in groups.items():
        first = items[0]
        last = items[-1]
        close = number(last.get("close"))
        pre_close = number(first.get("pre_close"), previous_close)
        change_pct = None
        if pre_close not in (None, 0) and close is not None:
            change_pct = (close / pre_close - 1) * 100
        aggregated.append(
            {
                "date": last["date"],
                "start_date": first["date"],
                "period": key,
                "open": first.get("open"),
                "high": max(clean_numbers(item.get("high") for item in items), default=last.get("high")),
                "low": min(clean_numbers(item.get("low") for item in items), default=last.get("low")),
                "close": close,
                "pre_close": pre_close,
                "change_pct": change_pct,
                "volume": sum(clean_numbers(item.get("volume") for item in items)),
                "amount": sum(clean_numbers(item.get("amount") for item in items)),
                "turnover_rate": sum(clean_numbers(item.get("turnover_rate") for item in items)) or None,
                "pe_ttm": last.get("pe_ttm"),
                "pb": last.get("pb"),
                "ps_ttm": last.get("ps_ttm"),
                "pcf_ncf_ttm": last.get("pcf_ncf_ttm"),
                "provider": last.get("provider"),
                "adjust": last.get("adjust") or "",
                "fetched_at": last.get("fetched_at"),
            }
        )
        previous_close = close
    return aggregated


def bar_period_key(value: str, period: str) -> str:
    parsed = parse_date(value)
    if not parsed:
        return value
    if period == "weekly":
        iso_year, iso_week, _ = parsed.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    if period == "monthly":
        return parsed.strftime("%Y-%m")
    if period == "quarterly":
        quarter = (parsed.month - 1) // 3 + 1
        return f"{parsed.year}Q{quarter}"
    return value


def period_payload(period: str, label: str, bars: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "period": period,
        "label": label,
        "rows": len(bars),
        "bars": bars,
    }


def financial_history(conn: sqlite3.Connection, symbol: str, limit: int = 12) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select *
        from financial_metrics_history
        where upper(symbol) = upper(?)
        order by fetched_at desc
        limit 80
        """,
        (symbol,),
    ).fetchall()
    items = [normalize_financial_row(row) for row in rows]
    usable = [item for item in items if item["status"] != "no_data"]
    if not usable:
        usable = items
    usable.sort(
        key=lambda item: (
            item["period_sort"] or "",
            FINANCIAL_PROVIDER_PRIORITY.get(str(item["provider"]), 0),
            item.get("fetched_at") or "",
        ),
        reverse=True,
    )
    deduped: dict[str, dict[str, Any]] = {}
    for item in usable:
        key = item["period_sort"] or item["report_period"]
        deduped.setdefault(key, item)
    return list(deduped.values())[: max(1, min(limit, 24))]


def normalize_financial_row(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    raw = parse_json(item.get("raw_json"))
    period_sort = normalize_financial_period(item.get("report_period"))
    status = str(raw.get("status") or "ok")
    return {
        "symbol": item.get("symbol"),
        "report_period": item.get("report_period"),
        "period": period_sort or item.get("report_period"),
        "provider": item.get("provider"),
        "announce_date": item.get("announce_date"),
        "status": status,
        "revenue_growth": number(item.get("revenue_growth")),
        "roe": percentish(item.get("roe")),
        "fcf_margin": percentish(item.get("fcf_margin")),
        "debt_ratio": percentish(item.get("debt_ratio") if item.get("debt_ratio") is not None else item.get("liability_to_asset")),
        "gross_margin": percentish(item.get("gross_margin")),
        "net_margin": percentish(item.get("net_margin")),
        "net_profit": number(item.get("net_profit")),
        "eps_ttm": number(item.get("eps_ttm")),
        "mb_revenue": number(item.get("mb_revenue")),
        "total_share": number(item.get("total_share")),
        "liqa_share": number(item.get("liqa_share")),
        "current_ratio": number(item.get("current_ratio")),
        "quick_ratio": number(item.get("quick_ratio")),
        "cash_ratio": number(item.get("cash_ratio")),
        "asset_to_equity": number(item.get("asset_to_equity")),
        "asset_turn_ratio": number(item.get("asset_turn_ratio")),
        "operating_cash_flow_to_asset": percentish(item.get("operating_cash_flow_to_asset")),
        "period_sort": period_sort,
        "fetched_at": item.get("fetched_at"),
    }


def detail_summary(
    symbol_row: dict[str, Any],
    latest_bar: dict[str, Any] | None,
    previous_bar: dict[str, Any] | None,
    bars: list[dict[str, Any]],
    latest_financial: dict[str, Any] | None,
) -> dict[str, Any]:
    price = latest_bar.get("close") if latest_bar else None
    pre_close = latest_bar.get("pre_close") if latest_bar else None
    if pre_close is None and previous_bar:
        pre_close = previous_bar.get("close")
    change = None
    if price is not None and pre_close is not None:
        change = price - pre_close
    change_pct = latest_bar.get("change_pct") if latest_bar else None
    if change_pct is None and price is not None and pre_close not in (None, 0):
        change_pct = (price / pre_close - 1) * 100

    total_share = latest_financial.get("total_share") if latest_financial else None
    float_share = latest_financial.get("liqa_share") if latest_financial else None
    return {
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "open": latest_bar.get("open") if latest_bar else None,
        "high": latest_bar.get("high") if latest_bar else None,
        "low": latest_bar.get("low") if latest_bar else None,
        "pre_close": pre_close,
        "volume": latest_bar.get("volume") if latest_bar else None,
        "amount": latest_bar.get("amount") if latest_bar else None,
        "turnover_rate": latest_bar.get("turnover_rate") if latest_bar else None,
        "pe_ttm": latest_bar.get("pe_ttm") if latest_bar else None,
        "pb": latest_bar.get("pb") if latest_bar else None,
        "ps_ttm": latest_bar.get("ps_ttm") if latest_bar else None,
        "pcf_ncf_ttm": latest_bar.get("pcf_ncf_ttm") if latest_bar else None,
        "eps_ttm": latest_financial.get("eps_ttm") if latest_financial else None,
        "roe": latest_financial.get("roe") if latest_financial else None,
        "gross_margin": latest_financial.get("gross_margin") if latest_financial else None,
        "net_margin": latest_financial.get("net_margin") if latest_financial else None,
        "debt_ratio": latest_financial.get("debt_ratio") if latest_financial else None,
        "total_share": total_share,
        "float_share": float_share,
        "market_cap": price * total_share if price is not None and total_share else None,
        "float_market_cap": price * float_share if price is not None and float_share else None,
        "high_52w": max(clean_numbers(bar.get("high") for bar in bars[-252:]), default=None),
        "low_52w": min(clean_numbers(bar.get("low") for bar in bars[-252:]), default=None),
        "latest_trade_date": latest_bar.get("date") if latest_bar else None,
        "latest_financial_period": latest_financial.get("period") if latest_financial else None,
        "currency": symbol_row.get("currency") or "CNY",
    }


def public_symbol(symbol_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": symbol_row.get("symbol"),
        "name": symbol_row.get("name"),
        "market": symbol_row.get("market"),
        "currency": symbol_row.get("currency"),
        "exchange": symbol_row.get("exchange"),
        "sector": symbol_row.get("sector"),
        "industry": symbol_row.get("industry"),
    }


def normalize_financial_period(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    date_match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if date_match:
        return "-".join(date_match.groups())
    compact_match = re.search(r"(\d{4})(\d{2})(\d{2})", text)
    if compact_match:
        year, month, day = compact_match.groups()
        return f"{year}-{month}-{day}"
    quarter_match = re.search(r"(\d{4})\s*[Qq]\s*([1-4])", text)
    if quarter_match:
        year = int(quarter_match.group(1))
        quarter = int(quarter_match.group(2))
        month = quarter * 3
        day = {3: 31, 6: 30, 9: 30, 12: 31}[month]
        return date(year, month, day).isoformat()
    return text


def parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_json(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def number(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed


def percentish(value: Any) -> float | None:
    parsed = number(value)
    if parsed is None:
        return None
    if -1 <= parsed <= 1:
        return parsed * 100
    return parsed


def clean_numbers(values: Any) -> list[float]:
    result = []
    for value in values:
        parsed = number(value)
        if parsed is not None:
            result.append(parsed)
    return result


def max_value(*values: float | None) -> float | None:
    items = [value for value in values if value is not None]
    return max(items) if items else None


def min_value(*values: float | None) -> float | None:
    items = [value for value in values if value is not None]
    return min(items) if items else None
