from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException

from .data_sources import DEFAULT_ACCOUNT_ID, active_source_ids, tushare_token
from .db import now_iso, row_to_dict, upsert_financial_metrics_history
from .providers import TushareClient, TushareError
from .providers.tushare import financial_date_window, latest_row, recent_tushare_date_window


TUSHARE_MARKET_SOURCE_ID = "cn-tushare-market"
TUSHARE_FINANCIAL_SOURCE_ID = "cn-tushare-financial"
TUSHARE_PROVIDER_MARKET = "tushare-market"
TUSHARE_PROVIDER_FINANCIAL = "tushare-financial"


def tushare_status(conn: sqlite3.Connection, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    source_ids = active_source_ids(conn, account_id)
    token_configured = bool(tushare_token(conn, account_id))
    latest_market = latest_snapshot_meta(conn, "market_snapshots", TUSHARE_PROVIDER_MARKET)
    latest_financial = latest_financial_metrics_meta(conn, TUSHARE_PROVIDER_FINANCIAL)
    return {
        "provider": "tushare",
        "account_id": account_id,
        "token_configured": token_configured,
        "market_active": TUSHARE_MARKET_SOURCE_ID in source_ids,
        "financial_active": TUSHARE_FINANCIAL_SOURCE_ID in source_ids,
        "latest_market": latest_market,
        "latest_financial": latest_financial,
    }


def refresh_tushare_data(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    refresh_universe: bool = False,
    account_id: str = DEFAULT_ACCOUNT_ID,
) -> dict[str, Any]:
    source_ids = active_source_ids(conn, account_id)
    market_active = TUSHARE_MARKET_SOURCE_ID in source_ids
    financial_active = TUSHARE_FINANCIAL_SOURCE_ID in source_ids
    if not market_active and not financial_active:
        raise HTTPException(status_code=400, detail="Tushare 数据源未启用")

    token = tushare_token(conn, account_id)
    if not token:
        raise HTTPException(status_code=400, detail="Tushare token 未配置")

    client = TushareClient(token)
    target_symbols = normalize_symbols(symbols) if symbols else existing_a_share_symbols(conn)
    if not target_symbols:
        raise HTTPException(status_code=400, detail="没有可刷新的 A 股股票代码")

    errors: list[dict[str, str]] = []
    updated_symbols: list[str] = []
    market_count = 0
    financial_count = 0

    if refresh_universe:
        try:
            basics = client.stock_basic()
        except TushareError as exc:
            raise HTTPException(status_code=502, detail=f"Tushare stock_basic 失败：{exc}") from exc
        upsert_symbols(conn, basics)

    daily_start, daily_end = recent_tushare_date_window(20)
    financial_start, financial_end = financial_date_window()

    for symbol in target_symbols:
        if not is_a_share_symbol(symbol):
            errors.append({"symbol": symbol, "error": "当前 Tushare 接入只处理 A 股 .SH/.SZ/.BJ 代码"})
            continue

        try:
            daily_rows = client.daily(symbol, daily_start, daily_end)
            daily_basic_rows: list[dict[str, Any]] = []
            try:
                daily_basic_rows = client.daily_basic(symbol, daily_start, daily_end)
            except TushareError as exc:
                errors.append({"symbol": symbol, "error": f"Tushare daily_basic 暂不可用：{exc}"})
            daily = latest_row(daily_rows, "trade_date")
            daily_basic = latest_row(daily_basic_rows, "trade_date")
            if not daily:
                errors.append({"symbol": symbol, "error": "Tushare daily 无返回数据"})
                continue

            if market_active:
                insert_market_snapshot(conn, daily, daily_basic)
                market_count += 1

            if financial_active:
                try:
                    indicator_rows = client.fina_indicator(symbol, financial_start, financial_end)
                    income_rows = client.income(symbol, financial_start, financial_end)
                    cashflow_rows: list[dict[str, Any]] = []
                    try:
                        cashflow_rows = client.cashflow(symbol, financial_start, financial_end)
                    except TushareError as exc:
                        errors.append({"symbol": symbol, "error": f"Tushare cashflow 暂不可用：{exc}"})
                    indicator = latest_row(indicator_rows, "end_date")
                    income = latest_row(income_rows, "end_date")
                    cashflow = latest_row(cashflow_rows, "end_date")
                    if indicator or income or cashflow:
                        insert_financial_snapshot(conn, symbol, indicator, income, cashflow, daily_basic)
                        financial_count += 1
                    else:
                        errors.append({"symbol": symbol, "error": "Tushare 财务接口无返回数据"})
                except TushareError as exc:
                    errors.append({"symbol": symbol, "error": f"Tushare 财务接口暂不可用：{exc}"})

            updated_symbols.append(symbol)
        except TushareError as exc:
            errors.append({"symbol": symbol, "error": str(exc)})

    conn.commit()
    return {
        "status": "ok" if updated_symbols else "partial",
        "mode": "tushare",
        "refreshed_at": now_iso(),
        "symbols": updated_symbols,
        "requested_symbols": target_symbols,
        "counts": {
            "market_snapshots": market_count,
            "financial_snapshots": financial_count,
            "financial_metrics_history": financial_count,
            "errors": len(errors),
        },
        "errors": errors,
        "status_detail": tushare_status(conn, account_id),
    }


def existing_a_share_symbols(conn: sqlite3.Connection) -> list[str]:
    return [
        row["symbol"]
        for row in conn.execute(
            """
            select symbol
            from symbols
            where market = 'A' and (symbol like '%.SH' or symbol like '%.SZ' or symbol like '%.BJ')
            order by symbol
            """
        )
    ]


def normalize_symbols(symbols: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in symbols:
        symbol = item.strip().upper()
        if not symbol:
            continue
        if symbol not in seen:
            seen.add(symbol)
            normalized.append(symbol)
    return normalized


def is_a_share_symbol(symbol: str) -> bool:
    return symbol.endswith(".SH") or symbol.endswith(".SZ") or symbol.endswith(".BJ")


def upsert_symbols(conn: sqlite3.Connection, basics: list[dict[str, Any]]) -> None:
    rows = []
    for item in basics:
        symbol = str(item.get("ts_code") or "").upper()
        if not is_a_share_symbol(symbol):
            continue
        rows.append(
            {
                "symbol": symbol,
                "market": "A",
                "name": item.get("name") or symbol,
                "currency": item.get("curr_type") or "CNY",
                "exchange": item.get("exchange") or exchange_from_symbol(symbol),
                "sector": item.get("area") or "A股",
                "industry": item.get("industry") or item.get("market") or "未分类",
            }
        )
    conn.executemany(
        """
        insert into symbols (symbol, market, name, currency, exchange, sector, industry)
        values (:symbol, :market, :name, :currency, :exchange, :sector, :industry)
        on conflict(symbol) do update set
          name = excluded.name,
          currency = excluded.currency,
          exchange = excluded.exchange,
          sector = excluded.sector,
          industry = excluded.industry
        """,
        rows,
    )


def insert_market_snapshot(
    conn: sqlite3.Connection,
    daily: dict[str, Any],
    daily_basic: dict[str, Any] | None,
) -> None:
    trade_date = str(daily["trade_date"])
    close = float_value(daily.get("close"), 0)
    amount_cny = float_value(daily.get("amount"), 0) * 1000
    volume_shares = float_value(daily.get("vol"), 0) * 100
    turnover_rate = first_number(daily_basic, ["turnover_rate", "turnover_rate_f"], 0)
    raw_json = {
        "daily": daily,
        "daily_basic": daily_basic or {},
        "change": float_value(daily.get("pct_chg"), 0),
        "volume_ratio": first_number(daily_basic, ["volume_ratio"], 1),
        "pe": first_number(daily_basic, ["pe_ttm", "pe"], None),
        "pb": first_number(daily_basic, ["pb"], None),
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
            daily["ts_code"],
            TUSHARE_PROVIDER_MARKET,
            trade_date_to_as_of(trade_date),
            now_iso(),
            close,
            volume_shares,
            amount_cny,
            turnover_rate,
            5,
            json.dumps(raw_json, ensure_ascii=False),
            freshness_for_trade_date(trade_date),
        ),
    )


def insert_financial_snapshot(
    conn: sqlite3.Connection,
    symbol: str,
    indicator: dict[str, Any] | None,
    income: dict[str, Any] | None,
    cashflow: dict[str, Any] | None,
    daily_basic: dict[str, Any] | None,
) -> None:
    indicator = indicator or {}
    income = income or {}
    cashflow = cashflow or {}
    period = str(indicator.get("end_date") or income.get("end_date") or cashflow.get("end_date") or "")
    fcf = tushare_fcf_margin(income, cashflow)
    raw_json = {
        "fina_indicator": indicator,
        "income": income,
        "cashflow": cashflow,
        "daily_basic": daily_basic or {},
        "fcf_margin_source": fcf["source"],
        "free_cash_flow": fcf["free_cash_flow"],
        "fcf_margin": fcf["margin"],
    }
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
            TUSHARE_PROVIDER_FINANCIAL,
            number_or_zero(optional_number(indicator, ["or_yoy", "tr_yoy"])),
            number_or_zero(optional_number(indicator, ["roe_dt", "roe_waa", "roe", "q_roe"])),
            number_or_zero(fcf["margin"]),
            number_or_zero(optional_number(indicator, ["debt_to_assets"])),
            first_number(daily_basic, ["pe_ttm", "pe"], 0),
            first_number(daily_basic, ["pb"], 0),
            json.dumps(raw_json, ensure_ascii=False),
        ),
    )
    upsert_financial_metrics_history(
        conn,
        {
            "symbol": symbol,
            "report_period": period,
            "provider": TUSHARE_PROVIDER_FINANCIAL,
            "announce_date": str(indicator.get("ann_date") or income.get("ann_date") or cashflow.get("ann_date") or ""),
            "revenue_growth": optional_number(indicator, ["or_yoy", "tr_yoy"]),
            "roe": optional_number(indicator, ["roe_dt", "roe_waa", "roe", "q_roe"]),
            "fcf_margin": fcf["margin"],
            "debt_ratio": optional_number(indicator, ["debt_to_assets"]),
            "gross_margin": optional_number(indicator, ["grossprofit_margin"]),
            "net_margin": optional_number(indicator, ["netprofit_margin"]),
            "net_profit": optional_number(income, ["n_income_attr_p", "n_income"]),
            "raw_json": raw_json,
        },
    )


def latest_snapshot_meta(conn: sqlite3.Connection, table: str, provider: str) -> dict[str, Any] | None:
    if table == "financial_snapshots":
        row = conn.execute(
            """
            select provider, max(period) as as_of, count(*) as count
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


def trade_date_to_as_of(trade_date: str) -> str:
    try:
        parsed = datetime.strptime(trade_date, "%Y%m%d").date()
        return f"{parsed.isoformat()}T15:00:00+08:00"
    except ValueError:
        return trade_date


def freshness_for_trade_date(trade_date: str) -> str:
    try:
        parsed = datetime.strptime(trade_date, "%Y%m%d").date()
    except ValueError:
        return "warn"
    age_days = (date.today() - parsed).days
    if age_days <= 3:
        return "fresh"
    if age_days <= 10:
        return "warn"
    return "stale"


def exchange_from_symbol(symbol: str) -> str:
    if symbol.endswith(".SH"):
        return "SSE"
    if symbol.endswith(".SZ"):
        return "SZSE"
    if symbol.endswith(".BJ"):
        return "BSE"
    return "A股"


def tushare_fcf_margin(income: dict[str, Any], cashflow: dict[str, Any]) -> dict[str, Any]:
    revenue = optional_number(income, ["total_revenue", "revenue"])
    operating_cash_flow = optional_number(cashflow, ["n_cashflow_act"])
    capex = optional_number(cashflow, ["c_pay_acq_const_fiolta"])
    reported_free_cash_flow = optional_number(cashflow, ["free_cashflow"])

    source = "missing_cashflow_or_revenue"
    free_cash_flow: float | None = None
    if operating_cash_flow is not None and capex is not None:
        free_cash_flow = operating_cash_flow - capex
        source = "n_cashflow_act_minus_c_pay_acq_const_fiolta"
    elif reported_free_cash_flow is not None:
        free_cash_flow = reported_free_cash_flow
        source = "free_cashflow"

    margin = None
    if free_cash_flow is not None and revenue not in (None, 0):
        margin = free_cash_flow / revenue * 100
    return {"margin": margin, "free_cash_flow": free_cash_flow, "source": source}


def optional_number(row: dict[str, Any] | None, keys: list[str]) -> float | None:
    if not row:
        return None
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            parsed = float_value(value, 0)
            return parsed
    return None


def number_or_zero(value: float | None) -> float:
    return 0 if value is None else value


def first_number(row: dict[str, Any] | None, keys: list[str], default: float | None = 0) -> float:
    if not row:
        return 0 if default is None else float(default)
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return float_value(value, 0 if default is None else float(default))
    return 0 if default is None else float(default)


def float_value(value: Any, default: float) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
