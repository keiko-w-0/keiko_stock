from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time as datetime_time, timedelta
from typing import Any

from fastapi import HTTPException

from .data_sources import DEFAULT_ACCOUNT_ID, tushare_token
from .db import get_db, now_iso, row_to_dict
from .job_monitor import terminate_script_processes
from .pinyin import pinyin_initials
from .providers import BaostockError, TushareClient, TushareError
from .providers.baostock_provider import (
    query_baostock_all_stock,
    query_baostock_basic,
    query_baostock_company_reports_batch_guarded,
    query_baostock_history,
    query_baostock_history_batch,
    query_baostock_quarterly_financials_batch_guarded,
    standard_symbol,
)
from .providers.tushare import latest_row
from .symbol_resolver import infer_symbol, resolve_symbol


AKSHARE_MARKET_PROVIDER = "akshare-market"
BAOSTOCK_MARKET_PROVIDER = "baostock-market"
BAOSTOCK_FINANCIAL_PROVIDER = "baostock-financial"
BAOSTOCK_REPORT_PROVIDER = "baostock-report"
TUSHARE_MARKET_PROVIDER = "tushare-market"
BAOSTOCK_BACKGROUND_STALE_MINUTES = 45
BAOSTOCK_BATCH_SLEEP_SECONDS = 1.0
BAOSTOCK_FINANCIAL_NO_DATA_RETRY_DAYS = 7
BAOSTOCK_PRIORITY_REFRESH_WAIT_SECONDS = 20.0
A_SHARE_FILING_PROVIDER = "cninfo_sse_szse"
A_SHARE_FILING_BACKGROUND_STALE_MINUTES = 45
A_SHARE_FILING_BATCH_SLEEP_SECONDS = 0.8
A_SHARE_FILING_REFRESH_RETRY_HOURS = 20
A_SHARE_FILING_DEFAULT_DAYS = 180
STOCK_DETAIL_MARKET_OVERLAP_DAYS = 20
STOCK_DETAIL_FILING_DAYS = 30
STOCK_DETAIL_FINANCIAL_QUARTERS = 4
STOCK_DETAIL_SENTIMENT_EVIDENCE_LIMIT = 120
BAOSTOCK_DAILY_SCRIPT_NAMES = ["scripts/run_baostock_backfill.py", "run_baostock_backfill.py"]
BAOSTOCK_FINANCIAL_SCRIPT_NAMES = ["scripts/run_baostock_financial_backfill.py", "run_baostock_financial_backfill.py"]
A_SHARE_FILING_SCRIPT_NAMES = ["scripts/run_a_share_filings_backfill.py", "run_a_share_filings_backfill.py"]


def warehouse_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "symbols": scalar_count(conn, "symbols"),
        "aliases": scalar_count(conn, "symbol_aliases"),
        "daily_bars": scalar_count(conn, "daily_bars"),
        "financial_metrics": scalar_count(conn, "financial_metrics_history"),
        "filings": scalar_count(conn, "filings_history"),
        "company_reports": scalar_count(conn, "company_reports_history"),
        "community_posts": scalar_count(conn, "community_posts"),
        "sentiment_evidence": scalar_count(conn, "sentiment_evidence"),
        "sentiment_snapshots": scalar_count(conn, "sentiment_snapshots"),
        "latest_daily_bar": scalar_value(conn, "select max(trade_date) from daily_bars"),
    }


def refresh_akshare_data(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    refresh_universe: bool = False,
    days: int = 260,
    allow_slow_fallback: bool = True,
) -> dict[str, Any]:
    run_id = start_ingestion(conn, "akshare", "a-share-history", symbols or [], refresh_universe)
    conn.commit()
    errors: list[dict[str, str]] = []
    updated_symbols: list[str] = []
    counts = {"symbols": 0, "daily_bars": 0, "market_snapshots": 0}

    if refresh_universe or not symbols:
        try:
            universe = fetch_akshare_spot()
            counts["symbols"] += upsert_akshare_universe(conn, universe)
            counts["daily_bars"] += upsert_spot_daily_bars(conn, universe)
            counts["market_snapshots"] += upsert_spot_market_snapshots(conn, universe)
        except Exception as exc:  # AKShare/network failures should be visible but not corrupt the run.
            errors.append({"scope": "universe", "error": str(exc)})
            if not allow_slow_fallback:
                finish_ingestion(conn, run_id, "partial", updated_symbols, counts, errors)
                conn.commit()
                return {
                    "status": "partial",
                    "mode": "akshare-history",
                    "run_id": run_id,
                    "refreshed_at": now_iso(),
                    "symbols": updated_symbols,
                    "requested_symbols": [],
                    "counts": counts,
                    "errors": errors,
                    "warehouse": warehouse_summary(conn),
                }
            try:
                fallback = refresh_tushare_latest_trade_date(conn)
                counts["symbols"] += fallback["symbols"]
                counts["daily_bars"] += fallback["daily_bars"]
                counts["market_snapshots"] += fallback["market_snapshots"]
                updated_symbols.extend(fallback["symbols_updated"])
                if fallback["errors"]:
                    errors.extend(fallback["errors"])
            except Exception as fallback_exc:
                errors.append({"scope": "tushare-latest-trade-date", "error": str(fallback_exc)})

    target_symbols = normalize_symbols(conn, symbols or [])

    start_date = (date.today() - timedelta(days=days)).strftime("%Y%m%d")
    end_date = date.today().strftime("%Y%m%d")
    for symbol in target_symbols:
        if not is_a_share(symbol):
            errors.append({"symbol": symbol, "error": "AKShare 历史同步当前只处理 A 股 .SH/.SZ/.BJ"})
            continue
        try:
            rows = fetch_akshare_hist(symbol, start_date, end_date)
            inserted = upsert_akshare_history(conn, symbol, rows)
            counts["daily_bars"] += inserted
            if rows:
                upsert_latest_history_snapshot(conn, symbol, rows[-1])
                counts["market_snapshots"] += 1
            updated_symbols.append(symbol)
        except Exception as exc:
            if not allow_slow_fallback:
                errors.append({"symbol": symbol, "error": str(exc)})
                continue
            baostock_fallback = refresh_baostock_history_symbol(
                conn,
                symbol,
                normalize_date(start_date),
                normalize_date(end_date),
            )
            if baostock_fallback["daily_bars"]:
                counts["daily_bars"] += baostock_fallback["daily_bars"]
                counts["market_snapshots"] += baostock_fallback["market_snapshots"]
                updated_symbols.append(symbol)
                errors.append({"symbol": symbol, "error": f"AKShare 历史失败，已用 BaoStock 兜底：{exc}"})
                errors.extend(baostock_fallback["errors"])
            else:
                tushare_fallback = refresh_tushare_history_symbol(conn, symbol, start_date, end_date)
                if tushare_fallback["daily_bars"]:
                    counts["daily_bars"] += tushare_fallback["daily_bars"]
                    counts["market_snapshots"] += tushare_fallback["market_snapshots"]
                    updated_symbols.append(symbol)
                    errors.append({"symbol": symbol, "error": f"AKShare/BaoStock 历史失败，已用 Tushare 兜底：{exc}"})
                    errors.extend(baostock_fallback["errors"])
                    errors.extend(tushare_fallback["errors"])
                else:
                    errors.append({"symbol": symbol, "error": str(exc)})
                    errors.extend(baostock_fallback["errors"])
                    errors.extend(tushare_fallback["errors"])

    status = "ok" if updated_symbols or counts["symbols"] or counts["daily_bars"] else "partial"
    finish_ingestion(conn, run_id, status, updated_symbols, counts, errors)
    conn.commit()
    return {
        "status": status,
        "mode": "akshare-history",
        "run_id": run_id,
        "refreshed_at": now_iso(),
        "symbols": updated_symbols,
        "requested_symbols": target_symbols,
        "counts": counts,
        "errors": errors,
        "warehouse": warehouse_summary(conn),
    }


def ensure_query_data(
    conn: sqlite3.Connection,
    query: str,
    market: str = "all",
    days: int = 260,
) -> dict[str, Any]:
    clean = query.strip()
    if not clean:
        return {"status": "skipped", "errors": []}

    resolved = resolve_symbol(conn, clean, market)
    if not resolved:
        try:
            universe = fetch_akshare_spot()
            upsert_akshare_universe(conn, universe)
            upsert_spot_daily_bars(conn, universe)
            upsert_spot_market_snapshots(conn, universe)
            conn.commit()
            resolved = resolve_symbol(conn, clean, market)
        except Exception as exc:
            fallback_error = str(exc)
            try:
                basics = query_baostock_all_stock(latest_baostock_daily_trade_date())
                upsert_baostock_universe(conn, basics)
                conn.commit()
                resolved = resolve_symbol(conn, clean, market)
                if not resolved:
                    basics = query_baostock_basic(code_name=clean)
                    upsert_baostock_universe(conn, basics)
                    conn.commit()
                    resolved = resolve_symbol(conn, clean, market)
            except Exception as baostock_exc:
                try:
                    basics = fetch_tushare_universe(conn)
                    upsert_tushare_universe(conn, basics)
                    conn.commit()
                    resolved = resolve_symbol(conn, clean, market)
                except Exception as fallback_exc:
                    return {
                        "status": "failed",
                        "errors": [
                            {"scope": "akshare-symbol-lookup", "error": fallback_error},
                            {"scope": "baostock-symbol-lookup", "error": str(baostock_exc)},
                            {"scope": "tushare-symbol-lookup", "error": str(fallback_exc)},
                        ],
                    }

    symbol = str(resolved.get("symbol") or "").upper() if resolved else infer_symbol(clean.upper())
    if not symbol:
        return {"status": "not_found", "errors": []}
    if not is_a_share(symbol):
        return {"status": "skipped", "symbol": symbol, "errors": []}
    result = refresh_akshare_data(conn, [symbol], refresh_universe=False, days=days)
    try:
        filing_result = refresh_filings_for_symbol_if_needed(conn, symbol, days=STOCK_DETAIL_FILING_DAYS)
        filing_count = int(filing_result.get("filings") or 0)
        result.setdefault("counts", {})["filings"] = filing_count
        result.setdefault("counts", {})["filings_skipped"] = 1 if filing_result.get("status") == "skipped" else 0
        result.setdefault("warehouse", warehouse_summary(conn))
    except Exception as exc:
        result.setdefault("errors", []).append({"symbol": symbol, "error": f"公告同步失败：{exc}"})
    return result


def refresh_stock_detail_data(
    conn: sqlite3.Connection,
    query: str,
    market: str = "all",
    days: int = 260,
    quarters: int = 8,
) -> dict[str, Any]:
    total_started = time.monotonic()
    clean = query.strip()
    if not clean:
        return {"status": "skipped", "errors": [{"scope": "symbol", "error": "empty symbol"}]}

    resolved = resolve_symbol(conn, clean, market)
    symbol = str(resolved.get("symbol") or "").upper() if resolved else (infer_symbol(clean.upper()) or clean.upper())
    if not symbol:
        return {"status": "not_found", "errors": [{"scope": "symbol", "error": f"未找到证券：{query}"}]}
    if not is_a_share(symbol):
        return {"status": "skipped", "symbol": symbol, "errors": [{"symbol": symbol, "error": "当前详情页刷新只处理 A 股"}]}

    stale_run_ids = mark_stale_running_ingestions(
        conn,
        "baostock",
        "a-share-history-background",
        stale_minutes=BAOSTOCK_BACKGROUND_STALE_MINUTES,
    )
    stale_run_ids.extend(
        mark_stale_running_ingestions(
            conn,
            "baostock",
            "a-share-quarterly-financials-background",
            stale_minutes=BAOSTOCK_BACKGROUND_STALE_MINUTES,
        )
    )
    stale_processes: list[dict[str, Any]] = []
    if stale_run_ids:
        conn.commit()
        stale_processes.extend(terminate_script_processes(BAOSTOCK_DAILY_SCRIPT_NAMES + BAOSTOCK_FINANCIAL_SCRIPT_NAMES))
    priority_jobs = request_baostock_background_priority_pause(conn, symbol)
    preempted_jobs: list[dict[str, Any]] = []
    if priority_jobs:
        conn.commit()
        wait_for_baostock_background_pause(conn, BAOSTOCK_PRIORITY_REFRESH_WAIT_SECONDS)
        preempted_jobs = preempt_baostock_background_jobs(conn, symbol)
        if preempted_jobs:
            conn.commit()

    errors: list[dict[str, str]] = []
    counts: dict[str, int] = {
        "daily_bars": 0,
        "market_snapshots": 0,
        "financial_metrics": 0,
        "company_reports": 0,
        "filings": 0,
        "sentiment_evidence": 0,
        "sentiment_snapshots": 0,
    }
    run_ids: dict[str, int] = {}
    steps: list[dict[str, Any]] = []
    effective_quarters = min(max(1, int(quarters or STOCK_DETAIL_FINANCIAL_QUARTERS)), STOCK_DETAIL_FINANCIAL_QUARTERS)
    periods = recent_quarter_periods(effective_quarters)

    parallel_steps = {
        "market": lambda: refresh_stock_detail_market_step(symbol, days),
        "financials": lambda: refresh_stock_detail_financial_step(symbol, periods),
        "filings": lambda: refresh_stock_detail_filings_step(symbol),
    }
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(run_stock_detail_timed_step, step, callback): step
            for step, callback in parallel_steps.items()
        }
        for future in as_completed(futures):
            steps.append(future.result())

    steps.append(run_stock_detail_timed_step("sentiment", lambda: refresh_stock_detail_sentiment_step(symbol)))

    for step in steps:
        result = step.get("result") or {}
        if step.get("status") == "failed":
            errors.extend(result.get("errors") or [{"symbol": symbol, "error": f"{step.get('step')} failed"}])
            continue
        if step.get("step") == "market":
            if result.get("run_id"):
                run_ids["market"] = int(result.get("run_id") or 0)
            market_counts = result.get("counts") or {}
            counts["daily_bars"] += int(market_counts.get("daily_bars") or 0)
            counts["market_snapshots"] += int(market_counts.get("market_snapshots") or 0)
        elif step.get("step") == "financials":
            counts["financial_metrics"] += int(result.get("financial_metrics") or 0)
            counts["company_reports"] += int(result.get("company_reports") or 0)
        elif step.get("step") == "filings":
            counts["filings"] += int(result.get("filings") or 0)
        elif step.get("step") == "sentiment":
            sentiment_counts = result.get("counts") or {}
            counts["sentiment_evidence"] += sum(
                int(sentiment_counts.get(key) or 0)
                for key in ("filing_news_evidence", "community_evidence", "market_evidence")
            )
            counts["sentiment_snapshots"] += int(sentiment_counts.get("snapshots") or 0)
        errors.extend(result.get("errors") or [])

    sql_started = time.monotonic()
    summary = warehouse_summary(conn)
    steps.append(
        {
            "step": "sql-summary",
            "status": "ok",
            "duration_ms": elapsed_ms(sql_started),
            "result": {"counts": summary},
        }
    )
    status = "partial" if errors else "ok"
    return {
        "status": status,
        "mode": "stock-detail-refresh",
        "symbol": symbol,
        "name": str(resolved.get("name") or "") if resolved else "",
        "run_ids": run_ids,
        "counts": counts,
        "errors": errors,
        "stale_run_ids": stale_run_ids,
        "stale_processes": stale_processes,
        "priority_jobs": priority_jobs,
        "preempted_jobs": preempted_jobs,
        "background_jobs_after_priority_wait": active_baostock_background_jobs(conn),
        "performance": {
            "total_ms": elapsed_ms(total_started),
            "requested_quarters": quarters,
            "effective_quarters": effective_quarters,
            "steps": [stock_detail_step_summary(step) for step in steps],
        },
        "refreshed_at": now_iso(),
        "warehouse": summary,
    }


def refresh_stock_detail_market_step(symbol: str, days: int) -> dict[str, Any]:
    with get_db() as conn:
        refresh_days, reason = stock_detail_market_refresh_days(conn, symbol, days)
        if refresh_days <= 0:
            return {"status": "skipped", "reason": reason, "counts": {"daily_bars": 0, "market_snapshots": 0}, "errors": []}
        result = refresh_akshare_data(conn, [symbol], refresh_universe=False, days=refresh_days, allow_slow_fallback=False)
        result["requested_days"] = refresh_days
        result["reason"] = reason
        return result


def refresh_stock_detail_financial_step(symbol: str, periods: list[tuple[int, int]]) -> dict[str, Any]:
    with get_db() as conn:
        plan = baostock_financial_backfill_plan(conn, [symbol], periods)
        if not plan.get(symbol):
            return {
                "status": "skipped",
                "reason": "recent financial_metrics_history already covers requested quarters",
                "symbols": [],
                "financial_metrics": 0,
                "company_reports": 0,
                "errors": [],
            }
        result = refresh_baostock_financial_batch(conn, [symbol], periods)
        result["planned_periods"] = [quarter_period_key(year, quarter) for year, quarter in plan.get(symbol, [])]
        conn.commit()
        return result


def refresh_stock_detail_filings_step(symbol: str) -> dict[str, Any]:
    with get_db() as conn:
        result = refresh_filings_for_symbol_if_needed(conn, symbol, days=STOCK_DETAIL_FILING_DAYS)
        conn.commit()
        return result


def refresh_stock_detail_sentiment_step(symbol: str) -> dict[str, Any]:
    from .sentiment import refresh_symbol_sentiment

    with get_db() as conn:
        freshness = latest_sentiment_snapshot_freshness(conn, symbol)
        if freshness.get("fresh"):
            return {
                "status": "skipped",
                "reason": freshness.get("reason", "recent sentiment snapshot already exists"),
                "counts": {
                    "filing_news_evidence": 0,
                    "community_evidence": 0,
                    "market_evidence": 0,
                    "snapshots": 0,
                },
                "errors": [],
            }
        result = refresh_symbol_sentiment(
            conn,
            symbol,
            days=30,
            use_llm=True,
            evidence_limit=STOCK_DETAIL_SENTIMENT_EVIDENCE_LIMIT,
        )
        conn.commit()
        return result


def latest_sentiment_snapshot_freshness(conn: sqlite3.Connection, symbol: str, max_age_minutes: int = 360) -> dict[str, Any]:
    row = conn.execute(
        """
        select generated_at
        from sentiment_snapshots
        where symbol = ?
        order by generated_at desc, id desc
        limit 1
        """,
        (symbol,),
    ).fetchone()
    if not row:
        return {"fresh": False, "reason": "no sentiment snapshot"}
    generated_at = str(row["generated_at"] or "")
    try:
        parsed = datetime.fromisoformat(generated_at)
    except ValueError:
        return {"fresh": False, "reason": "sentiment snapshot timestamp invalid"}
    age_minutes = (datetime.now() - parsed).total_seconds() / 60
    if age_minutes <= max_age_minutes:
        return {"fresh": True, "reason": f"sentiment snapshot generated {int(age_minutes)} minutes ago"}
    return {"fresh": False, "reason": f"sentiment snapshot older than {max_age_minutes} minutes"}


def stock_detail_market_refresh_days(conn: sqlite3.Connection, symbol: str, requested_days: int) -> tuple[int, str]:
    row = conn.execute(
        """
        select max(trade_date) as latest_trade_date, max(fetched_at) as latest_fetch
        from daily_bars
        where symbol = ?
          and provider != 'mock-market'
        """,
        (symbol,),
    ).fetchone()
    latest_trade_date = str(row["latest_trade_date"] or "") if row else ""
    target_trade_date = latest_cn_trade_date()
    if latest_trade_date and latest_trade_date >= target_trade_date:
        return 0, f"daily_bars already covers latest trade date {target_trade_date}"
    if latest_trade_date:
        try:
            overlap_start = datetime.fromisoformat(latest_trade_date).date() - timedelta(days=STOCK_DETAIL_MARKET_OVERLAP_DAYS)
        except ValueError:
            overlap_start = date.today() - timedelta(days=max(20, requested_days))
        incremental_days = max(20, (date.today() - overlap_start).days)
        return min(max(20, int(requested_days or 260)), incremental_days), f"incremental daily refresh after {latest_trade_date}"
    return max(20, int(requested_days or 260)), "no local non-mock daily_bars"


def run_stock_detail_timed_step(step: str, callback: Any) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = callback()
        status = str(result.get("status") or "ok")
    except Exception as exc:
        result = {"errors": [{"scope": step, "error": str(exc)}]}
        status = "failed"
    return {"step": step, "status": status, "duration_ms": elapsed_ms(started), "result": result}


def stock_detail_step_summary(step: dict[str, Any]) -> dict[str, Any]:
    result = step.get("result") or {}
    summary = {
        "step": step.get("step"),
        "status": step.get("status"),
        "duration_ms": step.get("duration_ms"),
        "reason": result.get("reason", ""),
        "error_count": len(result.get("errors") or []),
    }
    if result.get("counts"):
        summary["counts"] = result.get("counts")
    for key in ("daily_bars", "market_snapshots", "financial_metrics", "company_reports", "filings"):
        if key in result:
            summary[key] = result.get(key)
    if result.get("requested_days"):
        summary["requested_days"] = result.get("requested_days")
    if result.get("planned_periods"):
        summary["planned_periods"] = result.get("planned_periods")
    return summary


def elapsed_ms(started: float) -> int:
    return int(round((time.monotonic() - started) * 1000))


def active_baostock_background_jobs(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "scope": row["scope"],
            "started_at": row["started_at"],
        }
        for row in baostock_background_running_rows(conn)
    ]


def baostock_background_running_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for scope_prefix in ("a-share-history-background", "a-share-quarterly-financials-background"):
        rows = conn.execute(
            """
            select *
            from ingestion_runs
            where provider = 'baostock'
              and scope like ?
              and status = 'running'
            order by id
            """,
            (f"{scope_prefix}%",),
        ).fetchall()
        jobs.extend(row_to_dict(row) for row in rows)
    return jobs


def request_baostock_background_priority_pause(conn: sqlite3.Connection, symbol: str) -> list[dict[str, Any]]:
    requested_at = now_iso()
    jobs: list[dict[str, Any]] = []
    for row in baostock_background_running_rows(conn):
        counts = parse_json_value(row.get("counts_json"), {})
        errors = parse_json_value(row.get("errors_json"), [])
        if not counts.get("priority_refresh_requested_at"):
            errors.append(
                {
                    "scope": "priority-refresh",
                    "error": f"Priority single-stock refresh requested for {symbol}; background job will pause at the next batch boundary.",
                }
            )
        counts["priority_refresh_requested_at"] = requested_at
        counts["priority_refresh_symbol"] = symbol
        conn.execute(
            """
            update ingestion_runs
            set counts_json = ?, errors_json = ?
            where id = ? and status = 'running'
            """,
            (
                json.dumps(counts, ensure_ascii=False),
                json.dumps(errors, ensure_ascii=False),
                row["id"],
            ),
        )
        jobs.append({"id": row["id"], "scope": row["scope"], "started_at": row["started_at"]})
    return jobs


def wait_for_baostock_background_pause(conn: sqlite3.Connection, timeout_seconds: float) -> None:
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while time.monotonic() < deadline:
        if not active_baostock_background_jobs(conn):
            return
        time.sleep(0.5)


def preempt_baostock_background_jobs(conn: sqlite3.Connection, symbol: str) -> list[dict[str, Any]]:
    preempted: list[dict[str, Any]] = []
    rows = baostock_background_running_rows(conn)
    terminated_processes = (
        terminate_script_processes(BAOSTOCK_DAILY_SCRIPT_NAMES + BAOSTOCK_FINANCIAL_SCRIPT_NAMES)
        if rows
        else []
    )
    for row in rows:
        counts = parse_json_value(row.get("counts_json"), {})
        errors = parse_json_value(row.get("errors_json"), [])
        counts["preempted_by_priority_refresh_at"] = now_iso()
        counts["preempted_by_priority_refresh_symbol"] = symbol
        errors.append(
            {
                "scope": "priority-refresh",
                "error": f"Background job preempted so priority single-stock refresh for {symbol} can run first.",
            }
        )
        finish_ingestion(conn, int(row["id"]), "interrupted", parse_json_value(row.get("updated_symbols"), []), counts, errors)
        preempted.append(
            {
                "id": row["id"],
                "scope": row["scope"],
                "started_at": row["started_at"],
                "terminated_processes": terminated_processes,
            }
        )
    return preempted


def should_pause_after_priority_request(conn: sqlite3.Connection, run_id: int, counts: dict[str, Any]) -> bool:
    row = conn.execute(
        """
        select counts_json
        from ingestion_runs
        where id = ? and status = 'running' and finished_at is null
        """,
        (run_id,),
    ).fetchone()
    if not row:
        counts["paused_after_priority_request"] = True
        return True
    stored_counts = parse_json_value(row["counts_json"], {})
    requested_at = stored_counts.get("priority_refresh_requested_at")
    if not requested_at:
        return False
    counts["paused_after_priority_request"] = True
    counts["priority_refresh_requested_at"] = requested_at
    counts["priority_refresh_symbol"] = stored_counts.get("priority_refresh_symbol", "")
    return True


def refresh_baostock_data(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    refresh_universe: bool = False,
    days: int = 260,
) -> dict[str, Any]:
    run_id = start_ingestion(conn, "baostock", "a-share-history", symbols or [], refresh_universe)
    conn.commit()
    errors: list[dict[str, str]] = []
    updated_symbols: list[str] = []
    counts = {"symbols": 0, "daily_bars": 0, "market_snapshots": 0}

    if refresh_universe or not symbols:
        try:
            counts["symbols"] += upsert_baostock_universe(conn, query_baostock_all_stock(latest_baostock_daily_trade_date()))
        except Exception as exc:
            errors.append({"scope": "baostock-universe", "error": str(exc)})

    target_symbols = normalize_symbols(conn, symbols or [])
    if not target_symbols:
        target_symbols = baostock_backfill_candidates(conn, limit=80)
    end_date = latest_baostock_daily_trade_date()
    start_date = baostock_history_start_date(end_date, days)
    if target_symbols:
        batch = refresh_baostock_history_batch(conn, target_symbols, start_date, end_date)
        counts["daily_bars"] += batch["daily_bars"]
        counts["market_snapshots"] += batch["market_snapshots"]
        updated_symbols.extend(batch["symbols"])
        errors.extend(batch["errors"])

    status = "ok" if updated_symbols or counts["symbols"] or counts["daily_bars"] else "partial"
    finish_ingestion(conn, run_id, status, updated_symbols, counts, errors)
    conn.commit()
    return {
        "status": status,
        "mode": "baostock-history",
        "run_id": run_id,
        "refreshed_at": now_iso(),
        "symbols": updated_symbols,
        "requested_symbols": target_symbols,
        "counts": counts,
        "errors": errors,
        "warehouse": warehouse_summary(conn),
    }


def create_baostock_backfill_job(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    refresh_universe: bool = True,
    days: int = 260,
    batch_size: int = 30,
) -> dict[str, Any]:
    stale_run_ids = mark_stale_running_ingestions(
        conn,
        "baostock",
        "a-share-history-background",
        stale_minutes=BAOSTOCK_BACKGROUND_STALE_MINUTES,
    )
    stale_processes = terminate_script_processes(BAOSTOCK_DAILY_SCRIPT_NAMES) if stale_run_ids else []
    if stale_run_ids:
        conn.commit()
    running = latest_running_ingestion(conn, "baostock", "a-share-history-background")
    if running:
        return {
            "status": "running",
            "mode": "baostock-backfill-background",
            "run_id": running["id"],
            "already_running": True,
            "stale_run_ids": stale_run_ids,
            "stale_processes": stale_processes,
            "job": ingestion_run_payload(conn, int(running["id"])),
            "warehouse": warehouse_summary(conn),
        }

    requested_symbols = normalize_symbols(conn, symbols or [])
    target_end = latest_baostock_daily_trade_date()
    target_start = baostock_history_start_date(target_end, days)
    run_id = start_ingestion(
        conn,
        "baostock",
        "a-share-history-background",
        requested_symbols,
        refresh_universe,
    )
    counts = {
        "symbols": 0,
        "daily_bars": 0,
        "market_snapshots": 0,
        "batches": 0,
        "batch_size": batch_size,
        "batch_sleep_seconds": BAOSTOCK_BATCH_SLEEP_SECONDS,
        "requested_symbol_count": len(requested_symbols),
        "remaining_candidates": (
            baostock_backfill_candidate_count(conn, days=days, start_date=target_start, end_date=target_end)
            if not requested_symbols
            else baostock_backfill_missing_symbol_count(
                conn,
                requested_symbols,
                days,
                start_date=target_start,
                end_date=target_end,
            )
        ),
        "days": days,
        "target_start": target_start,
        "target_end": target_end,
    }
    update_ingestion_progress(conn, run_id, [], counts, [])
    conn.commit()
    return {
        "status": "queued",
        "mode": "baostock-backfill-background",
        "run_id": run_id,
        "already_running": False,
        "stale_run_ids": stale_run_ids,
        "stale_processes": stale_processes,
        "counts": counts,
        "warehouse": warehouse_summary(conn),
    }


def run_baostock_backfill_job(
    run_id: int,
    symbols: list[str] | None = None,
    refresh_universe: bool = True,
    days: int = 260,
    batch_size: int = 30,
    batch_sleep_seconds: float = BAOSTOCK_BATCH_SLEEP_SECONDS,
    max_batches: int | None = None,
) -> None:
    updated_symbols: list[str] = []
    errors: list[dict[str, str]] = []
    counts: dict[str, Any] = {
        "symbols": 0,
        "daily_bars": 0,
        "market_snapshots": 0,
        "batches": 0,
        "batch_size": batch_size,
        "batch_sleep_seconds": batch_sleep_seconds,
        "days": days,
    }
    try:
        with get_db() as conn:
            requested_symbols = normalize_symbols(conn, symbols or [])
            counts["requested_symbol_count"] = len(requested_symbols)
            end_date = latest_baostock_daily_trade_date()
            start_date = baostock_history_start_date(end_date, days)
            counts["target_start"] = start_date
            counts["target_end"] = end_date
            if refresh_universe:
                try:
                    universe_rows = query_baostock_all_stock(end_date)
                    counts["symbols"] += upsert_baostock_universe(conn, universe_rows)
                except Exception as exc:
                    errors.append({"scope": "baostock-universe", "error": str(exc)})
                counts["remaining_candidates"] = (
                    baostock_backfill_candidate_count(conn, days=days, start_date=start_date, end_date=end_date)
                    if not requested_symbols
                    else baostock_backfill_missing_symbol_count(
                        conn,
                        requested_symbols,
                        days,
                        start_date=start_date,
                        end_date=end_date,
                    )
                )
                update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
                conn.commit()

            if requested_symbols:
                target_requested_symbols = baostock_backfill_missing_symbols(
                    conn,
                    requested_symbols,
                    days,
                    start_date=start_date,
                    end_date=end_date,
                )
                counts["missing_requested_symbol_count"] = len(target_requested_symbols)
                counts["remaining_candidates"] = len(target_requested_symbols)
                update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
                conn.commit()
                batches = chunked(target_requested_symbols, batch_size)
                for batch_symbols in batches:
                    if should_pause_after_priority_request(conn, run_id, counts):
                        break
                    apply_baostock_background_batch(
                        conn,
                        run_id,
                        batch_symbols,
                        start_date,
                        end_date,
                        counts,
                        updated_symbols,
                        errors,
                        remaining_scope_symbols=target_requested_symbols,
                        days=days,
                    )
                    if should_pause_after_daily_errors(counts):
                        break
                    if should_pause_after_daily_no_progress(counts):
                        break
                    if should_pause_baostock_backfill(counts, max_batches):
                        break
                    sleep_between_baostock_batches(batch_sleep_seconds)
            else:
                while True:
                    if should_pause_after_priority_request(conn, run_id, counts):
                        break
                    candidates = baostock_backfill_candidates(
                        conn,
                        limit=batch_size,
                        days=days,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    if not candidates:
                        counts["remaining_candidates"] = 0
                        update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
                        conn.commit()
                        break
                    apply_baostock_background_batch(conn, run_id, candidates, start_date, end_date, counts, updated_symbols, errors, days=days)
                    if should_pause_after_daily_errors(counts):
                        break
                    if should_pause_after_daily_no_progress(counts):
                        break
                    if should_pause_baostock_backfill(counts, max_batches):
                        break
                    sleep_between_baostock_batches(batch_sleep_seconds)

            if counts.get("paused_after_max_batches"):
                status = "partial"
            elif counts.get("paused_after_priority_request"):
                status = "partial"
            elif counts.get("paused_after_error_batches"):
                status = "partial"
            elif counts.get("paused_after_no_progress_batches"):
                status = "partial"
            else:
                status = "ok" if not errors else ("partial" if counts.get("daily_bars") or counts.get("symbols") else "failed")
            finish_ingestion(conn, run_id, status, updated_symbols, counts, errors)
            conn.commit()
    except Exception as exc:
        errors.append({"scope": "baostock-background-job", "error": str(exc)})
        with get_db() as conn:
            finish_ingestion(conn, run_id, "failed", updated_symbols, counts, errors)
            conn.commit()


def apply_baostock_background_batch(
    conn: sqlite3.Connection,
    run_id: int,
    batch_symbols: list[str],
    start_date: str,
    end_date: str,
    counts: dict[str, Any],
    updated_symbols: list[str],
    errors: list[dict[str, str]],
    remaining_scope_symbols: list[str] | None = None,
    days: int = 260,
) -> None:
    batch = refresh_baostock_history_batch(conn, batch_symbols, start_date, end_date)
    counts["daily_bars"] = counts.get("daily_bars", 0) + batch["daily_bars"]
    counts["market_snapshots"] = counts.get("market_snapshots", 0) + batch["market_snapshots"]
    counts["batches"] = counts.get("batches", 0) + 1
    counts["last_batch_symbol_count"] = len(batch_symbols)
    counts["remaining_candidates"] = (
        baostock_backfill_missing_symbol_count(
            conn,
            remaining_scope_symbols,
            days,
            start_date=start_date,
            end_date=end_date,
        )
        if remaining_scope_symbols is not None
        else baostock_backfill_candidate_count(conn, days=days, start_date=start_date, end_date=end_date)
    )
    if batch["daily_bars"] or batch["market_snapshots"]:
        counts["consecutive_error_batches"] = 0
        counts["consecutive_no_progress_batches"] = 0
    elif batch["errors"]:
        counts["consecutive_error_batches"] = int(counts.get("consecutive_error_batches") or 0) + 1
        counts["consecutive_no_progress_batches"] = int(counts.get("consecutive_no_progress_batches") or 0) + 1
    else:
        counts["consecutive_no_progress_batches"] = int(counts.get("consecutive_no_progress_batches") or 0) + 1
    updated_symbols.extend(batch["symbols"])
    errors.extend(batch["errors"])
    update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
    conn.commit()


def should_pause_baostock_backfill(counts: dict[str, Any], max_batches: int | None) -> bool:
    if not max_batches or max_batches <= 0:
        return False
    if int(counts.get("batches") or 0) < max_batches:
        return False
    counts["paused_after_max_batches"] = True
    return True


def should_pause_after_daily_errors(counts: dict[str, Any], max_error_batches: int = 3) -> bool:
    if int(counts.get("consecutive_error_batches") or 0) < max_error_batches:
        return False
    counts["paused_after_error_batches"] = True
    return True


def should_pause_after_daily_no_progress(counts: dict[str, Any], max_no_progress_batches: int = 3) -> bool:
    if int(counts.get("consecutive_no_progress_batches") or 0) < max_no_progress_batches:
        return False
    counts["paused_after_no_progress_batches"] = True
    return True


def should_pause_after_financial_errors(counts: dict[str, Any], max_error_batches: int = 3) -> bool:
    if int(counts.get("consecutive_error_batches") or 0) < max_error_batches:
        return False
    counts["paused_after_error_batches"] = True
    return True


def sleep_between_baostock_batches(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def create_baostock_financial_backfill_job(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    refresh_universe: bool = True,
    quarters: int = 12,
    batch_size: int = 10,
) -> dict[str, Any]:
    stale_run_ids = mark_stale_running_ingestions(
        conn,
        "baostock",
        "a-share-quarterly-financials-background",
        stale_minutes=BAOSTOCK_BACKGROUND_STALE_MINUTES,
    )
    stale_processes = terminate_script_processes(BAOSTOCK_FINANCIAL_SCRIPT_NAMES) if stale_run_ids else []
    if stale_run_ids:
        conn.commit()
    running = latest_running_ingestion(conn, "baostock", "a-share-quarterly-financials-background")
    if running:
        return {
            "status": "running",
            "mode": "baostock-quarterly-financials-background",
            "run_id": running["id"],
            "already_running": True,
            "stale_run_ids": stale_run_ids,
            "stale_processes": stale_processes,
            "job": ingestion_run_payload(conn, int(running["id"])),
            "warehouse": warehouse_summary(conn),
        }

    periods = recent_quarter_periods(quarters)
    requested_symbols = normalize_symbols(conn, symbols or [])
    run_id = start_ingestion(
        conn,
        "baostock",
        "a-share-quarterly-financials-background",
        requested_symbols,
        refresh_universe,
    )
    counts = {
        "symbols": 0,
        "financial_metrics": 0,
        "company_reports": 0,
        "batches": 0,
        "batch_size": batch_size,
        "quarters": quarters,
        "periods": [quarter_period_key(year, quarter) for year, quarter in periods],
        "report_periods": financial_storage_periods(periods),
        "requested_symbol_count": len(requested_symbols),
        "remaining_candidates": (
            baostock_financial_candidate_count(conn, periods)
            if not requested_symbols
            else baostock_financial_missing_symbol_count(conn, requested_symbols, periods)
        ),
    }
    update_ingestion_progress(conn, run_id, [], counts, [])
    conn.commit()
    return {
        "status": "queued",
        "mode": "baostock-quarterly-financials-background",
        "run_id": run_id,
        "already_running": False,
        "stale_run_ids": stale_run_ids,
        "stale_processes": stale_processes,
        "counts": counts,
        "warehouse": warehouse_summary(conn),
    }


def run_baostock_financial_backfill_job(
    run_id: int,
    symbols: list[str] | None = None,
    refresh_universe: bool = True,
    quarters: int = 12,
    batch_size: int = 10,
    max_batches: int | None = None,
) -> None:
    updated_symbols: list[str] = []
    errors: list[dict[str, str]] = []
    periods = recent_quarter_periods(quarters)
    counts: dict[str, Any] = {
        "symbols": 0,
        "financial_metrics": 0,
        "company_reports": 0,
        "batches": 0,
        "batch_size": batch_size,
        "quarters": quarters,
        "periods": [quarter_period_key(year, quarter) for year, quarter in periods],
        "report_periods": financial_storage_periods(periods),
    }
    try:
        with get_db() as conn:
            requested_symbols = normalize_symbols(conn, symbols or [])
            counts["requested_symbol_count"] = len(requested_symbols)
            if refresh_universe:
                try:
                    universe_rows = query_baostock_all_stock(latest_baostock_daily_trade_date())
                    counts["symbols"] += upsert_baostock_universe(conn, universe_rows)
                except Exception as exc:
                    errors.append({"scope": "baostock-universe", "error": str(exc)})
                counts["remaining_candidates"] = (
                    baostock_financial_candidate_count(conn, periods)
                    if not requested_symbols
                    else baostock_financial_missing_symbol_count(conn, requested_symbols, periods)
                )
                update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
                conn.commit()

            if requested_symbols:
                target_requested_symbols = baostock_financial_missing_symbols(conn, requested_symbols, periods)
                counts["missing_requested_symbol_count"] = len(target_requested_symbols)
                counts["remaining_candidates"] = len(target_requested_symbols)
                update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
                conn.commit()
                batches = chunked(target_requested_symbols, batch_size)
                for batch_symbols in batches:
                    if should_pause_after_priority_request(conn, run_id, counts):
                        break
                    apply_baostock_financial_background_batch(
                        conn,
                        run_id,
                        batch_symbols,
                        periods,
                        counts,
                        updated_symbols,
                        errors,
                        remaining_scope_symbols=target_requested_symbols,
                    )
                    if should_pause_after_financial_errors(counts):
                        break
                    if should_pause_baostock_backfill(counts, max_batches):
                        break
                    sleep_between_baostock_batches(BAOSTOCK_BATCH_SLEEP_SECONDS)
            else:
                while True:
                    if should_pause_after_priority_request(conn, run_id, counts):
                        break
                    candidates = baostock_financial_backfill_candidates(conn, periods, limit=batch_size)
                    if not candidates:
                        counts["remaining_candidates"] = 0
                        update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
                        conn.commit()
                        break
                    apply_baostock_financial_background_batch(conn, run_id, candidates, periods, counts, updated_symbols, errors)
                    if should_pause_after_financial_errors(counts):
                        break
                    if should_pause_baostock_backfill(counts, max_batches):
                        break
                    sleep_between_baostock_batches(BAOSTOCK_BATCH_SLEEP_SECONDS)

            if counts.get("paused_after_max_batches"):
                status = "partial"
            elif counts.get("paused_after_priority_request"):
                status = "partial"
            elif counts.get("paused_after_error_batches"):
                status = "partial"
            else:
                status = "ok" if not errors else ("partial" if counts.get("financial_metrics") or counts.get("company_reports") else "failed")
            finish_ingestion(conn, run_id, status, updated_symbols, counts, errors)
            conn.commit()
    except Exception as exc:
        errors.append({"scope": "baostock-quarterly-financials-job", "error": str(exc)})
        with get_db() as conn:
            finish_ingestion(conn, run_id, "failed", updated_symbols, counts, errors)
            conn.commit()


def apply_baostock_financial_background_batch(
    conn: sqlite3.Connection,
    run_id: int,
    batch_symbols: list[str],
    periods: list[tuple[int, int]],
    counts: dict[str, Any],
    updated_symbols: list[str],
    errors: list[dict[str, str]],
    remaining_scope_symbols: list[str] | None = None,
) -> None:
    batch = refresh_baostock_financial_batch(conn, batch_symbols, periods)
    counts["financial_metrics"] = counts.get("financial_metrics", 0) + batch["financial_metrics"]
    counts["company_reports"] = counts.get("company_reports", 0) + batch["company_reports"]
    counts["batches"] = counts.get("batches", 0) + 1
    counts["last_batch_symbol_count"] = len(batch_symbols)
    counts["remaining_candidates"] = (
        baostock_financial_missing_symbol_count(conn, remaining_scope_symbols, periods)
        if remaining_scope_symbols is not None
        else baostock_financial_candidate_count(conn, periods)
    )
    if batch["financial_metrics"] or batch["company_reports"]:
        counts["consecutive_error_batches"] = 0
    elif batch["errors"]:
        counts["consecutive_error_batches"] = int(counts.get("consecutive_error_batches") or 0) + 1
    updated_symbols.extend(batch["symbols"])
    errors.extend(batch["errors"])
    update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
    conn.commit()


def refresh_baostock_financial_batch(
    conn: sqlite3.Connection,
    symbols: list[str],
    periods: list[tuple[int, int]],
) -> dict[str, Any]:
    target_symbols = [symbol for symbol in symbols if is_baostock_supported_a_share(symbol)]
    skipped = [{"symbol": symbol, "error": "BaoStock 季频财务同步当前只处理沪深 .SH/.SZ 代码；北交所跳过"} for symbol in symbols if symbol not in target_symbols]
    if not target_symbols:
        return {"symbols": [], "financial_metrics": 0, "company_reports": 0, "errors": skipped}
    financial_plan = baostock_financial_backfill_plan(conn, target_symbols, periods)
    target_symbols = [symbol for symbol in target_symbols if financial_plan.get(symbol)]
    if not target_symbols:
        return {"symbols": [], "financial_metrics": 0, "company_reports": 0, "errors": skipped}

    errors: list[dict[str, str]] = [*skipped]
    financial_results: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {}
    report_results: dict[str, dict[str, list[dict[str, Any]]]] = {}
    failed_financial_periods: set[tuple[str, str]] = set()
    planned_periods = sorted(
        {period for symbol in target_symbols for period in financial_plan.get(symbol, [])},
        key=lambda item: quarter_end_date(item[0], item[1]),
    )
    try:
        financial_results, financial_errors = query_baostock_quarterly_financials_batch_guarded(
            target_symbols,
            periods,
            periods_by_symbol=financial_plan,
            timeout_seconds=baostock_financial_batch_timeout_seconds(target_symbols, planned_periods),
        )
        errors.extend(financial_errors)
        failed_financial_periods = {
            (str(item.get("symbol") or ""), str(item.get("period") or ""))
            for item in financial_errors
            if item.get("symbol") and item.get("period")
        }
    except BaostockError as exc:
        errors.append({"scope": "baostock-quarterly-financials-batch", "error": str(exc)})
        failed_financial_periods.update(
            (symbol, quarter_period_key(year, quarter))
            for symbol in target_symbols
            for year, quarter in financial_plan.get(symbol, [])
        )
    report_start = quarter_report_start_date(planned_periods)
    report_end = date.today().isoformat()
    try:
        report_results, report_errors = query_baostock_company_reports_batch_guarded(
            target_symbols,
            report_start,
            report_end,
            timeout_seconds=baostock_report_batch_timeout_seconds(target_symbols),
        )
        errors.extend(report_errors)
    except BaostockError as exc:
        errors.append({"scope": "baostock-company-reports-batch", "error": str(exc)})

    financial_count = upsert_baostock_financial_metrics(
        conn,
        financial_results,
        target_symbols,
        planned_periods,
        failed_financial_periods,
        requested_periods_by_symbol=financial_plan,
    )
    report_count = upsert_baostock_company_reports(conn, report_results)
    updated = sorted(set(target_symbols if financial_count else []) | set(report_results.keys()))
    return {
        "symbols": updated,
        "financial_metrics": financial_count,
        "company_reports": report_count,
        "errors": errors,
    }


def create_a_share_filings_backfill_job(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    refresh_universe: bool = True,
    source: str = "all",
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
    batch_size: int = 20,
) -> dict[str, Any]:
    filing_source = normalize_filing_source(source)
    stale_run_ids = mark_stale_running_ingestions(
        conn,
        A_SHARE_FILING_PROVIDER,
        "a-share-filings-background",
        stale_minutes=A_SHARE_FILING_BACKGROUND_STALE_MINUTES,
    )
    stale_processes = terminate_script_processes(A_SHARE_FILING_SCRIPT_NAMES) if stale_run_ids else []
    if stale_run_ids:
        conn.commit()
    running = latest_running_ingestion(conn, A_SHARE_FILING_PROVIDER, "a-share-filings-background")
    if running:
        return {
            "status": "running",
            "mode": "a-share-filings-background",
            "run_id": running["id"],
            "already_running": True,
            "stale_run_ids": stale_run_ids,
            "stale_processes": stale_processes,
            "job": ingestion_run_payload(conn, int(running["id"])),
            "warehouse": warehouse_summary(conn),
        }

    requested_symbols = normalize_symbols(conn, symbols or [])
    target_start, target_end = a_share_filing_date_range(days)
    run_id = start_ingestion(
        conn,
        A_SHARE_FILING_PROVIDER,
        f"a-share-filings-background:{filing_source}",
        requested_symbols,
        refresh_universe,
    )
    counts = {
        "symbols": 0,
        "filings": 0,
        "symbols_refreshed": 0,
        "no_data_symbols": 0,
        "failed_symbols": 0,
        "batches": 0,
        "batch_size": batch_size,
        "batch_sleep_seconds": A_SHARE_FILING_BATCH_SLEEP_SECONDS,
        "source": filing_source,
        "days": days,
        "target_start": target_start,
        "target_end": target_end,
        "requested_symbol_count": len(requested_symbols),
        "remaining_candidates": (
            a_share_filing_candidate_count(conn, source=filing_source, days=days, start_date=target_start, end_date=target_end)
            if not requested_symbols
            else a_share_filing_missing_symbol_count(
                conn,
                requested_symbols,
                source=filing_source,
                days=days,
                start_date=target_start,
                end_date=target_end,
            )
        ),
    }
    update_ingestion_progress(conn, run_id, [], counts, [])
    conn.commit()
    return {
        "status": "queued",
        "mode": "a-share-filings-background",
        "run_id": run_id,
        "already_running": False,
        "stale_run_ids": stale_run_ids,
        "stale_processes": stale_processes,
        "counts": counts,
        "warehouse": warehouse_summary(conn),
    }


def run_a_share_filings_backfill_job(
    run_id: int,
    symbols: list[str] | None = None,
    refresh_universe: bool = True,
    source: str = "all",
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
    batch_size: int = 20,
    batch_sleep_seconds: float = A_SHARE_FILING_BATCH_SLEEP_SECONDS,
    max_batches: int | None = None,
) -> None:
    filing_source = normalize_filing_source(source)
    updated_symbols: list[str] = []
    errors: list[dict[str, str]] = []
    target_start, target_end = a_share_filing_date_range(days)
    counts: dict[str, Any] = {
        "symbols": 0,
        "filings": 0,
        "symbols_refreshed": 0,
        "no_data_symbols": 0,
        "failed_symbols": 0,
        "batches": 0,
        "batch_size": batch_size,
        "batch_sleep_seconds": batch_sleep_seconds,
        "source": filing_source,
        "days": days,
        "target_start": target_start,
        "target_end": target_end,
    }
    try:
        with get_db() as conn:
            requested_symbols = normalize_symbols(conn, symbols or [])
            counts["requested_symbol_count"] = len(requested_symbols)
            if refresh_universe:
                try:
                    counts["symbols"] += upsert_baostock_universe(conn, query_baostock_all_stock(latest_baostock_daily_trade_date()))
                except Exception as exc:
                    errors.append({"scope": "a-share-filing-universe", "error": str(exc)})
                counts["remaining_candidates"] = (
                    a_share_filing_candidate_count(conn, source=filing_source, days=days, start_date=target_start, end_date=target_end)
                    if not requested_symbols
                    else a_share_filing_missing_symbol_count(
                        conn,
                        requested_symbols,
                        source=filing_source,
                        days=days,
                        start_date=target_start,
                        end_date=target_end,
                    )
                )
                update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
                conn.commit()

            if requested_symbols:
                target_requested_symbols = a_share_filing_missing_symbols(
                    conn,
                    requested_symbols,
                    source=filing_source,
                    days=days,
                    start_date=target_start,
                    end_date=target_end,
                )
                counts["missing_requested_symbol_count"] = len(target_requested_symbols)
                counts["remaining_candidates"] = len(target_requested_symbols)
                update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
                conn.commit()
                for batch_symbols in chunked(target_requested_symbols, batch_size):
                    apply_a_share_filings_background_batch(
                        conn,
                        run_id,
                        batch_symbols,
                        filing_source,
                        days,
                        counts,
                        updated_symbols,
                        errors,
                        remaining_scope_symbols=target_requested_symbols,
                    )
                    if should_pause_after_filing_errors(counts):
                        break
                    if should_pause_after_daily_no_progress(counts):
                        break
                    if should_pause_baostock_backfill(counts, max_batches):
                        break
                    sleep_between_baostock_batches(batch_sleep_seconds)
            else:
                while True:
                    candidates = a_share_filing_backfill_candidates(
                        conn,
                        source=filing_source,
                        limit=batch_size,
                        days=days,
                        start_date=target_start,
                        end_date=target_end,
                    )
                    if not candidates:
                        counts["remaining_candidates"] = 0
                        update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
                        conn.commit()
                        break
                    apply_a_share_filings_background_batch(conn, run_id, candidates, filing_source, days, counts, updated_symbols, errors)
                    if should_pause_after_filing_errors(counts):
                        break
                    if should_pause_after_daily_no_progress(counts):
                        break
                    if should_pause_baostock_backfill(counts, max_batches):
                        break
                    sleep_between_baostock_batches(batch_sleep_seconds)

            if counts.get("paused_after_max_batches"):
                status = "partial"
            elif counts.get("paused_after_error_batches"):
                status = "partial"
            elif counts.get("paused_after_no_progress_batches"):
                status = "partial"
            else:
                status = (
                    "ok"
                    if not errors
                    else ("partial" if counts.get("symbols_refreshed") or counts.get("filings") or counts.get("remaining_candidates") == 0 else "failed")
                )
            finish_ingestion(conn, run_id, status, updated_symbols, counts, errors)
            conn.commit()
    except Exception as exc:
        errors.append({"scope": "a-share-filings-background-job", "error": str(exc)})
        with get_db() as conn:
            finish_ingestion(conn, run_id, "failed", updated_symbols, counts, errors)
            conn.commit()


def apply_a_share_filings_background_batch(
    conn: sqlite3.Connection,
    run_id: int,
    batch_symbols: list[str],
    source: str,
    days: int,
    counts: dict[str, Any],
    updated_symbols: list[str],
    errors: list[dict[str, str]],
    remaining_scope_symbols: list[str] | None = None,
) -> None:
    batch = refresh_a_share_filings_batch(conn, batch_symbols, source=source, days=days)
    counts["filings"] = counts.get("filings", 0) + batch["filings"]
    counts["symbols_refreshed"] = counts.get("symbols_refreshed", 0) + len(batch["symbols"])
    counts["no_data_symbols"] = counts.get("no_data_symbols", 0) + len(batch["no_data_symbols"])
    counts["failed_symbols"] = counts.get("failed_symbols", 0) + len(batch["failed_symbols"])
    counts["batches"] = counts.get("batches", 0) + 1
    counts["last_batch_symbol_count"] = len(batch_symbols)
    counts["remaining_candidates"] = (
        a_share_filing_missing_symbol_count(conn, remaining_scope_symbols, source=source, days=days)
        if remaining_scope_symbols is not None
        else a_share_filing_candidate_count(conn, source=source, days=days)
    )
    if batch["symbols"] or batch["no_data_symbols"] or batch["filings"]:
        counts["consecutive_error_batches"] = 0
        counts["consecutive_no_progress_batches"] = 0
    elif batch["errors"]:
        counts["consecutive_error_batches"] = int(counts.get("consecutive_error_batches") or 0) + 1
        counts["consecutive_no_progress_batches"] = int(counts.get("consecutive_no_progress_batches") or 0) + 1
    else:
        counts["consecutive_no_progress_batches"] = int(counts.get("consecutive_no_progress_batches") or 0) + 1
    updated_symbols.extend(batch["symbols"])
    errors.extend(batch["errors"])
    update_ingestion_progress(conn, run_id, updated_symbols, counts, errors)
    conn.commit()


def refresh_a_share_filings_batch(
    conn: sqlite3.Connection,
    symbols: list[str],
    source: str = "all",
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
    page_size: int = 30,
    timeout: int = 15,
) -> dict[str, Any]:
    from .filings import search_filing_documents

    filing_source = normalize_filing_source(source)
    start_date, end_date = a_share_filing_date_range(days)
    refreshed_symbols: list[str] = []
    no_data_symbols: list[str] = []
    failed_symbols: list[str] = []
    errors: list[dict[str, str]] = []
    filing_count = 0

    for symbol in symbols:
        selected_sources = filing_sources_for_symbol(symbol, filing_source)
        if not selected_sources:
            failed_symbols.append(symbol)
            errors.append({"symbol": symbol, "source": filing_source, "error": "公告源不支持该证券代码"})
            continue
        try:
            payload = search_filing_documents(
                symbol=symbol,
                source=filing_source,
                start_date=start_date,
                end_date=end_date,
                page_size=page_size,
                timeout=timeout,
            )
        except Exception as exc:
            failed_symbols.append(symbol)
            update_filing_refresh_state(
                conn,
                symbol,
                filing_source,
                start_date,
                end_date,
                "failed",
                0,
                [{"source": filing_source, "message": str(exc)}],
            )
            errors.append({"symbol": symbol, "source": filing_source, "error": str(exc)})
            continue

        documents = payload.get("documents") or []
        payload_errors = payload.get("errors") or []
        inserted = upsert_filing_documents(conn, documents)
        filing_count += inserted
        if documents:
            refreshed_symbols.append(symbol)
            status = "partial" if payload_errors else "ok"
        elif payload_errors:
            failed_symbols.append(symbol)
            status = "failed"
        else:
            no_data_symbols.append(symbol)
            status = "no_data"
        update_filing_refresh_state(conn, symbol, filing_source, start_date, end_date, status, len(documents), payload_errors)
        for item in payload_errors:
            errors.append(
                {
                    "symbol": symbol,
                    "source": str(item.get("source") or filing_source),
                    "error": str(item.get("message") or item.get("error") or item),
                }
            )

    return {
        "symbols": refreshed_symbols,
        "no_data_symbols": no_data_symbols,
        "failed_symbols": failed_symbols,
        "filings": filing_count,
        "errors": errors,
    }


def should_pause_after_filing_errors(counts: dict[str, Any], max_error_batches: int = 3) -> bool:
    if int(counts.get("consecutive_error_batches") or 0) < max_error_batches:
        return False
    counts["paused_after_error_batches"] = True
    return True


def a_share_filing_candidate_count(
    conn: sqlite3.Connection,
    source: str = "all",
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
    start_date: str | None = None,
    end_date: str | None = None,
) -> int:
    return len(a_share_filing_backfill_plan(conn, a_share_filing_universe_symbols(conn, source), source, days, start_date, end_date))


def a_share_filing_backfill_candidates(
    conn: sqlite3.Connection,
    source: str = "all",
    limit: int = 20,
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[str]:
    plan = a_share_filing_backfill_plan(
        conn,
        a_share_filing_universe_symbols(conn, source),
        source,
        days,
        start_date,
        end_date,
    )
    return list(plan.keys())[:limit]


def a_share_filing_missing_symbol_count(
    conn: sqlite3.Connection,
    symbols: list[str],
    source: str = "all",
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
    start_date: str | None = None,
    end_date: str | None = None,
) -> int:
    return len(a_share_filing_backfill_plan(conn, symbols, source, days, start_date, end_date))


def a_share_filing_missing_symbols(
    conn: sqlite3.Connection,
    symbols: list[str],
    source: str = "all",
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[str]:
    plan = a_share_filing_backfill_plan(conn, symbols, source, days, start_date, end_date)
    return [symbol for symbol in symbols if plan.get(symbol)]


def a_share_filing_backfill_plan(
    conn: sqlite3.Connection,
    symbols: list[str],
    source: str = "all",
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, list[str]]:
    filing_source = normalize_filing_source(source)
    target_start, target_end = start_date or "", end_date or ""
    if not target_start or not target_end:
        target_start, target_end = a_share_filing_date_range(days)
    target_symbols = [symbol for symbol in symbols if filing_sources_for_symbol(symbol, filing_source)]
    if not target_symbols:
        return {}

    source_names = sorted({item for symbol in target_symbols for item in filing_sources_for_symbol(symbol, filing_source)})
    symbol_placeholders = ",".join("?" for _ in target_symbols)
    source_placeholders = ",".join("?" for _ in source_names)
    rows = conn.execute(
        f"""
        select symbol, source
        from filings_history
        where symbol in ({symbol_placeholders})
          and source in ({source_placeholders})
          and substr(published_at, 1, 10) >= ?
        group by symbol, source
        """,
        (*target_symbols, *source_names, target_start),
    ).fetchall()
    existing_sources: dict[str, set[str]] = {}
    for row in rows:
        existing_sources.setdefault(row["symbol"], set()).add(row["source"])

    state_rows = conn.execute(
        f"""
        select symbol, source, start_date, end_date, status, fetched_at
        from filing_refresh_state
        where symbol in ({symbol_placeholders})
          and source = ?
        """,
        (*target_symbols, filing_source),
    ).fetchall()
    state_by_symbol = {row["symbol"]: row_to_dict(row) for row in state_rows}
    retry_cutoff = filing_refresh_state_cutoff()
    plan: dict[str, list[str]] = {}
    for symbol in sorted(target_symbols, key=lambda item: (str(state_by_symbol.get(item, {}).get("fetched_at") or ""), item)):
        selected_sources = filing_sources_for_symbol(symbol, filing_source)
        missing_sources = [item for item in selected_sources if item not in existing_sources.get(symbol, set())]
        if not missing_sources:
            continue
        state = state_by_symbol.get(symbol)
        if (
            state
            and str(state.get("status") or "") in {"ok", "partial", "no_data"}
            and str(state.get("fetched_at") or "") >= retry_cutoff
            and str(state.get("start_date") or "") <= target_start
            and str(state.get("end_date") or "") >= target_end
        ):
            continue
        plan[symbol] = missing_sources
    return plan


def a_share_filing_universe_symbols(conn: sqlite3.Connection, source: str = "all") -> list[str]:
    filing_source = normalize_filing_source(source)
    suffix_filter = ""
    if filing_source == "sse":
        suffix_filter = "and symbol like '%.SH'"
    elif filing_source == "szse":
        suffix_filter = "and symbol like '%.SZ'"
    rows = conn.execute(
        f"""
        select symbol
        from symbols
        where market = 'A'
          and (symbol like '%.SH' or symbol like '%.SZ' or symbol like '%.BJ')
          {suffix_filter}
        order by symbol
        """,
    ).fetchall()
    return [row["symbol"] for row in rows]


def update_filing_refresh_state(
    conn: sqlite3.Connection,
    symbol: str,
    source: str,
    start_date: str,
    end_date: str,
    status: str,
    document_count: int,
    errors: list[dict[str, Any]],
) -> None:
    last_error = "; ".join(
        str(item.get("message") or item.get("error") or item)
        for item in errors[-3:]
    )[:800]
    conn.execute(
        """
        insert into filing_refresh_state (
          symbol, source, start_date, end_date, status, document_count, last_error, fetched_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(symbol, source) do update set
          start_date = excluded.start_date,
          end_date = excluded.end_date,
          status = excluded.status,
          document_count = excluded.document_count,
          last_error = excluded.last_error,
          fetched_at = excluded.fetched_at
        """,
        (symbol, source, start_date, end_date, status, document_count, last_error, now_iso()),
    )


def normalize_filing_source(source: str) -> str:
    value = str(source or "").strip().lower().replace("-", "_")
    if value in {"", "a_share_filings", "filings", "filing", "cn_exchange_filings", "cninfo_sse_szse"}:
        return "all"
    if value in {"all", "auto", "cninfo", "sse", "szse"}:
        return value
    return "all"


def filing_sources_for_symbol(symbol: str, source: str = "all") -> list[str]:
    filing_source = normalize_filing_source(source)
    normalized = symbol.upper()
    if not is_a_share(normalized):
        return []
    if filing_source == "cninfo":
        return ["cninfo"]
    if filing_source == "sse":
        return ["sse"] if normalized.endswith(".SH") else []
    if filing_source == "szse":
        return ["szse"] if normalized.endswith(".SZ") else []
    if filing_source == "auto":
        if normalized.endswith(".SH"):
            return ["sse"]
        if normalized.endswith(".SZ"):
            return ["szse"]
        return ["cninfo"]
    if normalized.endswith(".SH"):
        return ["cninfo", "sse"]
    if normalized.endswith(".SZ"):
        return ["cninfo", "szse"]
    return ["cninfo"]


def filing_refresh_state_cutoff() -> str:
    return (datetime.now() - timedelta(hours=A_SHARE_FILING_REFRESH_RETRY_HOURS)).isoformat(timespec="seconds")


def a_share_filing_date_range(days: int = A_SHARE_FILING_DEFAULT_DAYS) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=max(1, days))
    return start.isoformat(), end.isoformat()


def baostock_financial_batch_timeout_seconds(symbols: list[str], periods: list[tuple[int, int]]) -> float:
    override = timeout_override("KEIKO_BAOSTOCK_FINANCIAL_BATCH_TIMEOUT_SECONDS")
    if override is not None:
        return override
    call_count = max(1, len(symbols)) * max(1, len(periods)) * 6
    return min(900.0, max(90.0, call_count * 5.0))


def baostock_report_batch_timeout_seconds(symbols: list[str]) -> float:
    override = timeout_override("KEIKO_BAOSTOCK_REPORT_BATCH_TIMEOUT_SECONDS")
    if override is not None:
        return override
    call_count = max(1, len(symbols)) * 2
    return min(300.0, max(60.0, call_count * 10.0))


def timeout_override(name: str) -> float | None:
    value = os.environ.get(name)
    if not value:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def baostock_financial_candidate_count(conn: sqlite3.Connection, periods: list[tuple[int, int]]) -> int:
    report_periods = financial_storage_periods(periods)
    if not report_periods:
        return 0
    placeholders = ",".join("?" for _ in report_periods)
    row = conn.execute(
        f"""
        select count(*)
        from symbols s
        left join (
          select symbol, count(distinct report_period) as periods
          from financial_metrics_history
          where provider = ?
            and report_period in ({placeholders})
            and (
              not json_valid(raw_json)
              or coalesce(json_extract(raw_json, '$.status'), '') != 'no_data'
              or fetched_at >= ?
            )
          group by symbol
        ) f on f.symbol = s.symbol
        where s.market = 'A'
          and (s.symbol like '%.SH' or s.symbol like '%.SZ')
          and coalesce(f.periods, 0) < ?
        """,
        (BAOSTOCK_FINANCIAL_PROVIDER, *report_periods, baostock_financial_no_data_cutoff(), len(report_periods)),
    ).fetchone()
    return int(row[0] if row else 0)


def baostock_financial_backfill_candidates(
    conn: sqlite3.Connection,
    periods: list[tuple[int, int]],
    limit: int = 10,
) -> list[str]:
    report_periods = financial_storage_periods(periods)
    if not report_periods:
        return []
    placeholders = ",".join("?" for _ in report_periods)
    rows = conn.execute(
        f"""
        select s.symbol
        from symbols s
        left join (
          select symbol, count(distinct report_period) as periods
          from financial_metrics_history
          where provider = ?
            and report_period in ({placeholders})
            and (
              not json_valid(raw_json)
              or coalesce(json_extract(raw_json, '$.status'), '') != 'no_data'
              or fetched_at >= ?
            )
          group by symbol
        ) f on f.symbol = s.symbol
        where s.market = 'A'
          and (s.symbol like '%.SH' or s.symbol like '%.SZ')
          and coalesce(f.periods, 0) < ?
        order by coalesce(f.periods, 0), s.symbol
        limit ?
        """,
        (BAOSTOCK_FINANCIAL_PROVIDER, *report_periods, baostock_financial_no_data_cutoff(), len(report_periods), limit),
    ).fetchall()
    return [row["symbol"] for row in rows]


def baostock_financial_missing_symbol_count(
    conn: sqlite3.Connection,
    symbols: list[str],
    periods: list[tuple[int, int]],
) -> int:
    return len(baostock_financial_backfill_plan(conn, symbols, periods))


def baostock_financial_missing_symbols(
    conn: sqlite3.Connection,
    symbols: list[str],
    periods: list[tuple[int, int]],
) -> list[str]:
    plan = baostock_financial_backfill_plan(conn, symbols, periods)
    return [symbol for symbol in symbols if plan.get(symbol)]


def baostock_financial_backfill_plan(
    conn: sqlite3.Connection,
    symbols: list[str],
    periods: list[tuple[int, int]],
) -> dict[str, list[tuple[int, int]]]:
    report_period_by_tuple = {period: quarter_end_date(period[0], period[1]) for period in periods}
    if not symbols or not report_period_by_tuple:
        return {}
    symbol_placeholders = ",".join("?" for _ in symbols)
    period_values = list(report_period_by_tuple.values())
    period_placeholders = ",".join("?" for _ in period_values)
    rows = conn.execute(
        f"""
        select symbol, report_period
        from financial_metrics_history
        where provider = ?
          and symbol in ({symbol_placeholders})
          and report_period in ({period_placeholders})
          and (
            not json_valid(raw_json)
            or coalesce(json_extract(raw_json, '$.status'), '') != 'no_data'
            or fetched_at >= ?
          )
        """,
        (BAOSTOCK_FINANCIAL_PROVIDER, *symbols, *period_values, baostock_financial_no_data_cutoff()),
    ).fetchall()
    existing = {(row["symbol"], row["report_period"]) for row in rows}
    plan: dict[str, list[tuple[int, int]]] = {}
    for symbol in symbols:
        missing = [
            period
            for period, report_period in report_period_by_tuple.items()
            if (symbol, report_period) not in existing
        ]
        if missing:
            plan[symbol] = missing
    return plan


def baostock_financial_no_data_cutoff() -> str:
    return (datetime.now() - timedelta(days=BAOSTOCK_FINANCIAL_NO_DATA_RETRY_DAYS)).isoformat(timespec="seconds")


def baostock_backfill_candidate_count(
    conn: sqlite3.Connection,
    days: int = 260,
    start_date: str | None = None,
    end_date: str | None = None,
) -> int:
    return len(
        baostock_daily_backfill_plan(
            conn,
            baostock_daily_universe_symbols(conn),
            start_date=start_date,
            end_date=end_date,
            days=days,
        )
    )


def baostock_backfill_candidates(
    conn: sqlite3.Connection,
    limit: int = 80,
    days: int = 260,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[str]:
    symbols = baostock_daily_universe_symbols(conn)
    plan = baostock_daily_backfill_plan(conn, symbols, start_date=start_date, end_date=end_date, days=days)
    return list(plan.keys())[:limit]


def baostock_backfill_missing_symbol_count(
    conn: sqlite3.Connection,
    symbols: list[str],
    days: int = 260,
    start_date: str | None = None,
    end_date: str | None = None,
) -> int:
    return len(baostock_daily_backfill_plan(conn, symbols, start_date=start_date, end_date=end_date, days=days))


def baostock_backfill_missing_symbols(
    conn: sqlite3.Connection,
    symbols: list[str],
    days: int = 260,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[str]:
    plan = baostock_daily_backfill_plan(conn, symbols, start_date=start_date, end_date=end_date, days=days)
    return [symbol for symbol in symbols if plan.get(symbol)]


def baostock_daily_backfill_plan(
    conn: sqlite3.Connection,
    symbols: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
    days: int = 260,
) -> dict[str, list[tuple[str, str]]]:
    target_end = end_date or latest_baostock_daily_trade_date()
    target_start = start_date or baostock_history_start_date(target_end, days)
    if not symbols:
        return {}
    placeholders = ",".join("?" for _ in symbols)
    rows = conn.execute(
        f"""
        select
          s.symbol,
          count(distinct d.trade_date) as bars,
          min(d.trade_date) as first_date,
          max(d.trade_date) as latest_date
        from symbols s
        left join daily_bars d
          on d.symbol = s.symbol
         and d.provider = ?
        where s.symbol in ({placeholders})
        group by s.symbol
        order by coalesce(max(d.trade_date), ''), s.symbol
        """,
        (BAOSTOCK_MARKET_PROVIDER, *symbols),
    ).fetchall()
    plan: dict[str, list[tuple[str, str]]] = {}
    for row in rows:
        symbol = row["symbol"]
        bars = int(row["bars"] or 0)
        first_date = str(row["first_date"] or "")
        latest_date = str(row["latest_date"] or "")
        ranges: list[tuple[str, str]] = []
        if not latest_date:
            ranges.append((target_start, target_end))
            plan[symbol] = ranges
            continue
        if latest_date < target_end:
            ranges.append((next_calendar_date(latest_date), target_end))
        if bars < 120 and first_date and first_date > target_start:
            ranges.append((target_start, previous_calendar_date(first_date)))
        valid_ranges = [(start, end) for start, end in ranges if start <= end]
        if valid_ranges:
            plan[symbol] = valid_ranges
    return plan


def baostock_daily_universe_symbols(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        select symbol
        from symbols
        where market = 'A'
        and (symbol like '%.SH' or symbol like '%.SZ')
        order by symbol
        """,
    ).fetchall()
    return [row["symbol"] for row in rows]


def next_calendar_date(value: str) -> str:
    return (datetime.fromisoformat(value).date() + timedelta(days=1)).isoformat()


def previous_calendar_date(value: str) -> str:
    return (datetime.fromisoformat(value).date() - timedelta(days=1)).isoformat()


def refresh_baostock_history_batch(
    conn: sqlite3.Connection,
    symbols: list[str],
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    target_symbols = [symbol for symbol in symbols if is_baostock_supported_a_share(symbol)]
    skipped = [{"symbol": symbol, "error": "BaoStock 历史同步当前只处理沪深 .SH/.SZ 代码；北交所走 AKShare/Tushare"} for symbol in symbols if symbol not in target_symbols]
    if not target_symbols:
        return {"symbols": [], "daily_bars": 0, "market_snapshots": 0, "errors": skipped}
    date_ranges = baostock_daily_backfill_plan(conn, target_symbols, start_date=start_date, end_date=end_date)
    target_symbols = [symbol for symbol in target_symbols if date_ranges.get(symbol)]
    if not target_symbols:
        return {"symbols": [], "daily_bars": 0, "market_snapshots": 0, "errors": skipped}
    try:
        results, errors = query_baostock_history_batch(
            target_symbols,
            start_date,
            end_date,
            date_ranges_by_symbol=date_ranges,
        )
    except BaostockError as exc:
        return {
            "symbols": [],
            "daily_bars": 0,
            "market_snapshots": 0,
            "errors": [*skipped, {"scope": "baostock-history-batch", "error": str(exc)}],
        }
    updated_symbols = []
    daily_bars = 0
    snapshots = 0
    failed_symbols = {str(item.get("symbol") or "") for item in errors if item.get("symbol")}
    empty_errors: list[dict[str, str]] = []
    for symbol, rows in results.items():
        inserted = upsert_baostock_history(conn, rows)
        daily_bars += inserted
        snapshots += upsert_baostock_latest_snapshot(conn, symbol, rows)
        if inserted:
            updated_symbols.append(symbol)
        elif not rows and symbol not in failed_symbols:
            ranges = date_ranges.get(symbol) or []
            empty_errors.append(
                {
                    "symbol": symbol,
                    "error": "BaoStock returned no daily rows for requested ranges",
                    "ranges": ",".join(f"{start}..{end}" for start, end in ranges),
                }
            )
    return {
        "symbols": updated_symbols,
        "daily_bars": daily_bars,
        "market_snapshots": snapshots,
        "errors": [*skipped, *errors, *empty_errors],
    }


def upsert_baostock_financial_metrics(
    conn: sqlite3.Connection,
    results: dict[str, dict[str, dict[str, list[dict[str, Any]]]]],
    requested_symbols: list[str] | None = None,
    requested_periods: list[tuple[int, int]] | None = None,
    failed_periods: set[tuple[str, str]] | None = None,
    requested_periods_by_symbol: dict[str, list[tuple[int, int]]] | None = None,
) -> int:
    fetched_at = now_iso()
    columns = [
        "symbol",
        "report_period",
        "provider",
        "announce_date",
        "revenue_growth",
        "roe",
        "fcf_margin",
        "debt_ratio",
        "gross_margin",
        "net_margin",
        "net_profit",
        "eps_ttm",
        "mb_revenue",
        "total_share",
        "liqa_share",
        "nr_turn_ratio",
        "nr_turn_days",
        "inv_turn_ratio",
        "inv_turn_days",
        "ca_turn_ratio",
        "asset_turn_ratio",
        "yoy_equity",
        "yoy_asset",
        "yoy_ni",
        "yoy_eps_basic",
        "yoy_pni",
        "current_ratio",
        "quick_ratio",
        "cash_ratio",
        "yoy_liability",
        "liability_to_asset",
        "asset_to_equity",
        "ca_to_asset",
        "tangible_asset_to_asset",
        "ebit_to_interest",
        "operating_cash_flow_to_asset",
        "operating_cash_flow_to_debt",
        "dupont_roe",
        "dupont_asset_to_equity",
        "dupont_asset_turn",
        "dupont_pnitoni",
        "dupont_nitogr",
        "dupont_tax_burden",
        "dupont_int_burden",
        "dupont_ebit_to_gr",
        "raw_json",
        "fetched_at",
    ]
    payloads: list[dict[str, Any]] = []
    failed_periods = failed_periods or set()
    period_maps: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {
        symbol: {period: dict(sections) for period, sections in period_map.items()}
        for symbol, period_map in results.items()
    }
    if requested_symbols is not None and requested_periods is not None:
        for symbol in requested_symbols:
            period_map = period_maps.setdefault(symbol, {})
            symbol_periods = (
                requested_periods_by_symbol.get(symbol, requested_periods)
                if requested_periods_by_symbol
                else requested_periods
            )
            for year, quarter in symbol_periods:
                period_key = quarter_period_key(year, quarter)
                if (symbol, period_key) not in failed_periods:
                    period_map.setdefault(period_key, {})
    for symbol, period_map in period_maps.items():
        for period_key, sections in period_map.items():
            profit = first_section_row(sections, "profit")
            operation = first_section_row(sections, "operation")
            growth = first_section_row(sections, "growth")
            balance = first_section_row(sections, "balance")
            cash_flow = first_section_row(sections, "cash_flow")
            dupont = first_section_row(sections, "dupont")
            report_period = financial_report_period(sections, period_key)
            if not report_period:
                continue
            no_data = not any(sections.values())
            payloads.append(
                {
                    "symbol": symbol,
                    "report_period": report_period,
                    "provider": BAOSTOCK_FINANCIAL_PROVIDER,
                    "announce_date": financial_announce_date(sections),
                    "revenue_growth": None,
                    "roe": number_value(profit, ["roeAvg"]) or number_value(dupont, ["dupontROE"]),
                    "fcf_margin": None,
                    "debt_ratio": number_value(balance, ["liabilityToAsset"]),
                    "gross_margin": number_value(profit, ["gpMargin"]),
                    "net_margin": number_value(profit, ["npMargin"]),
                    "net_profit": number_value(profit, ["netProfit"]),
                    "eps_ttm": number_value(profit, ["epsTTM"]),
                    "mb_revenue": number_value(profit, ["MBRevenue"]),
                    "total_share": number_value(profit, ["totalShare"]),
                    "liqa_share": number_value(profit, ["liqaShare"]),
                    "nr_turn_ratio": number_value(operation, ["NRTurnRatio"]),
                    "nr_turn_days": number_value(operation, ["NRTurnDays"]),
                    "inv_turn_ratio": number_value(operation, ["INVTurnRatio"]),
                    "inv_turn_days": number_value(operation, ["INVTurnDays"]),
                    "ca_turn_ratio": number_value(operation, ["CATurnRatio"]),
                    "asset_turn_ratio": number_value(operation, ["AssetTurnRatio"]),
                    "yoy_equity": number_value(growth, ["YOYEquity"]),
                    "yoy_asset": number_value(growth, ["YOYAsset"]),
                    "yoy_ni": number_value(growth, ["YOYNI"]),
                    "yoy_eps_basic": number_value(growth, ["YOYEPSBasic"]),
                    "yoy_pni": number_value(growth, ["YOYPNI"]),
                    "current_ratio": number_value(balance, ["currentRatio"]),
                    "quick_ratio": number_value(balance, ["quickRatio"]),
                    "cash_ratio": number_value(balance, ["cashRatio"]),
                    "yoy_liability": number_value(balance, ["YOYLiability"]),
                    "liability_to_asset": number_value(balance, ["liabilityToAsset"]),
                    "asset_to_equity": number_value(balance, ["assetToEquity"]),
                    "ca_to_asset": number_value(cash_flow, ["CAToAsset"]),
                    "tangible_asset_to_asset": number_value(cash_flow, ["tangibleAssetToAsset"]),
                    "ebit_to_interest": number_value(cash_flow, ["ebitToInterest"]),
                    "operating_cash_flow_to_asset": number_value(cash_flow, ["operatingCashFlowToAsset"]),
                    "operating_cash_flow_to_debt": number_value(cash_flow, ["operatingCashFlowToDebt"]),
                    "dupont_roe": number_value(dupont, ["dupontROE"]),
                    "dupont_asset_to_equity": number_value(dupont, ["dupontAssetStoEquity", "dupontAssetToEquity"]),
                    "dupont_asset_turn": number_value(dupont, ["dupontAssetTurn"]),
                    "dupont_pnitoni": number_value(dupont, ["dupontPnitoni"]),
                    "dupont_nitogr": number_value(dupont, ["dupontNitogr"]),
                    "dupont_tax_burden": number_value(dupont, ["dupontTaxBurden"]),
                    "dupont_int_burden": number_value(dupont, ["dupontIntburden", "dupontIntBurden"]),
                    "dupont_ebit_to_gr": number_value(dupont, ["dupontEbittogr", "dupontEbitToGr"]),
                    "raw_json": json.dumps(
                        {
                            "period_key": period_key,
                            "status": "no_data" if no_data else "ok",
                            "sections": sections,
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                    "fetched_at": fetched_at,
                }
            )
    if not payloads:
        return 0
    placeholders = ", ".join(f":{column}" for column in columns)
    updates = ", ".join(
        f"{column} = excluded.{column}"
        for column in columns
        if column not in {"symbol", "report_period", "provider"}
    )
    conn.executemany(
        f"""
        insert into financial_metrics_history ({", ".join(columns)})
        values ({placeholders})
        on conflict(symbol, report_period, provider) do update set
          {updates}
        """,
        payloads,
    )
    return len(payloads)


def upsert_baostock_company_reports(
    conn: sqlite3.Connection,
    results: dict[str, dict[str, list[dict[str, Any]]]],
) -> int:
    fetched_at = now_iso()
    payloads: list[dict[str, Any]] = []
    for symbol, section_map in results.items():
        for report_type, rows in section_map.items():
            for row in rows:
                report_period = report_row_period(row)
                published_at = report_row_published_at(row)
                summary = report_row_summary(row)
                title = "BaoStock 业绩快报" if report_type == "performance_express" else "BaoStock 业绩预告"
                report_key = "|".join([report_type, report_period, published_at, summary[:160]])
                payloads.append(
                    {
                        "symbol": symbol,
                        "report_period": report_period,
                        "provider": BAOSTOCK_REPORT_PROVIDER,
                        "report_type": report_type,
                        "report_key": report_key,
                        "published_at": published_at,
                        "title": title,
                        "summary": summary,
                        "raw_json": json.dumps(row, ensure_ascii=False, default=str),
                        "fetched_at": fetched_at,
                    }
                )
    if not payloads:
        return 0
    conn.executemany(
        """
        insert into company_reports_history (
          symbol, report_period, provider, report_type, report_key,
          published_at, title, summary, raw_json, fetched_at
        )
        values (
          :symbol, :report_period, :provider, :report_type, :report_key,
          :published_at, :title, :summary, :raw_json, :fetched_at
        )
        on conflict(provider, symbol, report_type, report_key) do update set
          report_period = excluded.report_period,
          published_at = excluded.published_at,
          title = excluded.title,
          summary = excluded.summary,
          raw_json = excluded.raw_json,
          fetched_at = excluded.fetched_at
        """,
        payloads,
    )
    return len(payloads)


def first_section_row(sections: dict[str, list[dict[str, Any]]], section: str) -> dict[str, Any]:
    rows = sections.get(section) or []
    return rows[0] if rows else {}


def financial_report_period(sections: dict[str, list[dict[str, Any]]], period_key: str) -> str:
    for rows in sections.values():
        for row in rows:
            value = normalize_date(text_value(row, ["statDate", "endDate", "reportDate"]))
            if value:
                return value
    match = re.match(r"^(\d{4})Q([1-4])$", period_key)
    if not match:
        return period_key
    return quarter_end_date(int(match.group(1)), int(match.group(2)))


def financial_announce_date(sections: dict[str, list[dict[str, Any]]]) -> str:
    candidates = []
    for rows in sections.values():
        for row in rows:
            value = normalize_date(text_value(row, ["pubDate", "annDate", "announceDate"]))
            if value:
                candidates.append(value)
    return min(candidates) if candidates else ""


def report_row_period(row: dict[str, Any]) -> str:
    return normalize_date(
        text_value(
            row,
            [
                "statDate",
                "performanceExpStatDate",
                "profitForcastExpStatDate",
                "forecastStatDate",
                "endDate",
            ],
        )
    )


def report_row_published_at(row: dict[str, Any]) -> str:
    return normalize_date(
        text_value(
            row,
            [
                "pubDate",
                "updateDate",
                "performanceExpPubDate",
                "profitForcastExpPubDate",
                "annDate",
            ],
        )
    )


def report_row_summary(row: dict[str, Any]) -> str:
    values = [
        text_value(row, ["profitForcastType", "forecastType", "type"]),
        text_value(row, ["profitForcastAbstract", "forecastAbstract", "performanceExpressAbstract", "abstract"]),
    ]
    return "；".join(value for value in values if value)


def screen_from_database(
    conn: sqlite3.Connection,
    market: str,
    filter_ids: list[str],
    mode: str,
    natural_query: str = "",
    industry: str = "",
) -> list[dict[str, Any]]:
    where = ["1 = 1"]
    params: list[Any] = []
    normalized_market = market.upper()
    if normalized_market != "ALL":
        where.append("upper(s.market) = ?")
        params.append(normalized_market)
    clean_industry = industry.strip()
    if clean_industry:
        where.append("(s.industry = ? or s.sector = ?)")
        params.extend([clean_industry, clean_industry])

    conditions = [filter_sql(item) for item in filter_ids]
    conditions = [item for item in conditions if item]
    if conditions:
        joiner = " and " if mode != "any" else " or "
        where.append("(" + joiner.join(conditions) + ")")
    natural_conditions, natural_params = natural_filter_conditions(natural_query)
    if natural_conditions:
        where.append("(" + " and ".join(natural_conditions) + ")")
        params.extend(natural_params)

    sql = f"""
        with ranked_daily as (
          select
            d.*,
            row_number() over (
              partition by d.symbol
              order by
                d.trade_date desc,
                case d.provider
                  when 'tushare-market' then 5
                  when 'akshare-market' then 4
                  when 'baostock-market' then 3
                  when 'finnhub-market' then 2
                  else 1
                end desc,
                d.fetched_at desc
            ) as rn
          from daily_bars d
          where d.trade_date is not null and d.provider != 'mock-market'
        )
        select
          s.symbol, s.market, s.name, s.currency, s.exchange, s.sector, s.industry,
          d.trade_date, d.close, d.change_pct, d.volume, d.amount, d.turnover_rate,
          d.pe_ttm, d.pb
        from symbols s
        left join ranked_daily d on s.symbol = d.symbol and d.rn = 1
        where {' and '.join(where)}
        order by coalesce(d.amount, 0) desc, s.symbol
    """
    return [row_to_dict(row) for row in conn.execute(sql, params)]


def daily_bars_for_backtest(
    conn: sqlite3.Connection,
    market: str,
    start_date: str,
    end_date: str,
    limit_symbols: int = 80,
) -> dict[str, list[dict[str, Any]]]:
    normalized_market = market.upper()
    params: list[Any] = [start_date, end_date]
    market_filter = ""
    if normalized_market != "ALL":
        market_filter = "and upper(s.market) = ?"
        params.append(normalized_market)
    params.append(limit_symbols)
    symbol_rows = conn.execute(
        f"""
        select s.symbol
        from symbols s
        join daily_bars d on d.symbol = s.symbol
        where d.trade_date between ? and ?
          and d.provider != 'mock-market'
          {market_filter}
        group by s.symbol
        order by count(*) desc, max(coalesce(d.amount, 0)) desc
        limit ?
        """,
        params,
    ).fetchall()
    symbols = [row["symbol"] for row in symbol_rows]
    result: dict[str, list[dict[str, Any]]] = {}
    for symbol in symbols:
        rows = conn.execute(
            """
            with ranked_daily as (
              select
                trade_date, close, amount, turnover_rate, pe_ttm, pb, provider, fetched_at,
                row_number() over (
                  partition by trade_date
                  order by
                    trade_date desc,
                    case provider
                      when 'tushare-market' then 5
                      when 'akshare-market' then 4
                      when 'baostock-market' then 3
                      when 'finnhub-market' then 2
                      else 1
                    end desc,
                    fetched_at desc
                ) as rn
              from daily_bars
              where symbol = ? and trade_date between ? and ? and provider != 'mock-market'
            )
            select trade_date, close, amount, turnover_rate, pe_ttm, pb
            from ranked_daily
            where rn = 1
            order by trade_date
            """,
            (symbol, start_date, end_date),
        ).fetchall()
        if len(rows) >= 8:
            result[symbol] = [row_to_dict(row) for row in rows]
    return result


def filter_sql(filter_id: str) -> str:
    mapping = {
        "amount-high": "coalesce(d.amount, 0) >= 5000000000",
        "amount-active": "coalesce(d.amount, 0) >= 1000000000",
        "turnover-high": "coalesce(d.turnover_rate, 0) >= 1",
        "turnover-healthy": "coalesce(d.turnover_rate, 0) between 0.5 and 8",
        "spread-low": "1 = 1",
        "pe-positive": "d.pe_ttm is not null and d.pe_ttm > 0",
        "pe-low": "d.pe_ttm is not null and d.pe_ttm > 0 and d.pe_ttm <= 30",
        "pb-low": "d.pb is not null and d.pb > 0 and d.pb <= 3",
        "valuation-not-hot": "d.pe_ttm is not null and d.pe_ttm > 0 and d.pe_ttm <= 70",
        "roe-high": latest_financial_condition("coalesce(f.roe, 0) >= 15"),
        "revenue-growth-positive": latest_financial_condition("coalesce(f.revenue_growth, 0) > 0"),
        "gross-margin-high": latest_financial_condition("coalesce(f.gross_margin, 0) >= 30"),
        "cashflow-good": latest_financial_condition("coalesce(f.fcf_margin, 0) >= 5"),
        "debt-low": latest_financial_condition("coalesce(f.debt_ratio, f.liability_to_asset, 100) <= 60"),
        "trend-strong": "d.close > (select avg(close) from (select d2.close from daily_bars d2 where d2.symbol = d.symbol and d2.trade_date <= d.trade_date order by d2.trade_date desc limit 20))",
        "trend-medium": "d.close > (select avg(close) from (select d2.close from daily_bars d2 where d2.symbol = d.symbol and d2.trade_date <= d.trade_date order by d2.trade_date desc limit 60))",
        "near-52w-high": "d.close >= 0.8 * (select max(high) from (select d2.high from daily_bars d2 where d2.symbol = d.symbol and d2.trade_date <= d.trade_date order by d2.trade_date desc limit 252))",
        "volume-confirm": "coalesce(d.volume, 0) > (select avg(volume) * 1.2 from (select d2.volume from daily_bars d2 where d2.symbol = d.symbol and d2.trade_date <= d.trade_date order by d2.trade_date desc limit 20))",
        "catalyst-strong": "exists (select 1 from filings_history fh where fh.symbol = s.symbol and fh.published_at >= date(d.trade_date, '-30 day'))",
        "data-fresh": "d.trade_date = (select max(trade_date) from daily_bars)",
        "evidence-high": "exists (select 1 from filings_history fh where fh.symbol = s.symbol)",
        "rumor-low": "1 = 1",
    }
    return mapping.get(filter_id, "")


def latest_financial_condition(condition: str) -> str:
    return f"""
        exists (
          select 1
          from financial_metrics_history f
          where f.symbol = s.symbol
            and f.report_period = (
              select max(f2.report_period)
              from financial_metrics_history f2
              where f2.symbol = s.symbol
                and coalesce(f2.raw_json, '{{}}') not like '%"status": "no_data"%'
            )
            and {condition}
        )
    """


def natural_filter_conditions(query: str) -> tuple[list[str], list[Any]]:
    text = normalize_filter_query(query)
    if not text:
        return [], []

    conditions: list[str] = []
    params: list[Any] = []
    add_numeric_conditions(
        text,
        r"(?:\bpe\s*(?:ttm)?\b|市盈率)\s*(<=|<|>=|>|=)\s*(-?\d+(?:\.\d+)?)",
        "d.pe_ttm",
        conditions,
        params,
        positive=True,
    )
    add_numeric_conditions(
        text,
        r"(?:\bpb\s*(?:mrq)?\b|市净率)\s*(<=|<|>=|>|=)\s*(-?\d+(?:\.\d+)?)",
        "d.pb",
        conditions,
        params,
        positive=True,
    )
    add_amount_conditions(text, conditions, params)
    add_numeric_conditions(
        text,
        r"(?:换手率|turnover(?:_rate)?)\s*(<=|<|>=|>|=)\s*(-?\d+(?:\.\d+)?)\s*%?",
        "d.turnover_rate",
        conditions,
        params,
    )

    for keyword, filter_id in {
        "成交额高": "amount-high",
        "高成交额": "amount-high",
        "成交活跃": "amount-active",
        "换手率高": "turnover-high",
        "换手健康": "turnover-healthy",
        "pe为正": "pe-positive",
        "盈利": "pe-positive",
        "pe低": "pe-low",
        "估值低": "pe-low",
        "pb低": "pb-low",
        "营收增长": "revenue-growth-positive",
        "毛利率高": "gross-margin-high",
        "负债低": "debt-low",
        "站上20日线": "trend-strong",
        "站上60日线": "trend-medium",
        "趋势强": "trend-strong",
        "接近新高": "near-52w-high",
        "量能": "volume-confirm",
        "证据可信": "evidence-high",
        "数据fresh": "data-fresh",
        "数据新鲜": "data-fresh",
    }.items():
        if keyword in text:
            condition = filter_sql(filter_id)
            if condition and condition not in conditions:
                conditions.append(condition)
    add_text_conditions(
        text,
        r"(?:行业|板块)\s*(?:=|是|为|:|：)\s*([\u4e00-\u9fffA-Za-z0-9/_-]{2,20})",
        "s.industry",
        conditions,
        params,
    )
    return conditions, params


def normalize_filter_query(query: str) -> str:
    return (
        query.strip()
        .lower()
        .replace("≤", "<=")
        .replace("≥", ">=")
        .replace("＝", "=")
        .replace("＜", "<")
        .replace("＞", ">")
    )


def add_numeric_conditions(
    text: str,
    pattern: str,
    column: str,
    conditions: list[str],
    params: list[Any],
    positive: bool = False,
) -> None:
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        operator, raw_value = match.groups()
        value = float(raw_value)
        positivity = f" and {column} > 0" if positive else ""
        conditions.append(f"{column} is not null{positivity} and {column} {operator} ?")
        params.append(value)


def add_amount_conditions(text: str, conditions: list[str], params: list[Any]) -> None:
    pattern = r"(?:成交额|amount)\s*(<=|<|>=|>|=)\s*(-?\d+(?:\.\d+)?)\s*([亿万]?)"
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        operator, raw_value, unit = match.groups()
        value = float(raw_value)
        if unit == "亿":
            value *= 100000000
        elif unit == "万":
            value *= 10000
        conditions.append(f"d.amount is not null and d.amount {operator} ?")
        params.append(value)


def add_text_conditions(
    text: str,
    pattern: str,
    column: str,
    conditions: list[str],
    params: list[Any],
) -> None:
    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        value = str(match.group(1) or "").strip()
        if not value:
            continue
        conditions.append(f"{column} = ?")
        params.append(value)


def fetch_akshare_spot() -> list[dict[str, Any]]:
    import akshare as ak

    frame = ak.stock_zh_a_spot_em()
    return frame.to_dict("records")


def fetch_akshare_hist(symbol: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
    import akshare as ak

    frame = ak.stock_zh_a_hist(
        symbol=symbol.split(".")[0],
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq",
    )
    return frame.to_dict("records")


def fetch_tushare_universe(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    token = tushare_token(conn, DEFAULT_ACCOUNT_ID)
    if not token:
        raise HTTPException(status_code=400, detail="Tushare token 未配置，无法 fallback 同步股票列表")
    return TushareClient(token).stock_basic()


def refresh_baostock_history_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    try:
        rows = query_baostock_history(symbol, start_date, end_date)
    except BaostockError as exc:
        return {"daily_bars": 0, "market_snapshots": 0, "errors": [{"symbol": symbol, "error": str(exc)}]}
    inserted = upsert_baostock_history(conn, rows)
    snapshot = upsert_baostock_latest_snapshot(conn, symbol, rows)
    return {"daily_bars": inserted, "market_snapshots": snapshot, "errors": errors}


def upsert_baostock_universe(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    now = now_iso()
    symbols = []
    aliases = []
    for row in rows:
        raw_code = str(row.get("code") or "").strip()
        name = str(row.get("code_name") or row.get("name") or "").strip()
        security_type = str(row.get("type") or "")
        status = str(row.get("status") or row.get("tradeStatus") or "")
        if not raw_code or not name:
            continue
        symbol = standard_symbol(raw_code)
        if not is_a_share(symbol):
            continue
        symbols.append(
            {
                "symbol": symbol,
                "market": "A",
                "name": name,
                "currency": "CNY",
                "exchange": exchange_from_symbol(symbol),
                "sector": "A股",
                "industry": "",
            }
        )
        for alias in {symbol, symbol.split(".")[0], raw_code, name, pinyin_initials(name)}:
            aliases.append(
                {
                    "alias": alias,
                    "normalized_alias": alias.strip().lower().replace(" ", ""),
                    "symbol": symbol,
                    "source": "baostock",
                    "updated_at": now,
                }
            )
    conn.executemany(
        """
        insert into symbols (symbol, market, name, currency, exchange, sector, industry)
        values (:symbol, :market, :name, :currency, :exchange, :sector, :industry)
        on conflict(symbol) do update set
          name = excluded.name,
          market = excluded.market,
          currency = excluded.currency,
          exchange = excluded.exchange,
          sector = coalesce(nullif(symbols.sector, ''), excluded.sector),
          industry = coalesce(nullif(symbols.industry, ''), excluded.industry)
        """,
        symbols,
    )
    conn.executemany(
        """
        insert into symbol_aliases (alias, normalized_alias, symbol, source, updated_at)
        values (:alias, :normalized_alias, :symbol, :source, :updated_at)
        on conflict(normalized_alias, symbol) do update set
          alias = excluded.alias,
          source = excluded.source,
          updated_at = excluded.updated_at
        """,
        aliases,
    )
    return len(symbols)


def upsert_baostock_history(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    fetched_at = now_iso()
    payloads = []
    for row in rows:
        symbol = standard_symbol(text_value(row, ["code"]))
        trade_date = normalize_date(text_value(row, ["date"]))
        close = number_value(row, ["close"])
        if not is_a_share(symbol) or not trade_date or close is None:
            continue
        if text_value(row, ["tradestatus"]) not in {"", "1"}:
            continue
        payloads.append(
            {
                "symbol": symbol,
                "trade_date": trade_date,
                "provider": BAOSTOCK_MARKET_PROVIDER,
                "adjust": baostock_adjust_label(text_value(row, ["adjustflag"])),
                "open": number_value(row, ["open"]),
                "high": number_value(row, ["high"]),
                "low": number_value(row, ["low"]),
                "close": close,
                "pre_close": number_value(row, ["preclose"]),
                "change_pct": number_value(row, ["pctChg"]),
                "volume": number_value(row, ["volume"]),
                "amount": number_value(row, ["amount"]),
                "turnover_rate": number_value(row, ["turn"]),
                "pe_ttm": number_value(row, ["peTTM"]),
                "pb": number_value(row, ["pbMRQ"]),
                "ps_ttm": number_value(row, ["psTTM"]),
                "pcf_ncf_ttm": number_value(row, ["pcfNcfTTM"]),
                "is_st": integer_value(row, ["isST"]),
                "trade_status": text_value(row, ["tradestatus"]) or None,
                "raw_json": json.dumps(row, ensure_ascii=False, default=str),
                "fetched_at": fetched_at,
            }
        )
    upsert_daily_payloads(conn, payloads)
    return len(payloads)


def upsert_baostock_latest_snapshot(
    conn: sqlite3.Connection,
    symbol: str,
    rows: list[dict[str, Any]],
) -> int:
    candidates = [
        row
        for row in rows
        if standard_symbol(text_value(row, ["code"])) == symbol
        and normalize_date(text_value(row, ["date"]))
        and number_value(row, ["close"]) is not None
        and text_value(row, ["tradestatus"]) in {"", "1"}
    ]
    if not candidates:
        return 0
    latest = sorted(candidates, key=lambda row: normalize_date(text_value(row, ["date"])), reverse=True)[0]
    trade_date = normalize_date(text_value(latest, ["date"]))
    close = number_value(latest, ["close"])
    if close is None:
        return 0
    conn.execute(
        """
        insert into market_snapshots (
          symbol, provider, as_of, fetched_at, price, volume, amount,
          turnover_rate, spread_bps, raw_json, freshness_status
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            symbol,
            BAOSTOCK_MARKET_PROVIDER,
            f"{trade_date}T15:00:00+08:00",
            now_iso(),
            close,
            number_value(latest, ["volume"]) or 0,
            number_value(latest, ["amount"]) or 0,
            number_value(latest, ["turn"]) or 0,
            5,
            json.dumps(
                {
                    "daily": latest,
                    "daily_basic": {
                        "pe_ttm": number_value(latest, ["peTTM"]),
                        "pb": number_value(latest, ["pbMRQ"]),
                        "turnover_rate": number_value(latest, ["turn"]),
                    },
                    "change": number_value(latest, ["pctChg"]) or 0,
                    "volume_ratio": 1,
                    "pe": number_value(latest, ["peTTM"]),
                    "pb": number_value(latest, ["pbMRQ"]),
                },
                ensure_ascii=False,
                default=str,
            ),
            "fresh" if trade_date >= latest_baostock_daily_trade_date() else "warn",
        ),
    )
    return 1


def baostock_adjust_label(adjustflag: str) -> str:
    return {"1": "hfq", "2": "qfq", "3": ""}.get(str(adjustflag or ""), "")


def refresh_tushare_latest_trade_date(conn: sqlite3.Connection) -> dict[str, Any]:
    token = tushare_token(conn, DEFAULT_ACCOUNT_ID)
    if not token:
        raise HTTPException(status_code=400, detail="Tushare token 未配置，无法同步最新交易日")
    client = TushareClient(token)
    trade_date = latest_cn_trade_date().replace("-", "")
    basics = client.stock_basic()
    symbols_count = upsert_tushare_universe(conn, basics)
    daily_rows = client.query(
        "daily",
        params={"trade_date": trade_date},
        fields="ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
    ).rows
    errors: list[dict[str, str]] = []
    try:
        daily_basic_rows = client.query(
            "daily_basic",
            params={"trade_date": trade_date},
            fields=(
                "ts_code,trade_date,close,turnover_rate,turnover_rate_f,volume_ratio,"
                "pe,pe_ttm,pb,ps,ps_ttm,total_share,float_share,total_mv,circ_mv"
            ),
        ).rows
    except TushareError as exc:
        daily_basic_rows = []
        errors.append({"scope": "tushare-daily-basic", "error": str(exc)})
    inserted = upsert_tushare_daily_history(conn, daily_rows, daily_basic_rows)
    snapshots = upsert_tushare_latest_snapshots(conn, daily_rows, daily_basic_rows)
    return {
        "symbols": symbols_count,
        "daily_bars": inserted,
        "market_snapshots": snapshots,
        "symbols_updated": sorted({str(row.get("ts_code") or "").upper() for row in daily_rows if row.get("ts_code")}),
        "errors": errors,
    }


def refresh_tushare_history_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    token = tushare_token(conn, DEFAULT_ACCOUNT_ID)
    if not token:
        return {
            "daily_bars": 0,
            "market_snapshots": 0,
            "errors": [{"symbol": symbol, "error": "Tushare token 未配置，无法兜底历史行情"}],
        }
    client = TushareClient(token)
    errors: list[dict[str, str]] = []
    try:
        daily_rows = client.daily(symbol, start_date, end_date)
    except TushareError as exc:
        return {"daily_bars": 0, "market_snapshots": 0, "errors": [{"symbol": symbol, "error": str(exc)}]}
    try:
        daily_basic_rows = client.daily_basic(symbol, start_date, end_date)
    except TushareError as exc:
        daily_basic_rows = []
        errors.append({"symbol": symbol, "error": f"Tushare daily_basic 暂不可用：{exc}"})
    inserted = upsert_tushare_daily_history(conn, daily_rows, daily_basic_rows)
    snapshots = upsert_tushare_latest_snapshots(conn, daily_rows, daily_basic_rows, only_symbol=symbol)
    return {"daily_bars": inserted, "market_snapshots": snapshots, "errors": errors}


def upsert_tushare_daily_history(
    conn: sqlite3.Connection,
    daily_rows: list[dict[str, Any]],
    daily_basic_rows: list[dict[str, Any]],
) -> int:
    basic_by_key = {
        (str(row.get("ts_code") or "").upper(), str(row.get("trade_date") or "")): row
        for row in daily_basic_rows
        if row.get("ts_code") and row.get("trade_date")
    }
    fetched_at = now_iso()
    payloads = []
    for row in daily_rows:
        symbol = str(row.get("ts_code") or "").upper()
        raw_trade_date = str(row.get("trade_date") or "")
        close = number_value(row, ["close"])
        if not is_a_share(symbol) or not raw_trade_date or close is None:
            continue
        daily_basic = basic_by_key.get((symbol, raw_trade_date), {})
        payloads.append(
            {
                "symbol": symbol,
                "trade_date": normalize_date(raw_trade_date),
                "provider": TUSHARE_MARKET_PROVIDER,
                "adjust": "",
                "open": number_value(row, ["open"]),
                "high": number_value(row, ["high"]),
                "low": number_value(row, ["low"]),
                "close": close,
                "pre_close": number_value(row, ["pre_close"]),
                "change_pct": number_value(row, ["pct_chg"]),
                "volume": (number_value(row, ["vol"]) or 0) * 100,
                "amount": (number_value(row, ["amount"]) or 0) * 1000,
                "turnover_rate": number_value(daily_basic, ["turnover_rate", "turnover_rate_f"]),
                "pe_ttm": number_value(daily_basic, ["pe_ttm", "pe"]),
                "pb": number_value(daily_basic, ["pb"]),
                "ps_ttm": number_value(daily_basic, ["ps_ttm", "ps"]),
                "raw_json": json.dumps({"daily": row, "daily_basic": daily_basic}, ensure_ascii=False, default=str),
                "fetched_at": fetched_at,
            }
        )
    upsert_daily_payloads(conn, payloads)
    return len(payloads)


def upsert_tushare_latest_snapshots(
    conn: sqlite3.Connection,
    daily_rows: list[dict[str, Any]],
    daily_basic_rows: list[dict[str, Any]],
    only_symbol: str | None = None,
) -> int:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in daily_rows:
        symbol = str(row.get("ts_code") or "").upper()
        if not symbol or (only_symbol and symbol != only_symbol):
            continue
        grouped.setdefault(symbol, []).append(row)
    basic_by_key = {
        (str(row.get("ts_code") or "").upper(), str(row.get("trade_date") or "")): row
        for row in daily_basic_rows
        if row.get("ts_code") and row.get("trade_date")
    }
    payloads = []
    fetched_at = now_iso()
    for symbol, rows in grouped.items():
        daily = latest_row(rows, "trade_date")
        if not daily:
            continue
        raw_trade_date = str(daily.get("trade_date") or "")
        trade_date = normalize_date(raw_trade_date)
        close = number_value(daily, ["close"])
        if not trade_date or close is None:
            continue
        daily_basic = basic_by_key.get((symbol, raw_trade_date), {})
        payloads.append(
            (
                symbol,
                TUSHARE_MARKET_PROVIDER,
                f"{trade_date}T15:00:00+08:00",
                fetched_at,
                close,
                (number_value(daily, ["vol"]) or 0) * 100,
                (number_value(daily, ["amount"]) or 0) * 1000,
                number_value(daily_basic, ["turnover_rate", "turnover_rate_f"]) or 0,
                5,
                json.dumps(
                    {
                        "daily": daily,
                        "daily_basic": daily_basic,
                        "change": number_value(daily, ["pct_chg"]) or 0,
                        "volume_ratio": number_value(daily_basic, ["volume_ratio"]) or 1,
                        "pe": number_value(daily_basic, ["pe_ttm", "pe"]),
                        "pb": number_value(daily_basic, ["pb"]),
                    },
                    ensure_ascii=False,
                    default=str,
                ),
                "fresh" if trade_date >= latest_cn_trade_date() else "warn",
            )
        )
    conn.executemany(
        """
        insert into market_snapshots (
          symbol, provider, as_of, fetched_at, price, volume, amount,
          turnover_rate, spread_bps, raw_json, freshness_status
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payloads,
    )
    return len(payloads)


def upsert_tushare_universe(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    now = now_iso()
    symbols = []
    aliases = []
    for row in rows:
        symbol = str(row.get("ts_code") or "").upper()
        name = str(row.get("name") or "").strip()
        if not symbol or not name or not is_a_share(symbol):
            continue
        symbols.append(
            {
                "symbol": symbol,
                "market": "A",
                "name": name,
                "currency": row.get("curr_type") or "CNY",
                "exchange": row.get("exchange") or exchange_from_symbol(symbol),
                "sector": row.get("area") or "",
                "industry": row.get("industry") or row.get("market") or "",
            }
        )
        for alias in {symbol, symbol.split(".")[0], name, pinyin_initials(name)}:
            aliases.append(
                {
                    "alias": alias,
                    "normalized_alias": alias.strip().lower().replace(" ", ""),
                    "symbol": symbol,
                    "source": "tushare",
                    "updated_at": now,
                }
            )
    conn.executemany(
        """
        insert into symbols (symbol, market, name, currency, exchange, sector, industry)
        values (:symbol, :market, :name, :currency, :exchange, :sector, :industry)
        on conflict(symbol) do update set
          name = excluded.name,
          market = excluded.market,
          currency = excluded.currency,
          exchange = excluded.exchange,
          sector = excluded.sector,
          industry = excluded.industry
        """,
        symbols,
    )
    conn.executemany(
        """
        insert into symbol_aliases (alias, normalized_alias, symbol, source, updated_at)
        values (:alias, :normalized_alias, :symbol, :source, :updated_at)
        on conflict(normalized_alias, symbol) do update set
          alias = excluded.alias,
          source = excluded.source,
          updated_at = excluded.updated_at
        """,
        aliases,
    )
    return len(symbols)


def refresh_filings_for_symbol(
    conn: sqlite3.Connection,
    symbol: str,
    source: str = "all",
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
) -> int:
    batch = refresh_a_share_filings_batch(conn, [symbol], source=source, days=days)
    return int(batch.get("filings") or 0)


def refresh_filings_for_symbol_if_needed(
    conn: sqlite3.Connection,
    symbol: str,
    source: str = "all",
    days: int = A_SHARE_FILING_DEFAULT_DAYS,
) -> dict[str, Any]:
    start_date, end_date = a_share_filing_date_range(days)
    recent_failure = recent_filing_refresh_failure(conn, symbol, source, start_date, end_date)
    if recent_failure:
        return {
            "status": "skipped",
            "reason": recent_failure,
            "symbols": [],
            "no_data_symbols": [],
            "failed_symbols": [],
            "filings": 0,
            "errors": [],
        }
    plan = a_share_filing_backfill_plan(conn, [symbol], source, days, start_date, end_date)
    if not plan.get(symbol):
        return {
            "status": "skipped",
            "reason": f"filing_refresh_state/filings_history already covers {start_date}..{end_date}",
            "symbols": [],
            "no_data_symbols": [],
            "failed_symbols": [],
            "filings": 0,
            "errors": [],
        }
    batch = refresh_a_share_filings_batch(conn, [symbol], source=source, days=days)
    batch["status"] = "ok" if not batch.get("errors") else "partial"
    batch["planned_sources"] = plan.get(symbol, [])
    return batch


def recent_filing_refresh_failure(
    conn: sqlite3.Connection,
    symbol: str,
    source: str,
    start_date: str,
    end_date: str,
    cooldown_minutes: int = 10,
) -> str:
    filing_source = normalize_filing_source(source)
    row = conn.execute(
        """
        select status, start_date, end_date, fetched_at, last_error
        from filing_refresh_state
        where symbol = ? and source = ?
        """,
        (symbol, filing_source),
    ).fetchone()
    if not row or str(row["status"] or "") != "failed":
        return ""
    if str(row["start_date"] or "") > start_date or str(row["end_date"] or "") < end_date:
        return ""
    fetched_at = str(row["fetched_at"] or "")
    try:
        fetched = datetime.fromisoformat(fetched_at)
    except ValueError:
        return ""
    age_minutes = (datetime.now() - fetched).total_seconds() / 60
    if age_minutes <= cooldown_minutes:
        return f"recent filing refresh failed {int(age_minutes)} minutes ago; cooling down before retry"
    return ""


def upsert_filing_documents(conn: sqlite3.Connection, documents: list[dict[str, Any]]) -> int:
    fetched_at = now_iso()
    rows = []
    for doc in documents:
        symbol = str(doc.get("symbol") or "").upper()
        title = str(doc.get("title") or "").strip()
        url = str(doc.get("url") or "").strip()
        if not symbol or not title or not url:
            continue
        rows.append(
            {
                "symbol": symbol,
                "source": str(doc.get("source") or ""),
                "published_at": str(doc.get("published_at") or ""),
                "title": title,
                "url": url,
                "category": str(doc.get("category") or ""),
                "source_tier": str(doc.get("source_tier") or "S"),
                "raw_json": json.dumps(doc, ensure_ascii=False, default=str),
                "fetched_at": fetched_at,
            }
        )
    conn.executemany(
        """
        insert into filings_history (
          symbol, source, published_at, title, url, category, source_tier, raw_json, fetched_at
        )
        values (
          :symbol, :source, :published_at, :title, :url, :category, :source_tier, :raw_json, :fetched_at
        )
        on conflict(source, symbol, url) do update set
          published_at = excluded.published_at,
          title = excluded.title,
          category = excluded.category,
          source_tier = excluded.source_tier,
          raw_json = excluded.raw_json,
          fetched_at = excluded.fetched_at
        """,
        rows,
    )
    return len(rows)


def upsert_akshare_universe(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    now = now_iso()
    symbols: list[dict[str, Any]] = []
    aliases: list[dict[str, str]] = []
    for row in rows:
        code = text_value(row, ["代码", "code", "股票代码"])
        name = text_value(row, ["名称", "name", "股票简称"])
        if not code or not name:
            continue
        symbol = normalize_a_symbol(code)
        symbols.append(
            {
                "symbol": symbol,
                "market": "A",
                "name": name,
                "currency": "CNY",
                "exchange": exchange_from_symbol(symbol),
                "sector": "",
                "industry": "",
            }
        )
        for alias in {symbol, code, name, pinyin_initials(name)}:
            aliases.append(
                {
                    "alias": alias,
                    "normalized_alias": alias.strip().lower().replace(" ", ""),
                    "symbol": symbol,
                    "source": "akshare",
                    "updated_at": now,
                }
            )
    conn.executemany(
        """
        insert into symbols (symbol, market, name, currency, exchange, sector, industry)
        values (:symbol, :market, :name, :currency, :exchange, :sector, :industry)
        on conflict(symbol) do update set
          name = excluded.name,
          market = excluded.market,
          currency = excluded.currency,
          exchange = excluded.exchange
        """,
        symbols,
    )
    conn.executemany(
        """
        insert into symbol_aliases (alias, normalized_alias, symbol, source, updated_at)
        values (:alias, :normalized_alias, :symbol, :source, :updated_at)
        on conflict(normalized_alias, symbol) do update set
          alias = excluded.alias,
          source = excluded.source,
          updated_at = excluded.updated_at
        """,
        aliases,
    )
    return len(symbols)


def upsert_spot_daily_bars(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    trade_date = latest_cn_trade_date()
    fetched_at = now_iso()
    payloads = []
    for row in rows:
        code = text_value(row, ["代码", "code", "股票代码"])
        if not code:
            continue
        close = number_value(row, ["最新价", "收盘", "close"])
        if close is None or close <= 0:
            continue
        payloads.append(
            {
                "symbol": normalize_a_symbol(code),
                "trade_date": trade_date,
                "provider": AKSHARE_MARKET_PROVIDER,
                "adjust": "",
                "open": number_value(row, ["今开", "开盘"]),
                "high": number_value(row, ["最高"]),
                "low": number_value(row, ["最低"]),
                "close": close,
                "pre_close": None,
                "change_pct": number_value(row, ["涨跌幅"]),
                "volume": number_value(row, ["成交量"]),
                "amount": number_value(row, ["成交额"]),
                "turnover_rate": number_value(row, ["换手率"]),
                "pe_ttm": number_value(row, ["市盈率-动态", "市盈率(TTM)", "市盈率"]),
                "pb": number_value(row, ["市净率"]),
                "raw_json": json.dumps(row, ensure_ascii=False, default=str),
                "fetched_at": fetched_at,
            }
        )
    upsert_daily_payloads(conn, payloads)
    return len(payloads)


def upsert_spot_market_snapshots(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    as_of = f"{latest_cn_trade_date()}T15:00:00+08:00"
    fetched_at = now_iso()
    payloads = []
    for row in rows:
        code = text_value(row, ["代码", "code", "股票代码"])
        close = number_value(row, ["最新价", "收盘", "close"])
        if not code or close is None or close <= 0:
            continue
        payloads.append(
            (
                normalize_a_symbol(code),
                AKSHARE_MARKET_PROVIDER,
                as_of,
                fetched_at,
                close,
                number_value(row, ["成交量"]) or 0,
                number_value(row, ["成交额"]) or 0,
                number_value(row, ["换手率"]) or 0,
                5,
                json.dumps(
                    {
                        "spot": row,
                        "change": number_value(row, ["涨跌幅"]) or 0,
                        "volume_ratio": 1,
                        "pe": number_value(row, ["市盈率-动态", "市盈率(TTM)", "市盈率"]),
                        "pb": number_value(row, ["市净率"]),
                    },
                    ensure_ascii=False,
                    default=str,
                ),
                "fresh",
            )
        )
    conn.executemany(
        """
        insert into market_snapshots (
          symbol, provider, as_of, fetched_at, price, volume, amount,
          turnover_rate, spread_bps, raw_json, freshness_status
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payloads,
    )
    return len(payloads)


def upsert_akshare_history(conn: sqlite3.Connection, symbol: str, rows: list[dict[str, Any]]) -> int:
    fetched_at = now_iso()
    payloads = []
    for row in rows:
        trade_date = normalize_date(text_value(row, ["日期", "date", "trade_date"]))
        close = number_value(row, ["收盘", "close"])
        if not trade_date or close is None:
            continue
        payloads.append(
            {
                "symbol": symbol,
                "trade_date": trade_date,
                "provider": AKSHARE_MARKET_PROVIDER,
                "adjust": "qfq",
                "open": number_value(row, ["开盘", "open"]),
                "high": number_value(row, ["最高", "high"]),
                "low": number_value(row, ["最低", "low"]),
                "close": close,
                "pre_close": None,
                "change_pct": number_value(row, ["涨跌幅", "pct_chg"]),
                "volume": number_value(row, ["成交量", "volume"]),
                "amount": number_value(row, ["成交额", "amount"]),
                "turnover_rate": number_value(row, ["换手率", "turnover"]),
                "pe_ttm": None,
                "pb": None,
                "raw_json": json.dumps(row, ensure_ascii=False, default=str),
                "fetched_at": fetched_at,
            }
        )
    upsert_daily_payloads(conn, payloads)
    return len(payloads)


def upsert_latest_history_snapshot(conn: sqlite3.Connection, symbol: str, row: dict[str, Any]) -> None:
    trade_date = normalize_date(text_value(row, ["日期", "date", "trade_date"]))
    close = number_value(row, ["收盘", "close"])
    if not trade_date or close is None:
        return
    raw = {
        "daily": row,
        "change": number_value(row, ["涨跌幅", "pct_chg"]) or 0,
        "volume_ratio": 1,
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
            AKSHARE_MARKET_PROVIDER,
            f"{trade_date}T15:00:00+08:00",
            now_iso(),
            close,
            number_value(row, ["成交量", "volume"]) or 0,
            number_value(row, ["成交额", "amount"]) or 0,
            number_value(row, ["换手率", "turnover"]) or 0,
            5,
            json.dumps(raw, ensure_ascii=False, default=str),
            "fresh" if trade_date >= latest_cn_trade_date() else "warn",
        ),
    )


def upsert_daily_payloads(conn: sqlite3.Connection, payloads: list[dict[str, Any]]) -> None:
    defaults = {
        "ps_ttm": None,
        "pcf_ncf_ttm": None,
        "is_st": None,
        "trade_status": None,
    }
    rows = [{**defaults, **payload} for payload in payloads]
    conn.executemany(
        """
        insert into daily_bars (
          symbol, trade_date, provider, adjust, open, high, low, close, pre_close,
          change_pct, volume, amount, turnover_rate, pe_ttm, pb, ps_ttm,
          pcf_ncf_ttm, is_st, trade_status, raw_json, fetched_at
        )
        values (
          :symbol, :trade_date, :provider, :adjust, :open, :high, :low, :close, :pre_close,
          :change_pct, :volume, :amount, :turnover_rate, :pe_ttm, :pb, :ps_ttm,
          :pcf_ncf_ttm, :is_st, :trade_status, :raw_json, :fetched_at
        )
        on conflict(symbol, trade_date, provider, adjust) do update set
          open = excluded.open,
          high = excluded.high,
          low = excluded.low,
          close = excluded.close,
          pre_close = excluded.pre_close,
          change_pct = excluded.change_pct,
          volume = excluded.volume,
          amount = excluded.amount,
          turnover_rate = excluded.turnover_rate,
          pe_ttm = coalesce(excluded.pe_ttm, daily_bars.pe_ttm),
          pb = coalesce(excluded.pb, daily_bars.pb),
          ps_ttm = coalesce(excluded.ps_ttm, daily_bars.ps_ttm),
          pcf_ncf_ttm = coalesce(excluded.pcf_ncf_ttm, daily_bars.pcf_ncf_ttm),
          is_st = coalesce(excluded.is_st, daily_bars.is_st),
          trade_status = coalesce(excluded.trade_status, daily_bars.trade_status),
          raw_json = excluded.raw_json,
          fetched_at = excluded.fetched_at
        """,
        rows,
    )


def normalize_symbols(conn: sqlite3.Connection, symbols: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in symbols:
        text = item.strip()
        if not text:
            continue
        resolved = resolve_symbol(conn, text)
        symbol = str(resolved["symbol"]).upper() if resolved else (infer_symbol(text.upper()) or text.upper())
        if symbol not in seen:
            seen.add(symbol)
            normalized.append(symbol)
    return normalized


def start_ingestion(
    conn: sqlite3.Connection,
    provider: str,
    scope: str,
    symbols: list[str],
    refresh_universe: bool,
) -> int:
    cursor = conn.execute(
        """
        insert into ingestion_runs (provider, scope, status, started_at, requested_symbols)
        values (?, ?, 'running', ?, ?)
        """,
        (
            provider,
            f"{scope}:universe" if refresh_universe else scope,
            now_iso(),
            json.dumps(symbols, ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def update_ingestion_progress(
    conn: sqlite3.Connection,
    run_id: int,
    updated_symbols: list[str],
    counts: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    counts["last_progress_at"] = now_iso()
    conn.execute(
        """
        update ingestion_runs
        set status = 'running', updated_symbols = ?, counts_json = ?, errors_json = ?
        where id = ? and status = 'running' and finished_at is null
        """,
        (
            json.dumps(updated_symbols, ensure_ascii=False),
            json.dumps(counts, ensure_ascii=False),
            json.dumps(errors, ensure_ascii=False),
            run_id,
        ),
    )


def finish_ingestion(
    conn: sqlite3.Connection,
    run_id: int,
    status: str,
    updated_symbols: list[str],
    counts: dict[str, Any],
    errors: list[dict[str, str]],
) -> None:
    finished_at = now_iso()
    counts["last_progress_at"] = finished_at
    conn.execute(
        """
        update ingestion_runs
        set status = ?, finished_at = ?, updated_symbols = ?, counts_json = ?, errors_json = ?
        where id = ? and status = 'running'
        """,
        (
            status,
            finished_at,
            json.dumps(updated_symbols, ensure_ascii=False),
            json.dumps(counts, ensure_ascii=False),
            json.dumps(errors, ensure_ascii=False),
            run_id,
        ),
    )


def mark_stale_running_ingestions(
    conn: sqlite3.Connection,
    provider: str,
    scope_prefix: str,
    stale_minutes: int,
) -> list[int]:
    rows = conn.execute(
        """
        select *
        from ingestion_runs
        where provider = ? and scope like ? and status = 'running'
        order by id
        """,
        (provider, f"{scope_prefix}%"),
    ).fetchall()
    stale_run_ids: list[int] = []
    for row in rows:
        item = row_to_dict(row)
        counts = parse_json_value(item.get("counts_json"), {})
        heartbeat = str(counts.get("last_progress_at") or item.get("started_at") or "")
        if not ingestion_heartbeat_is_stale(heartbeat, stale_minutes):
            continue
        errors = parse_json_value(item.get("errors_json"), [])
        updated_symbols = parse_json_value(item.get("updated_symbols"), [])
        counts["stale_detected_at"] = now_iso()
        counts["stale_after_minutes"] = stale_minutes
        errors.append(
            {
                "scope": "background-heartbeat",
                "error": f"No progress heartbeat for at least {stale_minutes} minutes; marked interrupted so a new backfill can resume.",
            }
        )
        finish_ingestion(conn, int(item["id"]), "interrupted", updated_symbols, counts, errors)
        stale_run_ids.append(int(item["id"]))
    return stale_run_ids


def ingestion_heartbeat_is_stale(value: str, stale_minutes: int) -> bool:
    if not value:
        return True
    try:
        heartbeat = datetime.fromisoformat(value)
    except ValueError:
        return True
    return datetime.now() - heartbeat >= timedelta(minutes=stale_minutes)


def latest_running_ingestion(conn: sqlite3.Connection, provider: str, scope_prefix: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        select *
        from ingestion_runs
        where provider = ? and scope like ? and status = 'running'
        order by id desc
        limit 1
        """,
        (provider, f"{scope_prefix}%"),
    ).fetchone()
    return row_to_dict(row) if row else None


def ingestion_run_payload(
    conn: sqlite3.Connection,
    run_id: int,
    include_symbols: bool = False,
    symbol_limit: int = 50,
) -> dict[str, Any]:
    row = conn.execute("select * from ingestion_runs where id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="ingestion run not found")
    item = row_to_dict(row)
    requested_symbols = parse_json_value(item.get("requested_symbols"), [])
    updated_symbols = parse_json_value(item.get("updated_symbols"), [])
    payload = {
        "id": item["id"],
        "provider": item["provider"],
        "scope": item["scope"],
        "status": item["status"],
        "started_at": item["started_at"],
        "finished_at": item["finished_at"],
        "requested_symbol_count": len(requested_symbols),
        "updated_symbol_count": len(updated_symbols),
        "requested_symbols_sample": requested_symbols[:symbol_limit],
        "updated_symbols_sample": updated_symbols[-symbol_limit:],
        "counts": parse_json_value(item.get("counts_json"), {}),
        "errors": parse_json_value(item.get("errors_json"), []),
        "warehouse": warehouse_summary(conn),
    }
    if include_symbols:
        payload["requested_symbols"] = requested_symbols
        payload["updated_symbols"] = updated_symbols
    return payload


def parse_json_value(value: Any, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), max(size, 1))]


def scalar_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"select count(*) from {table}").fetchone()[0])


def scalar_value(conn: sqlite3.Connection, sql: str) -> Any:
    row = conn.execute(sql).fetchone()
    return row[0] if row else None


def latest_cn_trade_date() -> str:
    today = date.today()
    while today.weekday() >= 5:
        today -= timedelta(days=1)
    return today.isoformat()


def latest_baostock_daily_trade_date(now: datetime | None = None) -> str:
    current = now or datetime.now()
    candidate = current.date()
    if candidate.weekday() < 5 and current.time() >= datetime_time(17, 30):
        return candidate.isoformat()
    candidate -= timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate.isoformat()


def baostock_history_start_date(end_date: str, days: int) -> str:
    return (datetime.fromisoformat(end_date).date() - timedelta(days=days)).isoformat()


def recent_quarter_periods(count: int = 12, today: date | None = None) -> list[tuple[int, int]]:
    current = today or date.today()
    year = current.year
    quarter = ((current.month - 1) // 3) + 1
    while quarter_report_due_date(year, quarter) > current:
        quarter -= 1
        if quarter == 0:
            quarter = 4
            year -= 1
    periods: list[tuple[int, int]] = []
    for _ in range(max(count, 0)):
        periods.append((year, quarter))
        quarter -= 1
        if quarter == 0:
            quarter = 4
            year -= 1
    return periods


def quarter_period_key(year: int, quarter: int) -> str:
    return f"{year}Q{quarter}"


def quarter_report_due_date(year: int, quarter: int) -> date:
    if quarter == 1:
        return date(year, 4, 30)
    if quarter == 2:
        return date(year, 8, 31)
    if quarter == 3:
        return date(year, 10, 31)
    return date(year + 1, 4, 30)


def financial_storage_periods(periods: list[tuple[int, int]]) -> list[str]:
    return [quarter_end_date(year, quarter) for year, quarter in periods]


def quarter_end_date(year: int, quarter: int) -> str:
    month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}.get(quarter, "12-31")
    return f"{year}-{month_day}"


def quarter_report_start_date(periods: list[tuple[int, int]]) -> str:
    if not periods:
        return (date.today() - timedelta(days=365 * 3)).isoformat()
    oldest = periods[-1]
    return quarter_end_date(oldest[0], oldest[1])


def normalize_a_symbol(code: str) -> str:
    clean = str(code).strip().upper().replace(".", "")
    if clean.endswith(("SH", "SZ", "BJ")) and len(clean) >= 8:
        clean = clean[:6]
    if clean.startswith(("5", "6", "9")):
        return f"{clean}.SH"
    if clean.startswith(("4", "8")):
        return f"{clean}.BJ"
    return f"{clean}.SZ"


def exchange_from_symbol(symbol: str) -> str:
    if symbol.endswith(".SH"):
        return "SSE"
    if symbol.endswith(".SZ"):
        return "SZSE"
    if symbol.endswith(".BJ"):
        return "BSE"
    return "A股"


def is_a_share(symbol: str) -> bool:
    return symbol.endswith((".SH", ".SZ", ".BJ"))


def is_baostock_supported_a_share(symbol: str) -> bool:
    return symbol.endswith((".SH", ".SZ"))


def normalize_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) >= 10 and "-" in text:
        return text[:10]
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return text


def text_value(row: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def number_value(row: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, "", "-"):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def integer_value(row: dict[str, Any], keys: list[str]) -> int | None:
    value = number_value(row, keys)
    return int(value) if value is not None else None
