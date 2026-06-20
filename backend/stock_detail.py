from __future__ import annotations

import json
import re
import sqlite3
import time
from collections import OrderedDict
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException

from .db import row_to_dict
from .live_quote import apply_live_quote_to_summary, fetch_live_market_quote
from .market_calendar import evaluate_market_quote_refresh, latest_db_trade_date
from .symbol_resolver import resolve_symbol


MARKET_PROVIDER_PRIORITY = {
    "tushare-market": 6,
    "baostock-market": 5,
    "akshare-market": 4,
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
    total_started = time.monotonic()
    timings: list[dict[str, Any]] = []
    symbol_row = resolve_symbol(conn, symbol, market)
    if not symbol_row:
        raise HTTPException(status_code=404, detail="symbol not found")

    normalized = str(symbol_row["symbol"]).upper()
    started = time.monotonic()
    daily_bars = preferred_daily_bars(conn, normalized, symbol_row, limit=limit)
    timings.append(detail_timing("daily_bars_sql", started, {"rows": len(daily_bars)}))
    started = time.monotonic()
    financials = financial_history(conn, normalized, limit=12)
    timings.append(detail_timing("financials_sql", started, {"rows": len(financials)}))
    latest_financial = financials[0] if financials else None
    started = time.monotonic()
    periods = {
        "daily": period_payload("daily", "日K", daily_bars),
        "weekly": period_payload("weekly", "周K", aggregate_bars(daily_bars, "weekly")),
        "monthly": period_payload("monthly", "月K", aggregate_bars(daily_bars, "monthly")),
        "quarterly": period_payload("quarterly", "季K", aggregate_bars(daily_bars, "quarterly")),
    }
    timings.append(detail_timing("periods_build", started, {"daily_rows": len(daily_bars)}))

    latest_bar = daily_bars[-1] if daily_bars else None
    previous_bar = daily_bars[-2] if len(daily_bars) > 1 else None
    started = time.monotonic()
    information = stock_information(conn, normalized)
    timings.append(
        detail_timing(
            "information_sql",
            started,
            {
                "filings": len(information["filings"]),
                "news": len(information["news"]),
                "discussions": len(information["discussions"]),
            },
        )
    )
    summary = detail_summary(symbol_row, latest_bar, previous_bar, daily_bars, latest_financial)
    quote_plan = maybe_refresh_live_quote(conn, normalized, symbol_row, summary)
    if quote_plan.get("quote"):
        summary = apply_live_quote_to_summary(summary, quote_plan["quote"])
    return {
        "mode": "warehouse-stock-detail",
        "symbol": public_symbol(symbol_row),
        "summary": summary,
        "market_data": {
            "source": "daily_bars",
            "preferred_adjust": latest_bar.get("adjust") if latest_bar else None,
            "latest_provider": quote_plan.get("quote_provider") or (latest_bar.get("provider") if latest_bar else None),
            "latest_trade_date": summary.get("latest_trade_date") or (latest_bar.get("date") if latest_bar else None),
            "quote_refresh": quote_plan,
            "periods": periods,
        },
        "financials": {
            "source": "financial_metrics_history",
            "latest": latest_financial,
            "quarters": financials,
        },
        "information": information,
        "data_status": {
            "has_daily_bars": bool(daily_bars),
            "has_financials": bool(financials),
            "has_filings": bool(information["filings"]),
            "has_news": bool(information["news"]),
            "has_discussions": bool(information["discussions"]),
            "has_sentiment": bool(information["sentiment"]),
            "daily_rows": len(daily_bars),
            "financial_rows": len(financials),
            "filing_rows": len(information["filings"]),
            "news_rows": len(information["news"]),
            "discussion_rows": len(information["discussions"]),
        },
        "performance": {
            "total_sql_ms": detail_elapsed_ms(total_started),
            "steps": timings,
        },
    }


def detail_timing(step: str, started: float, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"step": step, "duration_ms": detail_elapsed_ms(started), **(extra or {})}


def detail_elapsed_ms(started: float) -> int:
    return int(round((time.monotonic() - started) * 1000))


def maybe_refresh_live_quote(
    conn: sqlite3.Connection,
    symbol: str,
    symbol_row: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    if not is_a_share_symbol(symbol):
        return {"action": "skip", "reason": "live quote only applies to A-share detail", "quote": None, "quote_provider": None}

    db_latest = latest_db_trade_date(conn, symbol) or summary.get("latest_trade_date")
    plan = evaluate_market_quote_refresh(str(db_latest or "") or None)
    if plan["action"] == "skip":
        return {
            **plan,
            "quote": None,
            "quote_provider": None,
        }

    quote = fetch_live_market_quote(symbol)
    if quote and not quote.get("name"):
        quote["name"] = str(symbol_row.get("name") or "")
    return {
        **plan,
        "quote": quote,
        "quote_provider": (quote or {}).get("price_source"),
        "quote_error": None if quote else "live quote fetch failed",
    }


def is_a_share_symbol(symbol: str) -> bool:
    text = str(symbol or "").upper()
    return text.endswith((".SH", ".SZ", ".BJ"))


def stock_information(conn: sqlite3.Connection, symbol: str) -> dict[str, Any]:
    from .sentiment import apply_current_community_snapshot, resolve_sentiment_snapshot_row

    filings = [
        {
            "type": "filing",
            "title": row["title"],
            "source": row["source"],
            "published_at": row["published_at"],
            "url": row["url"],
            "category": row["category"],
            "summary": "",
        }
        for row in conn.execute(
            """
            select title, source, published_at, url, category
            from filings_history
            where symbol = ?
            order by published_at desc, id desc
            limit 20
            """,
            (symbol,),
        ).fetchall()
    ]
    reports = [
        {
            "type": "company_report",
            "title": row["title"],
            "source": row["provider"],
            "published_at": row["published_at"],
            "url": "",
            "category": row["report_type"],
            "summary": row["summary"],
        }
        for row in conn.execute(
            """
            select title, provider, published_at, report_type, summary
            from company_reports_history
            where symbol = ?
            order by published_at desc, id desc
            limit 12
            """,
            (symbol,),
        ).fetchall()
    ]
    news = [
        {
            "type": "news",
            "title": row["title"],
            "source": row["source"],
            "published_at": row["published_at"],
            "url": row["url"],
            "category": row["source_tier"],
            "summary": row["summary"],
            "sentiment_score": number(row["sentiment_score"]),
        }
        for row in conn.execute(
            """
            select title, source, source_tier, published_at, url, summary, sentiment_score
            from news_items
            where symbol = ?
            order by published_at desc, id desc
            limit 20
            """,
            (symbol,),
        ).fetchall()
    ]
    discussions = [
        {
            "type": "community",
            "title": row["title"],
            "source": row["source"],
            "published_at": row["published_at"] or row["fetched_at"],
            "url": row["url"],
            "category": "discussion",
            "summary": row["content"],
        }
        for row in conn.execute(
            """
            select title, source, published_at, fetched_at, url, content
            from community_posts
            where symbol = ?
            order by coalesce(nullif(published_at, ''), fetched_at) desc, id desc
            limit 20
            """,
            (symbol,),
        ).fetchall()
    ]
    sentiment_row = resolve_sentiment_snapshot_row(conn, symbol)
    return {
        "filings": filings + reports,
        "news": news,
        "discussions": discussions,
        "sentiment": apply_current_community_snapshot(conn, normalize_sentiment_snapshot(sentiment_row)) if sentiment_row else None,
    }


def preferred_daily_bars(
    conn: sqlite3.Connection,
    symbol: str,
    symbol_row: dict[str, Any],
    limit: int = 520,
) -> list[dict[str, Any]]:
    clean_limit = max(20, min(int(limit or 520), 1200))
    is_index = is_index_symbol(symbol_row)
    rows = select_preferred_daily_bars(conn, symbol, clean_limit, include_mock=False, is_index=is_index)
    if not rows:
        rows = select_preferred_daily_bars(conn, symbol, clean_limit, include_mock=True, is_index=is_index)
    return [normalize_daily_bar(row) for row in reversed(rows)]


def select_preferred_daily_bars(
    conn: sqlite3.Connection,
    symbol: str,
    limit: int,
    include_mock: bool,
    is_index: bool,
) -> list[sqlite3.Row]:
    preferred_adjust = preferred_daily_adjust(conn, symbol, limit, include_mock, is_index)
    if preferred_adjust is None:
        return []
    provider_filter = "" if include_mock else "and provider != 'mock-market'"
    return conn.execute(
        f"""
        with source_rows as (
          select *
          from daily_bars
          where symbol = ?
            and coalesce(adjust, '') = ?
            {provider_filter}
        ),
        ranked_daily as (
          select
            *,
            row_number() over (
              partition by trade_date
              order by
                case provider
                  when 'tushare-market' then 6
                  when 'baostock-market' then 5
                  when 'akshare-market' then 4
                  when 'finnhub-market' then 2
                  else 1
                end desc,
                fetched_at desc
            ) as rn
          from source_rows
        ),
        valuation_fallback as (
          select
            trade_date,
            max(case when pre_close is not null and pre_close > 0 then pre_close end) as pre_close,
            max(case when turnover_rate is not null and turnover_rate > 0 then turnover_rate end) as turnover_rate,
            max(case when pe_ttm is not null and pe_ttm > 0 then pe_ttm end) as pe_ttm,
            max(case when pb is not null and pb > 0 then pb end) as pb,
            max(case when ps_ttm is not null and ps_ttm > 0 then ps_ttm end) as ps_ttm,
            max(case when pcf_ncf_ttm is not null and pcf_ncf_ttm > 0 then pcf_ncf_ttm end) as pcf_ncf_ttm,
            max(case when provider = 'baostock-market' and volume > 0 then volume end) as baostock_volume,
            max(case when provider = 'baostock-market' and amount > 0 then amount end) as baostock_amount,
            max(case when provider = 'baostock-market' and open > 0 then open end) as baostock_open,
            max(case when provider = 'baostock-market' and high > 0 then high end) as baostock_high,
            max(case when provider = 'baostock-market' and low > 0 then low end) as baostock_low,
            max(case when provider = 'baostock-market' and close > 0 then close end) as baostock_close
          from source_rows
          group by trade_date
        )
        select
          r.symbol,
          r.trade_date,
          r.provider,
          r.adjust,
          case
            when v.baostock_volume is not null
             and r.volume is not null
             and r.volume < v.baostock_volume * 0.8
              then coalesce(v.baostock_open, r.open)
            else r.open
          end as open,
          case
            when v.baostock_volume is not null
             and r.volume is not null
             and r.volume < v.baostock_volume * 0.8
              then coalesce(v.baostock_high, r.high)
            else r.high
          end as high,
          case
            when v.baostock_volume is not null
             and r.volume is not null
             and r.volume < v.baostock_volume * 0.8
              then coalesce(v.baostock_low, r.low)
            else r.low
          end as low,
          case
            when v.baostock_volume is not null
             and r.volume is not null
             and r.volume < v.baostock_volume * 0.8
              then coalesce(v.baostock_close, r.close)
            else r.close
          end as close,
          coalesce(r.pre_close, v.pre_close) as pre_close,
          r.change_pct,
          case
            when v.baostock_volume is not null
             and r.volume is not null
             and r.volume < v.baostock_volume * 0.8
              then v.baostock_volume
            else r.volume
          end as volume,
          case
            when v.baostock_amount is not null
             and r.amount is not null
             and r.amount < v.baostock_amount * 0.8
              then v.baostock_amount
            else r.amount
          end as amount,
          coalesce(r.turnover_rate, v.turnover_rate) as turnover_rate,
          coalesce(r.pe_ttm, v.pe_ttm) as pe_ttm,
          coalesce(r.pb, v.pb) as pb,
          coalesce(r.ps_ttm, v.ps_ttm) as ps_ttm,
          coalesce(r.pcf_ncf_ttm, v.pcf_ncf_ttm) as pcf_ncf_ttm,
          r.is_st,
          r.trade_status,
          r.raw_json,
          r.fetched_at
        from ranked_daily r
        join valuation_fallback v on v.trade_date = r.trade_date
        where r.rn = 1
        order by r.trade_date desc
        limit ?
        """,
        (symbol, preferred_adjust, limit),
    ).fetchall()


def preferred_daily_adjust(
    conn: sqlite3.Connection,
    symbol: str,
    limit: int,
    include_mock: bool,
    is_index: bool,
) -> str | None:
    provider_filter = "" if include_mock else "and provider != 'mock-market'"
    series_rows = conn.execute(
        f"""
        select
          provider,
          coalesce(adjust, '') as adjust,
          count(*) as row_count,
          min(trade_date) as earliest_trade_date,
          max(trade_date) as latest_trade_date,
          min(close) as min_close,
          max(close) as max_close,
          avg(close) as avg_close,
          max(fetched_at) as latest_fetch
        from daily_bars
        where symbol = ?
          {provider_filter}
        group by provider, coalesce(adjust, '')
        """,
        (symbol,),
    ).fetchall()
    if not series_rows:
        return None
    preferred = max(series_rows, key=lambda row: daily_bar_series_rank(row, is_index, limit))
    return str(preferred["adjust"] or "")


def daily_bar_series_rank(row: sqlite3.Row, is_index: bool, limit: int) -> tuple[Any, ...]:
    provider = str(row["provider"] or "")
    adjust = str(row["adjust"] or "").lower()
    row_count = int(row["row_count"] or 0)
    avg_close = number(row["avg_close"], 0) or 0
    latest_trade_date = str(row["latest_trade_date"] or "")
    latest_fetch = str(row["latest_fetch"] or "")
    provider_score = MARKET_PROVIDER_PRIORITY.get(provider, 0)
    coverage_score = min(row_count, max(20, limit))

    if is_index:
        adjust_score = 8 if adjust == "" else 1
        scale_score = 3 if avg_close >= 100 else 0
        index_provider_score = {
            "baostock-market": 6,
            "tushare-market": 5,
            "akshare-market": 4,
            "finnhub-market": 2,
            "mock-market": 1,
        }.get(provider, provider_score)
        return (adjust_score, scale_score, latest_trade_date, coverage_score, index_provider_score, latest_fetch)

    adjust_score = {"qfq": 5, "hfq": 4, "": 3}.get(adjust, 2)
    return (latest_trade_date, adjust_score, provider_score, coverage_score, latest_fetch)


def is_index_symbol(symbol_row: dict[str, Any]) -> bool:
    symbol = str(symbol_row.get("symbol") or "").upper()
    name = str(symbol_row.get("name") or "")
    sector = str(symbol_row.get("sector") or "")
    industry = str(symbol_row.get("industry") or "")
    if "指数" in name or "指数" in sector or "指数" in industry:
        return True
    return symbol in {
        "000001.SH",
        "000002.SH",
        "000003.SH",
        "399001.SZ",
        "399006.SZ",
        "399300.SZ",
    }


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
        where symbol = ?
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


def normalize_sentiment_snapshot(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    item["source_counts"] = parse_json(item.pop("source_counts_json", "{}"))
    item["raw"] = parse_json(item.pop("raw_json", "{}"))
    return item


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
