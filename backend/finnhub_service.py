from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from .data_sources import DEFAULT_ACCOUNT_ID, active_source_ids, finnhub_token
from .db import now_iso, row_to_dict, upsert_financial_metrics_history
from .providers import FinnhubClient, FinnhubError


FINNHUB_MARKET_SOURCE_ID = "us-finnhub-market"
FINNHUB_FINANCIAL_SOURCE_ID = "us-finnhub-financial"
FINNHUB_NEWS_SOURCE_ID = "us-finnhub-news"
FINNHUB_HK_MARKET_SOURCE_ID = "hk-finnhub-market"
FINNHUB_HK_FINANCIAL_SOURCE_ID = "hk-finnhub-financial"
FINNHUB_PROVIDER_MARKET = "finnhub-market"
FINNHUB_PROVIDER_FINANCIAL = "finnhub-financial"
FINNHUB_PROVIDER_NEWS = "finnhub-news"
USD_TO_CNY = 7.2
HKD_TO_CNY = 0.92


def finnhub_status(conn: sqlite3.Connection, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    source_ids = active_source_ids(conn, account_id)
    token_configured = bool(finnhub_token(conn, account_id))
    return {
        "provider": "finnhub",
        "account_id": account_id,
        "token_configured": token_configured,
        "market_active": bool({FINNHUB_MARKET_SOURCE_ID, FINNHUB_HK_MARKET_SOURCE_ID} & source_ids),
        "financial_active": bool({FINNHUB_FINANCIAL_SOURCE_ID, FINNHUB_HK_FINANCIAL_SOURCE_ID} & source_ids),
        "news_active": FINNHUB_NEWS_SOURCE_ID in source_ids,
        "active_sources": sorted(source_ids & {
            FINNHUB_MARKET_SOURCE_ID,
            FINNHUB_FINANCIAL_SOURCE_ID,
            FINNHUB_NEWS_SOURCE_ID,
            FINNHUB_HK_MARKET_SOURCE_ID,
            FINNHUB_HK_FINANCIAL_SOURCE_ID,
        }),
        "latest_market": latest_snapshot_meta(conn, "market_snapshots", FINNHUB_PROVIDER_MARKET),
        "latest_financial": latest_financial_metrics_meta(conn, FINNHUB_PROVIDER_FINANCIAL),
        "latest_news": latest_news_meta(conn),
    }


def refresh_finnhub_data(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    account_id: str = DEFAULT_ACCOUNT_ID,
) -> dict[str, Any]:
    source_ids = active_source_ids(conn, account_id)
    market_active = bool({FINNHUB_MARKET_SOURCE_ID, FINNHUB_HK_MARKET_SOURCE_ID} & source_ids)
    financial_active = bool({FINNHUB_FINANCIAL_SOURCE_ID, FINNHUB_HK_FINANCIAL_SOURCE_ID} & source_ids)
    news_active = FINNHUB_NEWS_SOURCE_ID in source_ids
    if not market_active and not financial_active and not news_active:
        raise HTTPException(status_code=400, detail="Finnhub 数据源未启用")

    token = finnhub_token(conn, account_id)
    if not token:
        raise HTTPException(status_code=400, detail="Finnhub key 未配置")

    target_symbols = normalize_symbols(symbols) if symbols else existing_finnhub_symbols(
        conn,
        include_us=bool({FINNHUB_MARKET_SOURCE_ID, FINNHUB_FINANCIAL_SOURCE_ID, FINNHUB_NEWS_SOURCE_ID} & source_ids),
        include_hk=bool({FINNHUB_HK_MARKET_SOURCE_ID, FINNHUB_HK_FINANCIAL_SOURCE_ID} & source_ids),
    )
    if not target_symbols:
        raise HTTPException(status_code=400, detail="没有可刷新的美股/港股股票代码")

    client = FinnhubClient(token)
    errors: list[dict[str, str]] = []
    updated_symbols: list[str] = []
    market_count = 0
    financial_count = 0
    news_count = 0

    for symbol in target_symbols:
        try:
            profile = client.company_profile(symbol) if financial_active or market_active else {}
            metrics_payload = client.basic_financials(symbol) if financial_active or market_active else {}
            upsert_finnhub_symbol(conn, symbol, profile)

            if market_active:
                quote = client.quote(symbol)
                insert_market_snapshot(conn, symbol, quote, metrics_payload, profile)
                market_count += 1

            if financial_active:
                insert_financial_snapshot(conn, symbol, metrics_payload, profile)
                financial_count += 1

            if news_active:
                to_date = date.today()
                from_date = to_date - timedelta(days=7)
                news_rows = client.company_news(symbol, from_date, to_date)
                news_count += insert_news_items(conn, symbol, news_rows)

            updated_symbols.append(symbol)
        except FinnhubError as exc:
            errors.append({"symbol": symbol, "error": str(exc)})
        except ValueError as exc:
            errors.append({"symbol": symbol, "error": str(exc)})

    conn.commit()
    return {
        "status": "ok" if updated_symbols else "partial",
        "mode": "finnhub",
        "account_id": account_id,
        "refreshed_at": now_iso(),
        "symbols": updated_symbols,
        "requested_symbols": target_symbols,
        "counts": {
            "market_snapshots": market_count,
            "financial_snapshots": financial_count,
            "financial_metrics_history": financial_count,
            "news_items": news_count,
            "errors": len(errors),
        },
        "errors": errors,
        "status_detail": finnhub_status(conn, account_id),
    }


def existing_finnhub_symbols(conn: sqlite3.Connection, include_us: bool = True, include_hk: bool = True) -> list[str]:
    markets = []
    if include_us:
        markets.append("US")
    if include_hk:
        markets.append("HK")
    if not markets:
        return []
    placeholders = ", ".join("?" for _ in markets)
    return [
        normalize_finnhub_symbol(row["symbol"])
        for row in conn.execute(
            f"""
            select symbol
            from symbols
            where market in ({placeholders})
            order by symbol
            """,
            markets,
        )
    ]


def normalize_symbols(symbols: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in symbols:
        symbol = normalize_finnhub_symbol(item)
        if not symbol or symbol.endswith((".SH", ".SZ", ".BJ")):
            continue
        if symbol not in seen:
            seen.add(symbol)
            normalized.append(symbol)
    return normalized


def normalize_finnhub_symbol(value: Any) -> str:
    symbol = str(value or "").strip().upper().replace(" ", "")
    if symbol.endswith(".HK"):
        code = symbol[:-3]
        if code.isdigit():
            code = (code.lstrip("0") or "0").zfill(4)
        return f"{code}.HK"
    return symbol


def upsert_finnhub_symbol(conn: sqlite3.Connection, symbol: str, profile: dict[str, Any]) -> None:
    market = "HK" if symbol.endswith(".HK") else "US"
    name = str(profile.get("name") or symbol)
    currency = str(profile.get("currency") or ("HKD" if market == "HK" else "USD"))
    exchange = str(profile.get("exchange") or ("HKEX" if market == "HK" else "US"))
    industry = str(profile.get("finnhubIndustry") or "未分类")
    conn.execute(
        """
        insert into symbols (symbol, market, name, currency, exchange, sector, industry)
        values (?, ?, ?, ?, ?, ?, ?)
        on conflict(symbol) do update set
          market = excluded.market,
          name = excluded.name,
          currency = excluded.currency,
          exchange = excluded.exchange,
          sector = excluded.sector,
          industry = excluded.industry
        """,
        (symbol, market, name, currency, exchange, "港股" if market == "HK" else "美股", industry),
    )


def insert_market_snapshot(
    conn: sqlite3.Connection,
    symbol: str,
    quote: dict[str, Any],
    metrics_payload: dict[str, Any],
    profile: dict[str, Any],
) -> None:
    price = float_value(quote.get("c"), 0)
    if price <= 0:
        raise ValueError("Finnhub quote 无有效现价")

    metrics = metrics_payload.get("metric") if isinstance(metrics_payload.get("metric"), dict) else {}
    avg_volume = average_volume(metrics)
    share_count = share_count_from_profile(profile)
    amount_usd = avg_volume * price
    turnover_rate = (avg_volume / share_count * 100) if share_count else 0
    as_of = finnhub_timestamp_as_of(quote.get("t"))
    currency = str(profile.get("currency") or ("HKD" if symbol.endswith(".HK") else "USD")).upper()
    amount_cny = amount_usd * currency_to_cny(currency)
    raw_json = {
        "quote": quote,
        "metric": metrics,
        "profile": compact_profile(profile),
        "currency": currency,
        "change": float_value(quote.get("dp"), 0),
        "price_change": float_value(quote.get("d"), 0),
        "previous_close": float_value(quote.get("pc"), 0),
        "volume_ratio": 1,
        "pe": first_number(metrics, ["peTTM", "peNormalizedAnnual", "peBasicExclExtraTTM"], 0),
        "pb": first_number(metrics, ["pbAnnual", "pbQuarterly"], 0),
    }
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
            FINNHUB_PROVIDER_MARKET,
            as_of,
            now_iso(),
            price,
            avg_volume,
            amount_cny,
            turnover_rate,
            5,
            json.dumps(raw_json, ensure_ascii=False),
            freshness_for_as_of(as_of),
        ),
    )


def insert_financial_snapshot(
    conn: sqlite3.Connection,
    symbol: str,
    metrics_payload: dict[str, Any],
    profile: dict[str, Any],
) -> None:
    metrics = metrics_payload.get("metric") if isinstance(metrics_payload.get("metric"), dict) else {}
    period = date.today().isoformat()
    revenue_growth = optional_number(metrics, ["revenueGrowthTTMYoy", "revenueGrowthQuarterlyYoy", "revenueGrowth5Y"])
    roe = optional_number(metrics, ["roeTTM", "roeRfy", "roeAnnual"])
    fcf_margin = optional_number(metrics, ["fcfMarginTTM", "fcfMarginAnnual"])
    debt_ratio = optional_number(metrics, ["totalDebt/totalAssetsAnnual", "totalDebt/totalAssetsQuarterly", "totalDebt/totalEquityAnnual"])
    raw_json = {"metric": metrics, "series": metrics_payload.get("series") or {}, "profile": compact_profile(profile)}
    conn.execute(
        """
        insert into financial_snapshots (
          symbol, period, provider, revenue_growth, roe, fcf_margin, debt_ratio, pe, pb, raw_json
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            symbol,
            period,
            FINNHUB_PROVIDER_FINANCIAL,
            number_or_zero(revenue_growth),
            number_or_zero(roe),
            number_or_zero(fcf_margin),
            number_or_zero(debt_ratio),
            first_number(metrics, ["peTTM", "peNormalizedAnnual", "peBasicExclExtraTTM"], 0),
            first_number(metrics, ["pbAnnual", "pbQuarterly"], 0),
            json.dumps(raw_json, ensure_ascii=False),
        ),
    )
    upsert_financial_metrics_history(
        conn,
        {
            "symbol": symbol,
            "report_period": period,
            "provider": FINNHUB_PROVIDER_FINANCIAL,
            "announce_date": "",
            "revenue_growth": revenue_growth,
            "roe": roe,
            "fcf_margin": fcf_margin,
            "debt_ratio": debt_ratio,
            "gross_margin": optional_number(metrics, ["grossMarginTTM", "grossMarginAnnual"]),
            "net_margin": optional_number(metrics, ["netProfitMarginTTM", "netProfitMarginAnnual"]),
            "raw_json": raw_json,
        },
    )


def insert_news_items(conn: sqlite3.Connection, symbol: str, rows: list[dict[str, Any]]) -> int:
    inserted = 0
    for row in rows[:8]:
        title = str(row.get("headline") or "").strip()
        if not title:
            continue
        published_at = finnhub_timestamp_as_of(row.get("datetime"))
        summary = str(row.get("summary") or title).strip()
        url = str(row.get("url") or "")
        publisher = str(row.get("source") or "")
        conn.execute(
            """
            insert into news_items (
              symbol, source, source_tier, title, url, published_at, summary, sentiment_score, raw_text_hash
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                FINNHUB_PROVIDER_NEWS,
                "B",
                title,
                url,
                published_at,
                summary,
                0,
                stable_hash({"symbol": symbol, "title": title, "published_at": published_at}),
            ),
        )
        conn.execute(
            """
            insert into claims (
              symbol, claim_text, claim_type, source_tier, source, source_url,
              confidence, truth_status, raw_json, created_at
            )
            values (?, ?, 'news', 'B', ?, ?, 0.64, 'needs_review', ?, ?)
            """,
            (
                symbol,
                title,
                FINNHUB_PROVIDER_NEWS,
                url,
                json.dumps({"provider": FINNHUB_PROVIDER_NEWS, "publisher": publisher, "news": row}, ensure_ascii=False),
                now_iso(),
            ),
        )
        inserted += 1
    return inserted


def latest_snapshot_meta(conn: sqlite3.Connection, table: str, provider: str) -> dict[str, Any] | None:
    if table == "financial_snapshots":
        row = conn.execute(
            """
            select provider, max(period) as period, count(*) as count
            from financial_snapshots
            where provider = ?
            """,
            (provider,),
        ).fetchone()
        if not row or not row["count"]:
            return None
        return row_to_dict(row)

    row = conn.execute(
        f"""
        select provider, max(fetched_at) as fetched_at, count(*) as count
        from {table}
        where provider = ?
        """,
        (provider,),
    ).fetchone()
    if not row or not row["count"]:
        return None
    return row_to_dict(row)


def latest_financial_metrics_meta(conn: sqlite3.Connection, provider: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        select provider, max(report_period) as period, count(*) as count
        from financial_metrics_history
        where provider = ?
        """,
        (provider,),
    ).fetchone()
    if not row or not row["count"]:
        return None
    return row_to_dict(row)


def latest_news_meta(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        """
        select source as provider, max(published_at) as latest_published_at, count(*) as count
        from news_items
        where source = ?
        """,
        (FINNHUB_PROVIDER_NEWS,),
    ).fetchone()
    if not row or not row["count"]:
        return None
    return row_to_dict(row)


def compact_profile(profile: dict[str, Any]) -> dict[str, Any]:
    keys = ["name", "ticker", "exchange", "currency", "country", "finnhubIndustry", "marketCapitalization", "shareOutstanding"]
    return {key: profile.get(key) for key in keys if profile.get(key) not in (None, "")}


def average_volume(metrics: dict[str, Any]) -> float:
    value = first_number(metrics, ["10DayAverageTradingVolume", "3MonthAverageTradingVolume"], 0)
    if value <= 0:
        return 0
    return value * 1_000_000 if value < 1_000_000 else value


def share_count_from_profile(profile: dict[str, Any]) -> float:
    value = float_value(profile.get("shareOutstanding"), 0)
    if value <= 0:
        return 0
    return value * 1_000_000 if value < 1_000_000 else value


def currency_to_cny(currency: str) -> float:
    if currency.upper() == "HKD":
        return HKD_TO_CNY
    return USD_TO_CNY


def optional_number(row: dict[str, Any] | None, keys: list[str]) -> float | None:
    if not row:
        return None
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return float_value(value, 0)
    return None


def number_or_zero(value: float | None) -> float:
    return 0 if value is None else value


def first_number(row: dict[str, Any] | None, keys: list[str], default: float = 0) -> float:
    if not row:
        return default
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return float_value(value, default)
    return default


def float_value(value: Any, default: float) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def finnhub_timestamp_as_of(value: Any) -> str:
    timestamp = float_value(value, 0)
    if timestamp <= 0:
        return now_iso()
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds")


def freshness_for_as_of(as_of: str) -> str:
    try:
        parsed = datetime.fromisoformat(as_of)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
    except ValueError:
        return "warn"
    age_minutes = (datetime.now() - parsed).total_seconds() / 60
    if age_minutes <= 24 * 60:
        return "fresh"
    if age_minutes <= 7 * 24 * 60:
        return "warn"
    return "stale"


def stable_hash(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
