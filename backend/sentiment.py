from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from .accounts import favorite_symbols_for_accounts
from .db import ROOT_DIR, now_iso, row_to_dict
from .providers.community import crawl_community_posts, normalize_community_source, upsert_community_posts, xueqiu_configured
from .providers.xueqiu import fetch_xueqiu_quote
from .stock_detail import preferred_daily_bars
from .symbol_resolver import infer_symbol, resolve_symbol


SENTIMENT_PROMPT_VERSION = "prompt-20260613-guba-v9"
DEFAULT_SENTIMENT_ACCOUNT_ID = "acct-admin"
SENTIMENT_METHOD_VERSION = f"sentiment-v4-{SENTIMENT_PROMPT_VERSION}"
LOCAL_MODEL_NAME = "fallback-v1"
COMMUNITY_SCORE_MIN = -100.0
COMMUNITY_SCORE_MAX = 100.0
COMMUNITY_SCORE_LEGACY_MULTIPLIER = 50.0
COMMUNITY_SENTIMENT_CLASSES = ("正面", "偏正面", "中性", "偏负面", "负面")
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
DEEPSEEK_ENV_NAMES = ("DEEPSEEK_API_KEY", "KEIKO_DEEPSEEK_API_KEY")
GLM_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_ENV_NAMES = ("GLM_API_KEY", "ZHIPU_API_KEY", "BIGMODEL_API_KEY", "KEIKO_GLM_API_KEY")
ENV_FILE = ROOT_DIR / ".env"
DEFAULT_COMMUNITY_LIMIT = 120
DEFAULT_SENTIMENT_EVIDENCE_LIMIT = 120
COMMUNITY_DETAIL_RETENTION_DAYS = 3
ENABLE_COMMUNITY_DAILY_CONCLUSION = False
LLM_CACHE_TTL_MINUTES = 30
LLM_BATCH_SIZE = 24
LLM_COMMUNITY_BATCH_SIZE = 10
LLM_COMMUNITY_RETRY_BATCH_SIZE = 5
LLM_COMMUNITY_TEXT_LIMIT = 100
LLM_MAX_CONCURRENCY = 2
LLM_BATCH_TIMEOUT_SECONDS = 25
LLM_COMMUNITY_TIMEOUT_SECONDS = 40
SENTIMENT_CYCLE_TIMEOUT_SECONDS = 1200.0
SENTIMENT_SYMBOL_BATCH_SIZE = 10


def refresh_sentiment(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    days: int = 30,
    use_llm: bool = True,
    crawl_community: bool = False,
    community_limit: int = DEFAULT_COMMUNITY_LIMIT,
    evidence_limit: int = DEFAULT_SENTIMENT_EVIDENCE_LIMIT,
    account_id: str | None = None,
    favorites_only: bool = False,
    analyze_filing_news: bool = False,
    cycle_deadline: float | None = None,
) -> dict[str, Any]:
    total_started = time.monotonic()
    performance = new_sentiment_performance()
    target_symbols, symbol_source = resolve_sentiment_target_symbols(
        conn,
        symbols or [],
        days=days,
        account_id=account_id,
        favorites_only=favorites_only,
    )

    counts = {
        "symbols": 0,
        "filing_news_evidence": 0,
        "community_evidence": 0,
        "community_posts_today": 0,
        "market_evidence": 0,
        "community_posts_crawled": 0,
        "community_posts": 0,
        "snapshots": 0,
    }
    errors: list[dict[str, str]] = []
    refreshed: list[str] = []
    refreshed_set: set[str] = set()
    batch_size = sentiment_symbol_batch_size()

    for batch in chunked_symbols(target_symbols, batch_size):
        if cycle_deadline_exceeded(cycle_deadline):
            errors.append(
                cycle_timeout_error(
                    cycle_deadline,
                    "sentiment-refresh",
                    pending_symbols=[symbol for symbol in target_symbols if symbol not in refreshed_set],
                )
            )
            break

        workers = min(batch_size, len(batch))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _refresh_sentiment_symbol_task,
                    symbol,
                    days=days,
                    use_llm=use_llm,
                    crawl_community=crawl_community,
                    community_limit=community_limit,
                    evidence_limit=evidence_limit,
                    analyze_filing_news=analyze_filing_news,
                ): symbol
                for symbol in batch
            }
            for future in as_completed(futures):
                task = future.result()
                symbol = str(task.get("symbol") or "")
                if not task.get("ok"):
                    errors.append({"symbol": symbol, "error": str(task.get("error") or "sentiment refresh failed")})
                    continue
                result = task.get("result") or {}
                merge_sentiment_performance(performance, result.get("performance") or {}, symbol=symbol)
                for key in ("filing_news_evidence", "community_evidence", "market_evidence", "snapshots"):
                    counts[key] += int((result.get("counts") or {}).get(key, 0))
                counts["community_posts_today"] += int((result.get("counts") or {}).get("community_evidence", 0))
                crawl_counts = task.get("crawl_counts") or {}
                counts["community_posts_crawled"] += int(crawl_counts.get("community_posts_crawled") or 0)
                counts["community_posts"] += int(crawl_counts.get("community_posts") or 0)
                errors.extend(task.get("crawl_errors") or [])
                counts["symbols"] += 1
                if symbol and symbol not in refreshed_set:
                    refreshed_set.add(symbol)
                    refreshed.append(symbol)

        if cycle_deadline_exceeded(cycle_deadline):
            errors.append(
                cycle_timeout_error(
                    cycle_deadline,
                    "sentiment-refresh",
                    pending_symbols=[symbol for symbol in target_symbols if symbol not in refreshed_set],
                )
            )
            break

    refreshed = [symbol for symbol in target_symbols if symbol in refreshed_set]
    performance["total_ms"] = elapsed_ms(total_started)
    llm_stats = performance.get("llm") or {}
    return {
        "mode": "sentiment-refresh",
        "method_version": SENTIMENT_METHOD_VERSION,
        "prompt_version": SENTIMENT_PROMPT_VERSION,
        "days": clean_days(days),
        "use_llm": bool(use_llm),
        "analyze_filing_news": bool(analyze_filing_news),
        "llm_configured": bool(preferred_llm_config()["configured"]),
        "llm_provider": preferred_llm_config()["provider"],
        "symbol_source": symbol_source,
        "account_id": sentiment_account_id(account_id),
        "symbols": refreshed,
        "counts": counts,
        "errors": errors,
        "performance": performance,
        "usage": summarize_llm_usage(llm_stats),
        "parallel_batch_size": batch_size,
        "refreshed_at": now_iso(),
    }


def _refresh_sentiment_symbol_task(
    symbol: str,
    *,
    days: int,
    use_llm: bool,
    crawl_community: bool,
    community_limit: int,
    evidence_limit: int,
    analyze_filing_news: bool,
) -> dict[str, Any]:
    from .db import get_db

    try:
        with get_db() as conn:
            crawl_counts = {"community_posts_crawled": 0, "community_posts": 0}
            crawl_errors: list[dict[str, str]] = []
            crawl_started = 0.0
            if crawl_community:
                crawl_started = time.monotonic()
                crawl = crawl_community_for_symbols(conn, [symbol], limit=community_limit)
                crawled = int(crawl["counts"].get("posts", 0))
                crawl_counts = {"community_posts_crawled": crawled, "community_posts": crawled}
                crawl_errors = list(crawl.get("errors") or [])
            result = refresh_symbol_sentiment(
                conn,
                symbol,
                days=days,
                use_llm=use_llm,
                evidence_limit=evidence_limit,
                analyze_filing_news=analyze_filing_news,
            )
            performance = result.get("performance") or new_sentiment_performance()
            if crawl_community:
                record_sentiment_step(
                    performance,
                    "community-crawl",
                    crawl_started,
                    {"symbol": symbol, "posts": int(crawl_counts.get("community_posts_crawled") or 0)},
                )
                result["performance"] = performance
            conn.commit()
        return {
            "ok": True,
            "symbol": str(result.get("symbol") or symbol),
            "result": result,
            "crawl_counts": crawl_counts,
            "crawl_errors": crawl_errors,
        }
    except Exception as exc:
        return {"ok": False, "symbol": symbol, "error": str(exc)}


def refresh_symbol_sentiment(
    conn: sqlite3.Connection,
    symbol: str,
    days: int = 30,
    use_llm: bool = True,
    evidence_limit: int = DEFAULT_SENTIMENT_EVIDENCE_LIMIT,
    analyze_filing_news: bool = False,
) -> dict[str, Any]:
    total_started = time.monotonic()
    performance = new_sentiment_performance()
    normalized = normalize_symbol(conn, symbol)
    if not normalized:
        raise HTTPException(status_code=404, detail="symbol not found")

    filing_news_count = 0
    if analyze_filing_news:
        started = time.monotonic()
        filing_news_count = analyze_filing_news_sentiment(
            conn,
            normalized,
            days=days,
            use_llm=use_llm,
            limit=evidence_limit,
            stats=performance["llm"],
        )
        record_sentiment_step(performance, "filing_news-analysis", started, {"rows": filing_news_count})

    started = time.monotonic()
    community_count = analyze_community_sentiment(
        conn,
        normalized,
        days=days,
        use_llm=use_llm,
        limit=evidence_limit,
        stats=performance["llm"],
    )
    record_sentiment_step(performance, "community-analysis", started, {"rows": community_count})

    started = time.monotonic()
    market_count = analyze_market_sentiment(conn, normalized, days=days)
    record_sentiment_step(performance, "market-analysis", started, {"rows": market_count})

    started = time.monotonic()
    snapshot = upsert_sentiment_snapshot(conn, normalized, days=days)
    record_sentiment_step(performance, "snapshot", started)
    performance["total_ms"] = elapsed_ms(total_started)
    return {
        "symbol": normalized,
        "snapshot": snapshot,
        "counts": {
            "filing_news_evidence": filing_news_count,
            "community_evidence": community_count,
            "market_evidence": market_count,
            "snapshots": 1 if snapshot else 0,
        },
        "performance": performance,
    }


def sentiment_payload(conn: sqlite3.Connection, symbol: str, days: int = 30, evidence_limit: int = 30) -> dict[str, Any]:
    normalized = normalize_symbol(conn, symbol)
    if not normalized:
        raise HTTPException(status_code=404, detail="symbol not found")
    symbol_row = conn.execute("select * from symbols where symbol = ?", (normalized,)).fetchone()
    snapshot_row = resolve_sentiment_snapshot_row(conn, normalized, window_days=days)
    evidence = sentiment_evidence_payload(conn, normalized, days=days, limit=evidence_limit)
    snapshot = apply_current_community_snapshot(conn, decode_snapshot(snapshot_row)) if snapshot_row else None
    return {
        "mode": "sentiment-payload",
        "symbol": row_to_dict(symbol_row) if symbol_row else {"symbol": normalized},
        "snapshot": snapshot,
        "evidence": evidence,
        "community_daily": community_daily_summaries(conn, normalized, days=days),
        "data_status": {
            "has_snapshot": bool(snapshot_row),
            "evidence_rows": sum(len(items) for items in evidence.values()),
            "window_days": clean_days(days),
        },
    }


def sentiment_status(conn: sqlite3.Connection) -> dict[str, Any]:
    latest_snapshots = conn.execute(
        """
        select symbol, max(generated_at) as latest_generated_at, count(*) as snapshots
        from sentiment_snapshots
        group by symbol
        order by latest_generated_at desc
        limit 20
        """
    ).fetchall()
    return {
        "mode": "sentiment-status",
        "method_version": SENTIMENT_METHOD_VERSION,
        "prompt_version": SENTIMENT_PROMPT_VERSION,
        "llm": llm_config_status(mask=True),
        "community_sources": {
            "default": "xueqiu",
            "xueqiu_configured": xueqiu_configured(),
        },
        "counts": {
            "community_posts": scalar_count(conn, "community_posts"),
            "sentiment_evidence": scalar_count(conn, "sentiment_evidence"),
            "sentiment_snapshots": scalar_count(conn, "sentiment_snapshots"),
            "community_sentiment_daily": scalar_count(conn, "community_sentiment_daily"),
        },
        "latest_snapshots": [row_to_dict(row) for row in latest_snapshots],
        "recent_agent_runs": recent_sentiment_agent_runs(conn, limit=10),
    }


def community_daily_payload(conn: sqlite3.Connection, symbol: str, days: int = 30) -> dict[str, Any]:
    normalized = normalize_symbol(conn, symbol)
    if not normalized:
        raise HTTPException(status_code=404, detail="symbol not found")
    return {
        "mode": "community-sentiment-daily",
        "symbol": normalized,
        "days": clean_days(days),
        "rows": community_daily_summaries(conn, normalized, days=days),
    }


def refresh_community_daily_summaries(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    day: str | None = None,
    use_llm: bool = True,
    llm_stats: dict[str, Any] | None = None,
    cycle_deadline: float | None = None,
) -> dict[str, Any]:
    trade_date = normalize_day(day) or date.today().isoformat()
    target_symbols = normalize_symbols(conn, symbols or [])
    if not target_symbols:
        target_symbols = community_daily_candidate_symbols(conn, trade_date)

    summaries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for symbol in target_symbols:
        if cycle_deadline_exceeded(cycle_deadline):
            errors.append(cycle_timeout_error(cycle_deadline, "community-daily", pending_symbols=target_symbols[len(summaries):]))
            break
        try:
            summary = upsert_community_daily_summary(conn, symbol, trade_date, use_llm=use_llm, llm_stats=llm_stats)
            if summary:
                summaries.append(summary)
        except Exception as exc:
            errors.append({"symbol": symbol, "trade_date": trade_date, "error": str(exc)})
    conn.commit()
    return {
        "mode": "community-daily-summary-refresh",
        "method_version": SENTIMENT_METHOD_VERSION,
        "prompt_version": SENTIMENT_PROMPT_VERSION,
        "trade_date": trade_date,
        "symbols": [item["symbol"] for item in summaries],
        "counts": {"symbols": len(summaries), "errors": len(errors)},
        "summaries": summaries,
        "errors": errors,
        "refreshed_at": now_iso(),
    }


def _empty_sentiment_refresh_result() -> dict[str, Any]:
    return {
        "mode": "sentiment-refresh",
        "symbols": [],
        "counts": {},
        "errors": [],
        "performance": new_sentiment_performance(),
    }


def _finish_skipped_community_sentiment_cycle(
    conn: sqlite3.Connection,
    run_id: int,
    *,
    symbol_source: str,
    account_id: str | None,
    reason: str,
    retention_days: int,
) -> dict[str, Any]:
    from .history import finish_ingestion

    cleanup = cleanup_expired_community_sentiment(conn, retention_days=retention_days)
    result = {
        "mode": "community-sentiment-cycle",
        "method_version": SENTIMENT_METHOD_VERSION,
        "prompt_version": SENTIMENT_PROMPT_VERSION,
        "symbol_source": symbol_source,
        "account_id": sentiment_account_id(account_id),
        "symbols": [],
        "skipped": True,
        "reason": reason,
        "live_refresh": {"symbols": [], "counts": {}, "errors": []},
        "sentiment": {
            "mode": "sentiment-refresh",
            "symbols": [],
            "counts": {},
            "errors": [],
            "performance": new_sentiment_performance(),
        },
        "daily": {"counts": {"symbols": 0}, "errors": []},
        "cleanup": cleanup,
        "refreshed_at": now_iso(),
    }
    usage = build_agent_usage(result)
    finish_ingestion(conn, run_id, "skipped", [], usage, [])
    conn.commit()
    result["run_id"] = run_id
    result["usage"] = usage
    return result


def run_community_sentiment_cycle(
    conn: sqlite3.Connection,
    symbols: list[str] | None = None,
    use_llm: bool = True,
    community_limit: int = DEFAULT_COMMUNITY_LIMIT,
    evidence_limit: int = DEFAULT_SENTIMENT_EVIDENCE_LIMIT,
    analysis_days: int = 30,
    retention_days: int = COMMUNITY_DETAIL_RETENTION_DAYS,
    refresh_market: bool = True,
    refresh_filings: bool = True,
    market_days: int = 20,
    account_id: str | None = None,
    favorites_only: bool = True,
    respect_watchlist_schedule: bool = False,
    cycle_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    from .history import finish_ingestion, start_ingestion
    from .market_calendar import cn_now, is_sentiment_watchlist_refresh_window

    explicit_symbols = bool(symbols)
    if (
        respect_watchlist_schedule
        and favorites_only
        and not explicit_symbols
        and not is_sentiment_watchlist_refresh_window()
    ):
        current = cn_now()
        run_id = start_ingestion(
            conn,
            "community-sentiment-agent",
            "account_favorites",
            [],
            refresh_universe=False,
        )
        return _finish_skipped_community_sentiment_cycle(
            conn,
            run_id,
            symbol_source="account_favorites",
            account_id=account_id,
            reason=f"outside watchlist refresh window (08:00-24:00 Asia/Shanghai, now {current.strftime('%H:%M')})",
            retention_days=retention_days,
        )

    target_symbols, symbol_source = resolve_sentiment_target_symbols(
        conn,
        symbols or [],
        days=analysis_days,
        account_id=account_id,
        favorites_only=favorites_only,
    )
    run_id = start_ingestion(
        conn,
        "community-sentiment-agent",
        symbol_source,
        target_symbols,
        refresh_universe=False,
    )
    try:
        if not target_symbols:
            return _finish_skipped_community_sentiment_cycle(
                conn,
                run_id,
                symbol_source=symbol_source,
                account_id=account_id,
                reason="no favorite symbols in account watchlist",
                retention_days=retention_days,
            )

        cycle_deadline, resolved_cycle_timeout_seconds = cycle_deadline_from_timeout(cycle_timeout_seconds)

        live_refresh = refresh_live_inputs_for_community_cycle(
            conn,
            target_symbols,
            refresh_market=refresh_market,
            refresh_filings=refresh_filings,
            market_days=market_days,
            cycle_deadline=cycle_deadline,
        )
        if cycle_deadline_exceeded(cycle_deadline):
            sentiment = _empty_sentiment_refresh_result()
            daily = {"counts": {"symbols": 0}, "errors": []}
        else:
            sentiment = refresh_sentiment(
                conn,
                target_symbols,
                days=analysis_days,
                use_llm=use_llm,
                crawl_community=True,
                community_limit=community_limit,
                evidence_limit=evidence_limit,
                account_id=account_id,
                favorites_only=favorites_only,
                analyze_filing_news=False,
                cycle_deadline=cycle_deadline,
            )
            if cycle_deadline_exceeded(cycle_deadline):
                daily = {"counts": {"symbols": 0}, "errors": []}
            else:
                daily = refresh_community_daily_summaries(
                    conn,
                    sentiment.get("symbols") or target_symbols,
                    use_llm=use_llm,
                    llm_stats=(sentiment.get("performance") or {}).get("llm"),
                    cycle_deadline=cycle_deadline,
                )
        timed_out = cycle_deadline_exceeded(cycle_deadline)
        cleanup = cleanup_expired_community_sentiment(conn, retention_days=retention_days)
        result = {
            "mode": "community-sentiment-cycle",
            "method_version": SENTIMENT_METHOD_VERSION,
            "prompt_version": SENTIMENT_PROMPT_VERSION,
            "symbol_source": symbol_source,
            "account_id": sentiment_account_id(account_id),
            "symbols": sentiment.get("symbols") or [],
            "timed_out": timed_out,
            "cycle_timeout_seconds": resolved_cycle_timeout_seconds,
            "live_refresh": live_refresh,
            "sentiment": sentiment,
            "daily": daily,
            "cleanup": cleanup,
            "refreshed_at": now_iso(),
        }
        errors = collect_cycle_errors(result)
        usage = build_agent_usage(result)
        status = "ok" if not errors else "partial"
        finish_ingestion(conn, run_id, status, result["symbols"], usage, errors)
        conn.commit()
        result["run_id"] = run_id
        result["usage"] = usage
        return result
    except Exception as exc:
        finish_ingestion(
            conn,
            run_id,
            "failed",
            target_symbols,
            {"error": str(exc)},
            [{"scope": "community-sentiment-cycle", "error": str(exc)}],
        )
        conn.commit()
        raise


def crawl_community_for_symbols(
    conn: sqlite3.Connection,
    symbols: list[str],
    source: str = "all",
    limit: int = DEFAULT_COMMUNITY_LIMIT,
    timeout: int = 15,
    sleep_seconds: float = 0.8,
) -> dict[str, Any]:
    target_symbols = normalize_symbols(conn, symbols)
    normalized_source = normalize_community_source(source)
    from .history import finish_ingestion, start_ingestion

    run_id = start_ingestion(conn, normalized_source, "community-crawl", target_symbols, False)
    counts = {"symbols": 0, "posts": 0, "fetched_posts": 0}
    errors: list[dict[str, str]] = []
    updated_symbols: list[str] = []
    for symbol in target_symbols:
        try:
            payload = crawl_community_posts(
                symbol,
                source=normalized_source,
                limit=limit,
                timeout=timeout,
                sleep_seconds=sleep_seconds,
            )
            posts = payload.get("posts") or []
            inserted = upsert_community_posts(conn, posts)
            counts["fetched_posts"] += len(posts)
            counts["posts"] += inserted
            counts["symbols"] += 1
            if posts:
                updated_symbols.append(symbol)
            for item in payload.get("errors") or []:
                errors.append({"symbol": symbol, "source": normalized_source, "error": str(item)})
        except Exception as exc:
            errors.append({"symbol": symbol, "source": normalized_source, "error": str(exc)})
    status = "ok" if counts["fetched_posts"] and not errors else ("partial" if counts["fetched_posts"] else "failed")
    finish_ingestion(conn, run_id, status, updated_symbols, counts, errors)
    conn.commit()
    return {
        "mode": "community-crawl",
        "source": normalized_source,
        "run_id": run_id,
        "status": status,
        "symbols": target_symbols,
        "counts": counts,
        "errors": errors,
        "fetched_at": now_iso(),
    }


def refresh_live_inputs_for_community_cycle(
    conn: sqlite3.Connection,
    symbols: list[str],
    refresh_market: bool = True,
    refresh_filings: bool = True,
    market_days: int = 20,
    cycle_deadline: float | None = None,
) -> dict[str, Any]:
    if not symbols:
        return {
            "mode": "community-live-input-refresh",
            "counts": {"market_symbols": 0, "daily_bars": 0, "market_snapshots": 0, "filing_symbols": 0, "filings": 0},
            "errors": [],
            "refreshed_at": now_iso(),
        }

    from .history import refresh_filings_for_symbol_if_needed, refresh_market_data_baostock_first

    counts = {"market_symbols": 0, "daily_bars": 0, "market_snapshots": 0, "filing_symbols": 0, "filings": 0}
    errors: list[dict[str, str]] = []
    market_days = max(3, min(int(market_days or 20), 80))
    processed = 0
    for symbol in symbols:
        if cycle_deadline_exceeded(cycle_deadline):
            errors.append(cycle_timeout_error(cycle_deadline, "live-refresh", pending_symbols=symbols[processed:]))
            break
        processed += 1
        if refresh_market:
            try:
                result = refresh_market_data_baostock_first(conn, symbol, market_days)
                market_counts = result.get("counts") or {}
                daily_bars = int(market_counts.get("daily_bars") or 0)
                market_snapshots = int(market_counts.get("market_snapshots") or 0)
                counts["daily_bars"] += daily_bars
                counts["market_snapshots"] += market_snapshots
                market_refreshed = bool(result.get("symbols")) or bool(daily_bars or market_snapshots)
                counts["market_symbols"] += 1 if market_refreshed else 0
                if not market_refreshed:
                    errors.extend(result.get("errors") or [])
            except Exception as exc:
                errors.append({"symbol": symbol, "scope": "market", "error": str(exc)})
        if refresh_filings:
            try:
                result = refresh_filings_for_symbol_if_needed(conn, symbol, days=30)
                counts["filings"] += int(result.get("filings") or 0)
                counts["filing_symbols"] += 0 if result.get("status") == "skipped" else 1
                errors.extend(result.get("errors") or [])
            except Exception as exc:
                errors.append({"symbol": symbol, "scope": "filings", "error": str(exc)})
    conn.commit()
    return {
        "mode": "community-live-input-refresh",
        "counts": counts,
        "errors": errors,
        "refreshed_at": now_iso(),
    }


def analyze_filing_news_sentiment(
    conn: sqlite3.Connection,
    symbol: str,
    days: int = 30,
    use_llm: bool = True,
    limit: int = DEFAULT_SENTIMENT_EVIDENCE_LIMIT,
    stats: dict[str, Any] | None = None,
) -> int:
    rows = filing_news_candidates(conn, symbol, days=days, limit=limit)
    cached = cached_llm_sentiment_evidence(conn, rows) if use_llm else {}
    record_llm_inventory(stats, "filing_news", total=len(rows), cache_hits=len(cached))
    uncached_items = [item for item in rows if sentiment_item_key(item) not in cached]
    fresh_results = analyze_text_items(uncached_items, use_llm=use_llm, stats=stats)
    results_by_key = {sentiment_item_key(item): item for item in cached.values()}
    results_by_key.update({sentiment_item_key(item): item for item in fresh_results})
    results = [results_by_key[sentiment_item_key(item)] for item in rows if sentiment_item_key(item) in results_by_key]
    analyzed = 0
    for result in results:
        upsert_sentiment_evidence(conn, result)
        analyzed += 1
    return analyzed


def analyze_community_sentiment(
    conn: sqlite3.Connection,
    symbol: str,
    days: int = 30,
    use_llm: bool = True,
    limit: int = DEFAULT_SENTIMENT_EVIDENCE_LIMIT,
    stats: dict[str, Any] | None = None,
) -> int:
    analysis_day = community_analysis_day()
    rows = conn.execute(
        """
        select id, symbol, source, title, content, url, published_at, fetched_at, metrics_json
        from community_posts
        where symbol = ?
          and coalesce(nullif(substr(published_at, 1, 10), ''), substr(fetched_at, 1, 10)) = ?
        order by coalesce(nullif(published_at, ''), fetched_at) desc, id desc
        limit ?
        """,
        (symbol, analysis_day, clean_limit(limit, 200)),
    ).fetchall()
    stock_context = community_stock_context(conn, symbol)
    items: list[dict[str, Any]] = []
    for row in rows:
        text = community_post_text(row["title"], row["content"])
        items.append(
            {
                "symbol": symbol,
                "sentiment_type": "community",
                "source_table": "community_posts",
                "source_id": str(row["id"]),
                "source": row["source"],
                "event_date": row["published_at"] or row["fetched_at"],
                "title": row["title"],
                "url": row["url"],
                "category": "community_discussion",
                "text": text,
                "source_tier": "C",
                "extra": {
                    "metrics": parse_json(row["metrics_json"], {}),
                    "stock_context": stock_context,
                },
            }
        )
    analyzed = 0
    cached = cached_llm_sentiment_evidence(conn, items, max_age_minutes=None) if use_llm else {}
    record_llm_inventory(stats, "community", total=len(items), cache_hits=len(cached))
    uncached_items = [item for item in items if sentiment_item_key(item) not in cached]
    fresh_results = analyze_text_items(uncached_items, use_llm=use_llm, community=True, stats=stats)
    results_by_key = {sentiment_item_key(item): item for item in cached.values()}
    results_by_key.update({sentiment_item_key(item): item for item in fresh_results})
    results = [results_by_key[sentiment_item_key(item)] for item in items if sentiment_item_key(item) in results_by_key]
    for result in results:
        upsert_sentiment_evidence(conn, result)
        analyzed += 1
    return analyzed


def community_post_text(title: Any, content: Any) -> str:
    title_text = re.sub(r"\s+", " ", str(title or "")).strip()
    content_text = re.sub(r"\s+", " ", str(content or "")).strip()
    if content_text:
        return content_text
    return title_text


def community_stock_context(conn: sqlite3.Connection, symbol: str) -> dict[str, Any]:
    normalized = str(symbol or "").upper()
    row = conn.execute(
        "select symbol, name, market, currency from symbols where symbol = ?",
        (normalized,),
    ).fetchone()
    symbol_row = row_to_dict(row) if row else {}
    context: dict[str, Any] = {
        "symbol": normalized,
        "name": str(symbol_row.get("name") or normalized),
    }
    if symbol_row:
        context["market"] = str(symbol_row.get("market") or "")
        context["currency"] = str(symbol_row.get("currency") or "")

    bar_quote = latest_community_daily_quote(conn, normalized)
    snapshot = conn.execute(
        """
        select provider, price, as_of
        from market_snapshots
        where symbol = ?
        order by fetched_at desc, id desc
        limit 1
        """,
        (normalized,),
    ).fetchone()
    snapshot_row = row_to_dict(snapshot) if snapshot else {}
    if snapshot_row.get("price") is not None:
        context["current_price"] = round(float(snapshot_row["price"]), 4)
        context["price_as_of"] = str(snapshot_row.get("as_of") or "")
        context["price_source"] = str(snapshot_row.get("provider") or "")
    elif bar_quote.get("current_price") is not None:
        context["current_price"] = bar_quote["current_price"]
        context["price_as_of"] = bar_quote.get("price_as_of") or ""
        context["price_source"] = bar_quote.get("price_source") or ""

    if bar_quote.get("change_pct") is not None:
        context["change_pct"] = bar_quote["change_pct"]

    xueqiu_quote = fetch_xueqiu_quote(normalized)
    if xueqiu_quote:
        if xueqiu_quote.get("name"):
            context["name"] = xueqiu_quote["name"]
        if xueqiu_quote.get("current_price") is not None:
            context["current_price"] = xueqiu_quote["current_price"]
        if xueqiu_quote.get("change_pct") is not None:
            context["change_pct"] = xueqiu_quote["change_pct"]
        context["price_source"] = xueqiu_quote.get("price_source") or "xueqiu"
        if xueqiu_quote.get("price_as_of"):
            context["price_as_of"] = xueqiu_quote["price_as_of"]
        if xueqiu_quote.get("market_status"):
            context["market_status"] = xueqiu_quote["market_status"]
        if xueqiu_quote.get("currency"):
            context["currency"] = xueqiu_quote["currency"]
    return context


def latest_community_daily_quote(conn: sqlite3.Connection, symbol: str) -> dict[str, Any]:
    bar_rows = [
        row_to_dict(item)
        for item in conn.execute(
            """
            select close, change_pct, trade_date, provider, adjust
            from daily_bars
            where symbol = ?
            order by trade_date desc, provider desc, adjust desc
            limit 20
            """,
            (symbol,),
        ).fetchall()
    ]
    if not bar_rows:
        return {}

    latest_date = bar_rows[0]["trade_date"]
    same_day = [item for item in bar_rows if item["trade_date"] == latest_date]
    bar = max(same_day, key=lambda item: (str(item.get("provider") or ""), str(item.get("adjust") or "")))
    quote: dict[str, Any] = {}
    if bar.get("close") is not None:
        quote["current_price"] = round(float(bar["close"]), 4)
        quote["price_as_of"] = str(bar.get("trade_date") or "")
        quote["price_source"] = str(bar.get("provider") or "")
    if bar.get("change_pct") is not None:
        quote["change_pct"] = round(float(bar["change_pct"]), 4)
    return quote


def community_llm_stock_context(item: dict[str, Any]) -> dict[str, Any]:
    context = dict((item.get("extra") or {}).get("stock_context") or {})
    if not context:
        symbol = str(item.get("symbol") or "").upper()
        if symbol:
            context = {"symbol": symbol, "name": symbol}
        else:
            return {}
    payload: dict[str, Any] = {}
    name = str(context.get("name") or context.get("symbol") or "").strip()
    if name:
        payload["stock_name"] = name
    symbol = str(context.get("symbol") or item.get("symbol") or "").strip()
    if symbol:
        payload["symbol"] = symbol.upper()
    if context.get("current_price") is not None:
        payload["current_price"] = context["current_price"]
    if context.get("currency"):
        payload["currency"] = context["currency"]
    if context.get("change_pct") is not None:
        payload["change_pct"] = context["change_pct"]
    if context.get("price_as_of"):
        payload["price_as_of"] = context["price_as_of"]
    return payload


def analyze_market_sentiment(conn: sqlite3.Connection, symbol: str, days: int = 30) -> int:
    symbol_row = conn.execute("select * from symbols where symbol = ?", (symbol,)).fetchone()
    if not symbol_row:
        return 0
    bars = preferred_daily_bars(conn, symbol, row_to_dict(symbol_row), limit=max(60, clean_days(days) + 30))
    if len(bars) < 2:
        return 0
    result = market_sentiment_result(symbol, bars, days=days)
    upsert_sentiment_evidence(conn, result)
    return 1


def filing_news_candidates(conn: sqlite3.Connection, symbol: str, days: int = 30, limit: int = 80) -> list[dict[str, Any]]:
    cutoff = cutoff_date(days)
    clean = clean_limit(limit, 200)
    candidates: list[dict[str, Any]] = []
    for row in conn.execute(
        """
        select id, symbol, source, source_tier, title, url, published_at, category
        from filings_history
        where symbol = ?
          and lower(source) not like '%mock%'
          and substr(published_at, 1, 10) >= ?
        order by published_at desc, id desc
        limit ?
        """,
        (symbol, cutoff, clean),
    ).fetchall():
        candidates.append(
            {
                "symbol": symbol,
                "sentiment_type": "filing_news",
                "source_table": "filings_history",
                "source_id": str(row["id"]),
                "source": row["source"],
                "source_tier": row["source_tier"],
                "event_date": row["published_at"],
                "title": row["title"],
                "url": row["url"],
                "category": row["category"] or "filing",
                "text": f"{row['title']} {row['category'] or ''}",
                "extra": {},
            }
        )
    for row in conn.execute(
        """
        select id, symbol, provider, report_type, title, summary, published_at
        from company_reports_history
        where symbol = ?
          and lower(provider) not like '%mock%'
          and coalesce(nullif(substr(published_at, 1, 10), ''), substr(fetched_at, 1, 10)) >= ?
        order by coalesce(nullif(published_at, ''), fetched_at) desc, id desc
        limit ?
        """,
        (symbol, cutoff, clean),
    ).fetchall():
        candidates.append(
            {
                "symbol": symbol,
                "sentiment_type": "filing_news",
                "source_table": "company_reports_history",
                "source_id": str(row["id"]),
                "source": row["provider"],
                "source_tier": "S",
                "event_date": row["published_at"],
                "title": row["title"] or row["report_type"],
                "url": "",
                "category": f"company_report:{row['report_type']}",
                "text": " ".join(part for part in [row["title"], row["summary"], row["report_type"]] if part),
                "extra": {},
            }
        )
    for row in conn.execute(
        """
        select id, symbol, source, source_tier, title, url, published_at, summary, sentiment_score
        from news_items
        where symbol = ?
          and lower(source) not like '%mock%'
          and substr(published_at, 1, 10) >= ?
        order by published_at desc, id desc
        limit ?
        """,
        (symbol, cutoff, clean),
    ).fetchall():
        candidates.append(
            {
                "symbol": symbol,
                "sentiment_type": "filing_news",
                "source_table": "news_items",
                "source_id": str(row["id"]),
                "source": row["source"],
                "source_tier": row["source_tier"],
                "event_date": row["published_at"],
                "title": row["title"],
                "url": row["url"],
                "category": "news",
                "text": " ".join(part for part in [row["title"], row["summary"]] if part),
                "extra": {"provider_sentiment_score": row["sentiment_score"]},
            }
        )
    candidates.extend(financial_metric_candidates(conn, symbol, limit=8))
    candidates.sort(key=lambda item: str(item.get("event_date") or ""), reverse=True)
    return candidates[:clean]


def financial_metric_candidates(conn: sqlite3.Connection, symbol: str, limit: int = 8) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select *
        from financial_metrics_history
        where symbol = ?
          and lower(provider) not like '%mock%'
        order by report_period desc, fetched_at desc
        limit ?
        """,
        (symbol, limit),
    ).fetchall()
    candidates: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_dict(row)
        raw = parse_json(item.get("raw_json"), {})
        if raw.get("status") == "no_data":
            continue
        score, details = score_financial_metrics(item)
        title = f"{item['report_period']} 基本面快照"
        candidates.append(
            {
                "symbol": symbol,
                "sentiment_type": "filing_news",
                "source_table": "financial_metrics_history",
                "source_id": f"{item['symbol']}:{item['report_period']}:{item['provider']}",
                "source": item["provider"],
                "source_tier": "S",
                "event_date": normalize_financial_event_date(
                    item.get("announce_date") or item.get("report_period") or item.get("fetched_at")
                ),
                "title": title,
                "url": "",
                "category": "fundamental",
                "text": financial_metric_text(item),
                "extra": {"rule_score": score, "financial_details": details},
            }
        )
    return candidates


def cached_llm_sentiment_evidence(
    conn: sqlite3.Connection,
    items: list[dict[str, Any]],
    max_age_minutes: int | None = LLM_CACHE_TTL_MINUTES,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    llm = preferred_llm_config()
    if not llm["configured"] or not items:
        return {}
    keys = [sentiment_item_key(item) for item in items]
    key_set = set(keys)
    text_lengths = {sentiment_item_key(item): len(str(item.get("text") or item.get("title") or "")) for item in items}
    source_ids = sorted({source_id for _, _, source_id in keys if source_id})
    if not source_ids:
        return {}
    placeholders = ",".join("?" for _ in source_ids)
    age_filter = ""
    params: list[Any] = [*source_ids, SENTIMENT_METHOD_VERSION, llm["provider"], llm["model"]]
    if max_age_minutes is not None:
        cutoff = (datetime.now() - timedelta(minutes=max_age_minutes)).isoformat(timespec="seconds")
        age_filter = "and analyzed_at >= ?"
        params.append(cutoff)
    rows = conn.execute(
        f"""
        select *
        from sentiment_evidence
        where source_id in ({placeholders})
          and method_version = ?
          and model_provider = ?
          and model_name = ?
          {age_filter}
        """,
        tuple(params),
    ).fetchall()
    cached: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        item = row_to_dict(row)
        item["keywords"] = parse_json(item.pop("keywords_json"), [])
        item["evidence"] = parse_json(item.pop("evidence_json"), {})
        key = (str(item.get("sentiment_type") or ""), str(item.get("source_table") or ""), str(item.get("source_id") or ""))
        expected_length = text_lengths.get(key, 0)
        evidence_length = item.get("evidence", {}).get("text_length")
        try:
            parsed_evidence_length = int(evidence_length or 0)
        except (TypeError, ValueError):
            parsed_evidence_length = 0
        if expected_length and parsed_evidence_length != expected_length:
            continue
        if key in key_set:
            cached[key] = item
    return cached


def sentiment_item_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("sentiment_type") or ""),
        str(item.get("source_table") or ""),
        str(item.get("source_id") or ""),
    )


def analyze_text_items(
    items: list[dict[str, Any]],
    use_llm: bool = False,
    community: bool = False,
    stats: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    results = [fallback_text_sentiment(item, community=community) for item in items]
    llm = preferred_llm_config()
    if not use_llm or not llm["configured"] or not results:
        record_llm_fallbacks(stats, len(results))
        return results

    batch_size = llm_batch_size(community=community)
    batches = [(offset, items[offset : offset + batch_size]) for offset in range(0, len(items), batch_size)]
    if llm_concurrency() <= 1 or len(batches) <= 1:
        batch_results = [request_llm_text_batch(offset, chunk_items, community=community) for offset, chunk_items in batches]
    else:
        batch_results = []
        max_workers = min(llm_concurrency(), len(batches))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(request_llm_text_batch, offset, chunk_items, community): (offset, chunk_items)
                for offset, chunk_items in batches
            }
            for future in as_completed(futures):
                batch_results.append(future.result())

    for batch in batch_results:
        offset = int(batch["offset"])
        chunk_items = items[offset : offset + batch_size]
        apply_llm_batch_result(results, items, batch, offset, chunk_items, llm, stats)
    return results


def analyze_text_item(item: dict[str, Any], use_llm: bool = False, community: bool = False) -> dict[str, Any]:
    return analyze_text_items([item], use_llm=use_llm, community=community)[0]


def request_llm_text_batch(offset: int, chunk_items: list[dict[str, Any]], community: bool = False) -> dict[str, Any]:
    started = time.monotonic()
    try:
        rows = llm_analyze_text_batch(chunk_items, community=community)
        return {"offset": offset, "rows": rows, "duration_ms": elapsed_ms(started), "error": ""}
    except Exception as exc:
        return {"offset": offset, "rows": [], "duration_ms": elapsed_ms(started), "error": str(exc)}


def apply_llm_batch_result(
    results: list[dict[str, Any]],
    all_items: list[dict[str, Any]],
    batch: dict[str, Any],
    offset: int,
    chunk_items: list[dict[str, Any]],
    llm: dict[str, Any],
    stats: dict[str, Any] | None = None,
) -> None:
    error = str(batch.get("error") or "")
    record_llm_request(
        stats,
        item_count=len(chunk_items),
        duration_ms=int(batch.get("duration_ms") or 0),
        error=error,
    )
    if error:
        retry_batches = retry_llm_batch_after_error(offset, chunk_items, error)
        if retry_batches:
            for retry_batch in retry_batches:
                retry_offset = int(retry_batch["offset"])
                retry_items = list(
                    retry_batch.get("input_items")
                    or all_items[retry_offset : retry_offset + llm_retry_batch_size(community=True)]
                )
                apply_llm_batch_result(results, all_items, retry_batch, retry_offset, retry_items, llm, stats)
            return
        mark_llm_fallback_error(results, offset, len(chunk_items), error, stats)
        return

    merge_llm_rows(results, offset, chunk_items, batch.get("rows") or [], llm, stats=stats)


def retry_llm_batch_after_error(offset: int, chunk_items: list[dict[str, Any]], error: str) -> list[dict[str, Any]]:
    if not should_retry_llm_batch(chunk_items, error):
        return []
    retry_size = llm_retry_batch_size(community=True)
    retry_chunks = [
        (offset + relative_offset, chunk_items[relative_offset : relative_offset + retry_size])
        for relative_offset in range(0, len(chunk_items), retry_size)
    ]
    if llm_concurrency() <= 1 or len(retry_chunks) <= 1:
        retry_batches = [
            request_llm_text_batch(retry_offset, retry_items, community=True)
            for retry_offset, retry_items in retry_chunks
        ]
    else:
        retry_batches = []
        with ThreadPoolExecutor(max_workers=min(llm_concurrency(), len(retry_chunks))) as executor:
            futures = {
                executor.submit(request_llm_text_batch, retry_offset, retry_items, True): (retry_offset, retry_items)
                for retry_offset, retry_items in retry_chunks
            }
            for future in as_completed(futures):
                retry_batches.append(future.result())
    retry_items_by_offset = {retry_offset: retry_items for retry_offset, retry_items in retry_chunks}
    for retry in retry_batches:
        retry["input_items"] = retry_items_by_offset.get(int(retry.get("offset") or 0), [])
        retry["retry_after_error"] = error[:180]
    return retry_batches


def should_retry_llm_batch(chunk_items: list[dict[str, Any]], error: str) -> bool:
    if len(chunk_items) <= llm_retry_batch_size(community=True):
        return False
    if not all(str(item.get("sentiment_type") or "") == "community" for item in chunk_items):
        return False
    text = error.lower()
    return any(pattern in text for pattern in ("timed out", "timeout", "read operation", "connection reset", "temporarily"))


def mark_llm_fallback_error(
    results: list[dict[str, Any]],
    offset: int,
    count: int,
    error: str,
    stats: dict[str, Any] | None = None,
) -> None:
    for result in results[offset : offset + count]:
        result["evidence"] = {
            **dict(result.get("evidence") or {}),
            "llm_error": error[:300],
        }
    record_llm_fallbacks(stats, count)


def merge_llm_rows(
    results: list[dict[str, Any]],
    offset: int,
    chunk_items: list[dict[str, Any]],
    llm_rows: list[dict[str, Any]],
    llm: dict[str, Any],
    stats: dict[str, Any] | None = None,
) -> None:
    item_indexes_by_id = {
        llm_item_id(item): offset + index
        for index, item in enumerate(chunk_items)
    }
    merged_indexes: set[int] = set()
    for llm_row in llm_rows:
        row_id = str(llm_row.get("id") or "").strip()
        absolute_index = item_indexes_by_id.get(row_id, -1) if row_id else -1
        if absolute_index < 0:
            try:
                index = int(llm_row.get("index"))
            except (TypeError, ValueError):
                continue
            absolute_index = offset + index
        if 0 <= absolute_index < len(results):
            merge_llm_sentiment_result(results[absolute_index], llm_row, llm)
            merged_indexes.add(absolute_index)
    missing = []
    for index in range(offset, offset + len(chunk_items)):
        if index not in merged_indexes:
            missing.append(index)
    for index in missing:
        mark_llm_fallback_error(results, index, 1, "llm_missing_result", stats)


def llm_item_id(item: dict[str, Any]) -> str:
    sentiment_type, source_table, source_id = sentiment_item_key(item)
    return f"{sentiment_type}:{source_table}:{source_id}"


COMMUNITY_SENTIMENT_CLASS_FALLBACK_SCORES: dict[str, float] = {
    "正面": 80.0,
    "偏正面": 40.0,
    "中性": 0.0,
    "偏负面": -40.0,
    "负面": -80.0,
    "积极": 80.0,
    "偏积极": 40.0,
    "消极": -80.0,
    "偏消极": -40.0,
    "positive": 80.0,
    "mild_positive": 40.0,
    "neutral": 0.0,
    "mild_negative": -40.0,
    "negative": -80.0,
}


def normalize_community_score(value: Any) -> float:
    score = clamp_float(value, COMMUNITY_SCORE_MIN, COMMUNITY_SCORE_MAX)
    if abs(score) <= 2.000001:
        return clamp_float(
            score * COMMUNITY_SCORE_LEGACY_MULTIPLIER,
            COMMUNITY_SCORE_MIN,
            COMMUNITY_SCORE_MAX,
        )
    return score


def resolve_community_llm_score(llm_result: dict[str, Any]) -> float:
    raw_score = llm_result.get("sentiment_score")
    if raw_score not in (None, ""):
        return normalize_community_score(raw_score)
    _, fallback_score = community_sentiment_class_score(
        llm_result.get("sentiment_class")
        or llm_result.get("sentiment_label")
        or llm_result.get("class")
        or llm_result.get("category")
    )
    return fallback_score


def normalize_community_sentiment_class(value: Any, score: float | None = None) -> str:
    text = str(value or "").strip()
    if text in COMMUNITY_SENTIMENT_CLASSES:
        return text
    normalized, _ = community_sentiment_class_score(text)
    if normalized in COMMUNITY_SENTIMENT_CLASSES:
        return normalized
    if score is not None:
        return community_class_from_score(score)
    return "中性"


def resolve_community_llm_class(llm_result: dict[str, Any], score: float) -> str:
    return normalize_community_sentiment_class(
        llm_result.get("sentiment_class")
        or llm_result.get("class")
        or llm_result.get("category"),
        score=score,
    )


def community_sentiment_class_score(value: Any) -> tuple[str, float]:
    text = str(value or "").strip().lower().replace(" ", "_")
    if text in COMMUNITY_SENTIMENT_CLASS_FALLBACK_SCORES:
        score = COMMUNITY_SENTIMENT_CLASS_FALLBACK_SCORES[text]
        return community_class_from_score(score), score
    if "偏正" in text or "偏积极" in text or "mild_positive" in text:
        return "偏正面", 40.0
    if "偏负" in text or "偏消极" in text or "mild_negative" in text:
        return "偏负面", -40.0
    if "正面" in text or "积极" in text or text == "positive":
        return "正面", 80.0
    if "负面" in text or "消极" in text or text == "negative":
        return "负面", -80.0
    return "中性", 0.0


def community_class_from_score(score: float) -> str:
    value = normalize_community_score(score)
    if value >= 75:
        return "正面"
    if value >= 25:
        return "偏正面"
    if value <= -75:
        return "负面"
    if value <= -25:
        return "偏负面"
    return "中性"


def community_sentiment_label(score: Any) -> str:
    value = normalize_community_score(score)
    if value >= 75:
        return "positive"
    if value >= 25:
        return "mild_positive"
    if value <= -75:
        return "negative"
    if value <= -25:
        return "mild_negative"
    return "neutral"


def fallback_text_sentiment(item: dict[str, Any], community: bool = False) -> dict[str, Any]:
    text = str(item.get("text") or item.get("title") or "")
    extra = dict(item.get("extra") or {})
    score = 0.0
    confidence = 0.28 if text else 0.12
    category = str(item.get("category") or ("community_discussion" if community else "neutral"))
    impact_horizon = "1w" if community else "1m"
    evidence: dict[str, Any] = {
        "text_length": len(text),
        "fallback_reason": "llm_unavailable_or_failed",
        "prompt_version": SENTIMENT_PROMPT_VERSION,
    }
    if item.get("category") == "fundamental" and "rule_score" in extra:
        score = clamp_score(extra["rule_score"])
        category = "fundamental"
        impact_horizon = "1q"
        confidence = 0.58
        evidence["structured_financial_score"] = score
        evidence["financial_details"] = extra.get("financial_details") or {}
    elif community and extra.get("stock_context"):
        evidence["stock_context"] = dict(extra["stock_context"])

    result = {
        **item,
        "sentiment_score": score,
        "sentiment_label": sentiment_label(score),
        "confidence": clamp_float(confidence, 0.0, 1.0),
        "impact_horizon": impact_horizon,
        "category": category,
        "keywords": [],
        "evidence": evidence,
        "model_provider": "local",
        "model_name": LOCAL_MODEL_NAME,
        "method_version": SENTIMENT_METHOD_VERSION,
        "analyzed_at": now_iso(),
    }
    return result


def merge_llm_sentiment_result(result: dict[str, Any], llm_result: dict[str, Any], llm: dict[str, Any]) -> None:
    evidence = dict(result.get("evidence") or {})
    evidence.pop("fallback_reason", None)
    evidence.pop("llm_error", None)
    evidence["prompt_version"] = SENTIMENT_PROMPT_VERSION
    if llm_result.get("id"):
        evidence["llm_id"] = str(llm_result.get("id") or "")
    reason = str(llm_result.get("reason") or llm_result.get("rationale") or "")[:500]
    if reason:
        evidence["llm_reason"] = reason
    if str(result.get("sentiment_type") or "") == "community":
        stock_context = dict((result.get("extra") or {}).get("stock_context") or {})
        if stock_context:
            evidence["stock_context"] = stock_context
        score = resolve_community_llm_score(llm_result)
        sentiment_class = resolve_community_llm_class(llm_result, score)
        evidence["sentiment_class"] = sentiment_class
        result.update(
            {
                "sentiment_score": score,
                "sentiment_label": community_sentiment_label(score),
                "confidence": clamp_float(llm_result.get("confidence", result["confidence"]), 0.0, 1.0),
                "category": sentiment_class,
                "impact_horizon": str(llm_result.get("impact_horizon") or result.get("impact_horizon") or "1w"),
                "keywords": safe_string_list(llm_result.get("keywords") or result.get("keywords") or []),
                "evidence": evidence,
                "model_provider": llm["provider"],
                "model_name": llm["model"],
            }
        )
        return
    result.update(
        {
            "sentiment_score": clamp_score(llm_result.get("sentiment_score", result["sentiment_score"])),
            "sentiment_label": sentiment_label(llm_result.get("sentiment_score", result["sentiment_score"])),
            "confidence": clamp_float(llm_result.get("confidence", result["confidence"]), 0.0, 1.0),
            "category": str(llm_result.get("category") or result.get("category") or ""),
            "impact_horizon": str(llm_result.get("impact_horizon") or result.get("impact_horizon") or ""),
            "keywords": safe_string_list(llm_result.get("keywords") or result.get("keywords") or []),
            "evidence": evidence,
            "model_provider": llm["provider"],
            "model_name": llm["model"],
        }
    )


def market_sentiment_result(symbol: str, bars: list[dict[str, Any]], days: int = 30) -> dict[str, Any]:
    latest = bars[-1]
    window = bars[-clean_days(days) :]
    close_latest = number(latest.get("close"))
    close_5 = number(bars[-6].get("close")) if len(bars) >= 6 else number(bars[0].get("close"))
    close_20 = number(bars[-21].get("close")) if len(bars) >= 21 else number(bars[0].get("close"))
    change_1d = number(latest.get("change_pct"), 0.0) or 0.0
    change_5d = pct_change(close_latest, close_5)
    change_20d = pct_change(close_latest, close_20)
    amount_ratio = latest_ratio(bars, "amount", lookback=20)
    volume_ratio = latest_ratio(bars, "volume", lookback=20)
    latest_turnover = number(latest.get("turnover_rate"), 0.0) or 0.0
    limit_up_days = sum(1 for bar in window if (number(bar.get("change_pct"), 0.0) or 0.0) >= 9.4)
    limit_down_days = sum(1 for bar in window if (number(bar.get("change_pct"), 0.0) or 0.0) <= -9.4)
    drawdown = max_drawdown(window)

    score = change_1d * 2.2 + change_5d * 1.4 + change_20d * 0.45
    if amount_ratio >= 2.0 and change_1d >= 2.0:
        score += 12
    if amount_ratio >= 2.0 and change_1d <= -2.0:
        score -= 14
    score += min(limit_up_days * 8, 24)
    score -= min(limit_down_days * 10, 30)
    if drawdown <= -18:
        score -= 12
    if latest_turnover >= 12 and change_1d < 0:
        score -= 8
    score = clamp_score(score)
    confidence = clamp_float(0.45 + min(len(window), 30) / 80 + min(abs(score), 60) / 220, 0.35, 0.9)
    details = {
        "latest_trade_date": latest.get("date"),
        "change_1d": change_1d,
        "change_5d": change_5d,
        "change_20d": change_20d,
        "amount_ratio_20d": amount_ratio,
        "volume_ratio_20d": volume_ratio,
        "turnover_rate": latest_turnover,
        "limit_up_days": limit_up_days,
        "limit_down_days": limit_down_days,
        "max_drawdown": drawdown,
        "bar_count": len(window),
    }
    return {
        "symbol": symbol,
        "sentiment_type": "market",
        "source_table": "daily_bars",
        "source_id": f"{symbol}:{latest.get('date') or latest.get('trade_date')}",
        "source": str(latest.get("provider") or "daily_bars"),
        "event_date": str(latest.get("date") or ""),
        "title": "交易型情绪",
        "url": "",
        "category": "market_behavior",
        "sentiment_score": score,
        "sentiment_label": sentiment_label(score),
        "confidence": confidence,
        "impact_horizon": "1w",
        "keywords": market_keywords(details),
        "evidence": details,
        "model_provider": "local",
        "model_name": LOCAL_MODEL_NAME,
        "method_version": SENTIMENT_METHOD_VERSION,
        "analyzed_at": now_iso(),
    }


def upsert_sentiment_evidence(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    conn.execute(
        """
        insert into sentiment_evidence (
          symbol, sentiment_type, source_table, source_id, source, event_date, title, url,
          category, sentiment_score, sentiment_label, confidence, impact_horizon,
          keywords_json, evidence_json, model_provider, model_name, method_version, analyzed_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(sentiment_type, source_table, source_id, method_version) do update set
          source = excluded.source,
          event_date = excluded.event_date,
          title = excluded.title,
          url = excluded.url,
          category = excluded.category,
          sentiment_score = excluded.sentiment_score,
          sentiment_label = excluded.sentiment_label,
          confidence = excluded.confidence,
          impact_horizon = excluded.impact_horizon,
          keywords_json = excluded.keywords_json,
          evidence_json = excluded.evidence_json,
          model_provider = excluded.model_provider,
          model_name = excluded.model_name,
          analyzed_at = excluded.analyzed_at
        """,
        (
            str(item.get("symbol") or "").upper(),
            str(item.get("sentiment_type") or ""),
            str(item.get("source_table") or ""),
            str(item.get("source_id") or ""),
            str(item.get("source") or ""),
            str(item.get("event_date") or "")[:32],
            str(item.get("title") or "")[:500],
            str(item.get("url") or "")[:1000],
            str(item.get("category") or "")[:120],
            float(item.get("sentiment_score") or 0),
            evidence_sentiment_label(item),
            clamp_float(item.get("confidence"), 0.0, 1.0),
            str(item.get("impact_horizon") or "")[:40],
            json.dumps(safe_string_list(item.get("keywords") or []), ensure_ascii=False),
            json.dumps(item.get("evidence") or {}, ensure_ascii=False, default=str),
            str(item.get("model_provider") or "local"),
            str(item.get("model_name") or LOCAL_MODEL_NAME),
            str(item.get("method_version") or SENTIMENT_METHOD_VERSION),
            str(item.get("analyzed_at") or now_iso()),
        ),
    )


def upsert_sentiment_snapshot(conn: sqlite3.Connection, symbol: str, days: int = 30) -> dict[str, Any]:
    window_days = clean_days(days)
    cutoff = cutoff_date(window_days)
    rows = conn.execute(
        """
        select *
        from sentiment_evidence
        where symbol = ?
          and method_version = ?
          and lower(source) not like '%mock%'
          and coalesce(nullif(substr(event_date, 1, 10), ''), substr(analyzed_at, 1, 10)) >= ?
        order by coalesce(nullif(event_date, ''), analyzed_at) desc, id desc
        """,
        (symbol, SENTIMENT_METHOD_VERSION, cutoff),
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {"filing_news": [], "community": [], "market": []}
    failed_counts: dict[str, int] = {"filing_news": 0, "community": 0, "market": 0}
    valid_rows: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_dict(row)
        if failed_text_llm_evidence(item):
            failed_counts[item["sentiment_type"]] = failed_counts.get(item["sentiment_type"], 0) + 1
            continue
        if item["sentiment_type"] == "community" and sentiment_evidence_day(item) != community_analysis_day():
            continue
        valid_rows.append(item)
        grouped.setdefault(item["sentiment_type"], []).append(item)

    type_scores = {key: sentiment_group_score(key, items, window_days) for key, items in grouped.items() if items}
    available_weights = {
        "filing_news": 0.40 if "filing_news" in type_scores else 0.0,
        "community": 0.25 if "community" in type_scores else 0.0,
        "market": 0.35 if "market" in type_scores else 0.0,
    }
    weight_sum = sum(available_weights.values()) or 1.0
    composite = sum(type_scores[key]["score"] * available_weights.get(key, 0.0) for key in type_scores) / weight_sum
    confidence = sum(type_scores[key]["confidence"] * available_weights.get(key, 0.0) for key in type_scores) / weight_sum
    source_counts = {key: len(value) for key, value in grouped.items()}
    generated_at = now_iso()
    as_of = latest_as_of(valid_rows) or latest_as_of(rows) or generated_at[:10]
    raw = {
        "type_scores": type_scores,
        "source_counts": source_counts,
        "failed_counts": {key: value for key, value in failed_counts.items() if value},
        "method": "weighted recency-adjusted evidence average",
    }
    conn.execute(
        """
        insert into sentiment_snapshots (
          symbol, as_of, window_days, filing_news_score, community_score, market_score,
          composite_score, sentiment_label, confidence, source_counts_json,
          raw_json, method_version, generated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(symbol, as_of, window_days, method_version) do update set
          filing_news_score = excluded.filing_news_score,
          community_score = excluded.community_score,
          market_score = excluded.market_score,
          composite_score = excluded.composite_score,
          sentiment_label = excluded.sentiment_label,
          confidence = excluded.confidence,
          source_counts_json = excluded.source_counts_json,
          raw_json = excluded.raw_json,
          generated_at = excluded.generated_at
        """,
        (
            symbol,
            as_of,
            window_days,
            type_scores.get("filing_news", {}).get("score"),
            type_scores.get("community", {}).get("score"),
            type_scores.get("market", {}).get("score"),
            composite,
            sentiment_label(composite),
            clamp_float(confidence, 0.0, 1.0),
            json.dumps(source_counts, ensure_ascii=False),
            json.dumps(raw, ensure_ascii=False, default=str),
            SENTIMENT_METHOD_VERSION,
            generated_at,
        ),
    )
    return {
        "symbol": symbol,
        "as_of": as_of,
        "window_days": window_days,
        "filing_news_score": type_scores.get("filing_news", {}).get("score"),
        "community_score": type_scores.get("community", {}).get("score"),
        "market_score": type_scores.get("market", {}).get("score"),
        "composite_score": composite,
        "sentiment_label": sentiment_label(composite),
        "confidence": clamp_float(confidence, 0.0, 1.0),
        "source_counts": source_counts,
        "generated_at": generated_at,
    }


def upsert_community_daily_summary(
    conn: sqlite3.Connection,
    symbol: str,
    trade_date: str,
    use_llm: bool = True,
    source: str = "xueqiu",
    llm_stats: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    normalized_day = normalize_day(trade_date)
    if not normalized_day:
        return None
    rows = community_daily_evidence_rows(conn, symbol, normalized_day, source=source)
    if not rows:
        return None

    label_counts = Counter(str(row.get("sentiment_label") or "neutral") for row in rows)
    positive_count = label_counts.get("positive", 0) + label_counts.get("mild_positive", 0)
    negative_count = label_counts.get("negative", 0) + label_counts.get("mild_negative", 0)
    neutral_count = max(0, len(rows) - positive_count - negative_count)
    score_stats = community_daily_score(rows)
    keyword_counts = community_keyword_counts(rows)
    conclusion_payload = community_daily_conclusion(
        symbol,
        normalized_day,
        {
            "analyzed_count": len(rows),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "sentiment_score": score_stats["score"],
            "sentiment_label": sentiment_label(score_stats["score"]),
            "confidence": score_stats["confidence"],
            "label_counts": dict(label_counts),
            "top_keywords": keyword_counts[:12],
        },
        use_llm=use_llm,
        llm_stats=llm_stats,
    )
    generated_at = now_iso()
    raw = {
        "method": "distinct community sentiment_evidence rows grouped by analyzed_at date",
        "source": source,
        "score_method": "confidence weighted average",
        "detail_retention_days": COMMUNITY_DETAIL_RETENTION_DAYS,
    }
    conn.execute(
        """
        insert into community_sentiment_daily (
          symbol, source, trade_date, analyzed_count, positive_count, negative_count, neutral_count,
          sentiment_score, sentiment_label, confidence, conclusion, label_counts_json,
          keyword_counts_json, model_provider, model_name, method_version, generated_at, raw_json
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(symbol, source, trade_date, method_version) do update set
          analyzed_count = excluded.analyzed_count,
          positive_count = excluded.positive_count,
          negative_count = excluded.negative_count,
          neutral_count = excluded.neutral_count,
          sentiment_score = excluded.sentiment_score,
          sentiment_label = excluded.sentiment_label,
          confidence = excluded.confidence,
          conclusion = excluded.conclusion,
          label_counts_json = excluded.label_counts_json,
          keyword_counts_json = excluded.keyword_counts_json,
          model_provider = excluded.model_provider,
          model_name = excluded.model_name,
          generated_at = excluded.generated_at,
          raw_json = excluded.raw_json
        """,
        (
            symbol,
            source,
            normalized_day,
            len(rows),
            positive_count,
            negative_count,
            neutral_count,
            score_stats["score"],
            sentiment_label(score_stats["score"]),
            score_stats["confidence"],
            conclusion_payload["conclusion"],
            json.dumps(dict(label_counts), ensure_ascii=False),
            json.dumps(keyword_counts, ensure_ascii=False),
            conclusion_payload["model_provider"],
            conclusion_payload["model_name"],
            SENTIMENT_METHOD_VERSION,
            generated_at,
            json.dumps(raw, ensure_ascii=False),
        ),
    )
    return {
        "symbol": symbol,
        "source": source,
        "trade_date": normalized_day,
        "analyzed_count": len(rows),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "neutral_count": neutral_count,
        "sentiment_score": score_stats["score"],
        "sentiment_label": sentiment_label(score_stats["score"]),
        "confidence": score_stats["confidence"],
        "conclusion": conclusion_payload["conclusion"],
        "label_counts": dict(label_counts),
        "keyword_counts": keyword_counts,
        "model_provider": conclusion_payload["model_provider"],
        "model_name": conclusion_payload["model_name"],
        "generated_at": generated_at,
    }


def community_daily_evidence_rows(
    conn: sqlite3.Connection,
    symbol: str,
    trade_date: str,
    source: str = "xueqiu",
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select *
        from sentiment_evidence
        where symbol = ?
          and sentiment_type = 'community'
          and source_table = 'community_posts'
          and source = ?
          and method_version = ?
          and substr(analyzed_at, 1, 10) = ?
        order by analyzed_at desc, id desc
        """,
        (symbol, source, SENTIMENT_METHOD_VERSION, trade_date),
    ).fetchall()
    items: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for row in rows:
        item = row_to_dict(row)
        source_id = str(item.get("source_id") or "")
        if source_id in seen_source_ids:
            continue
        seen_source_ids.add(source_id)
        item["keywords"] = parse_json(item.pop("keywords_json"), [])
        item["evidence"] = parse_json(item.pop("evidence_json"), {})
        if failed_text_llm_evidence(item):
            continue
        items.append(item)
    return items


def community_daily_score(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        return {"score": 0.0, "confidence": 0.0}
    scores = [normalize_community_score(row.get("sentiment_score")) for row in rows]
    confidences = [clamp_float(row.get("confidence"), 0.0, 1.0) for row in rows]
    class_counts = community_class_counts(rows)
    return {
        "score": sum(scores) / len(scores),
        "confidence": sum(confidences) / len(confidences),
        "class_counts": class_counts,
    }


def community_keyword_counts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in rows:
        for keyword in safe_string_list(row.get("keywords") or []):
            clean = keyword.strip()
            if clean:
                counter[clean] += 1
    return [{"keyword": keyword, "count": count} for keyword, count in counter.most_common(20)]


def community_daily_conclusion(
    symbol: str,
    trade_date: str,
    stats: dict[str, Any],
    use_llm: bool = True,
    llm_stats: dict[str, Any] | None = None,
) -> dict[str, str]:
    if not ENABLE_COMMUNITY_DAILY_CONCLUSION:
        return {"conclusion": "", "model_provider": "disabled", "model_name": ""}
    llm = preferred_llm_config()
    if use_llm and llm["configured"]:
        try:
            conclusion = llm_community_daily_conclusion(symbol, trade_date, stats, llm, llm_stats=llm_stats)
            if conclusion:
                return {"conclusion": conclusion, "model_provider": llm["provider"], "model_name": llm["model"]}
        except Exception:
            pass
    return {
        "conclusion": local_community_daily_conclusion(symbol, trade_date, stats),
        "model_provider": "local",
        "model_name": LOCAL_MODEL_NAME,
    }


def llm_community_daily_conclusion(
    symbol: str,
    trade_date: str,
    stats: dict[str, Any],
    llm: dict[str, Any],
    llm_stats: dict[str, Any] | None = None,
) -> str:
    started = time.monotonic()
    payload = {
        "model": llm["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是A股股吧情绪日度汇总器。只根据输入的聚合统计给出一句中文结论，"
                    "不要引用或复述单条评论原文，不要给买卖建议。请只返回JSON对象，格式为"
                    "{\"conclusion\":\"...\"}。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "prompt_version": SENTIMENT_PROMPT_VERSION,
                        "symbol": symbol,
                        "trade_date": trade_date,
                        "stats": stats,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        llm["endpoint"],
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {llm['api_key']}"},
        method="POST",
    )
    with urlopen(request, timeout=llm_timeout_seconds(community=True)) as response:
        body = response.read().decode("utf-8", errors="ignore")
    record_daily_conclusion_request(llm_stats, elapsed_ms(started))
    response_payload = json.loads(body)
    content = str(response_payload.get("choices", [{}])[0].get("message", {}).get("content") or "{}")
    parsed = parse_json_object(content)
    return str(parsed.get("conclusion") or "").strip()[:800]


def local_community_daily_conclusion(symbol: str, trade_date: str, stats: dict[str, Any]) -> str:
    analyzed = int(stats.get("analyzed_count") or 0)
    positive = int(stats.get("positive_count") or 0)
    negative = int(stats.get("negative_count") or 0)
    neutral = int(stats.get("neutral_count") or 0)
    score = float(stats.get("sentiment_score") or 0.0)
    keywords = [item["keyword"] for item in stats.get("top_keywords") or [] if item.get("keyword")][:5]
    tone = sentiment_label_text(sentiment_label(score))
    keyword_text = f"，高频词集中在{'、'.join(keywords)}" if keywords else ""
    return (
        f"{trade_date} {symbol} 股吧共分析 {analyzed} 条去重评论，"
        f"正面 {positive} 条、负面 {negative} 条、中性 {neutral} 条，"
        f"综合情绪为{tone}（{score:.1f}）{keyword_text}。"
    )


def community_daily_summaries(conn: sqlite3.Connection, symbol: str, days: int = 30, limit: int = 60) -> list[dict[str, Any]]:
    cutoff = cutoff_date(days)
    rows = conn.execute(
        """
        select *
        from community_sentiment_daily
        where symbol = ?
          and method_version = ?
          and trade_date >= ?
        order by trade_date desc, generated_at desc, id desc
        limit ?
        """,
        (symbol, SENTIMENT_METHOD_VERSION, cutoff, clean_limit(limit, 365)),
    ).fetchall()
    return [decode_community_daily(row) for row in rows]


def community_daily_candidate_symbols(conn: sqlite3.Connection, trade_date: str) -> list[str]:
    rows = conn.execute(
        """
        select distinct symbol
        from sentiment_evidence
        where sentiment_type = 'community'
          and source_table = 'community_posts'
          and method_version = ?
          and substr(analyzed_at, 1, 10) = ?
        order by symbol
        """,
        (SENTIMENT_METHOD_VERSION, trade_date),
    ).fetchall()
    return [str(row["symbol"]).upper() for row in rows]


def decode_community_daily(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    item["label_counts"] = parse_json(item.pop("label_counts_json"), {})
    item["keyword_counts"] = parse_json(item.pop("keyword_counts_json"), [])
    item["raw"] = parse_json(item.pop("raw_json"), {})
    if item.get("sentiment_score") is not None:
        item["sentiment_score"] = normalize_community_score(item["sentiment_score"])
    return item


def cleanup_expired_community_sentiment(
    conn: sqlite3.Connection,
    retention_days: int = COMMUNITY_DETAIL_RETENTION_DAYS,
) -> dict[str, Any]:
    days = max(1, min(int(retention_days or COMMUNITY_DETAIL_RETENTION_DAYS), 30))
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    evidence_by_analysis = conn.execute(
        """
        delete from sentiment_evidence
        where sentiment_type = 'community'
          and source_table = 'community_posts'
          and analyzed_at < ?
        """,
        (cutoff,),
    ).rowcount
    conn.commit()
    return {
        "mode": "community-sentiment-retention-cleanup",
        "retention_days": days,
        "cutoff": cutoff,
        "preserve_community_posts": True,
        "deleted": {
            "community_posts": 0,
            "community_evidence": max(evidence_by_analysis, 0),
        },
        "cleaned_at": now_iso(),
    }


def normalize_day(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = parse_date(text)
    return parsed.isoformat() if parsed else ""


def sentiment_label_text(label: str) -> str:
    return {
        "positive": "积极",
        "mild_positive": "偏积极",
        "negative": "消极",
        "mild_negative": "偏消极",
        "neutral": "中性",
    }.get(str(label or ""), "中性")


def failed_text_llm_evidence(item: dict[str, Any]) -> bool:
    sentiment_type = str(item.get("sentiment_type") or "")
    if sentiment_type not in {"filing_news", "community"}:
        return False
    if str(item.get("model_provider") or "") != "local":
        return False
    evidence = parse_json(item.get("evidence_json"), {}) if "evidence_json" in item else dict(item.get("evidence") or {})
    if evidence.get("structured_financial_score") is not None:
        return False
    return bool(evidence.get("fallback_reason") or evidence.get("llm_error"))


def community_analysis_day() -> str:
    return date.today().isoformat()


def resolve_sentiment_snapshot_row(
    conn: sqlite3.Connection,
    symbol: str,
    window_days: int | None = None,
) -> sqlite3.Row | None:
    params: list[Any] = [symbol, SENTIMENT_METHOD_VERSION]
    window_sql = ""
    if window_days is not None:
        window_sql = "and window_days = ?"
        params.append(clean_days(window_days))
    row = conn.execute(
        f"""
        select *
        from sentiment_snapshots
        where symbol = ?
          and method_version = ?
          {window_sql}
        order by generated_at desc, id desc
        limit 1
        """,
        tuple(params),
    ).fetchone()
    if row:
        return row
    fallback_params: list[Any] = [symbol]
    if window_days is not None:
        fallback_params.append(clean_days(window_days))
    return conn.execute(
        f"""
        select *
        from sentiment_snapshots
        where symbol = ?
          {window_sql}
        order by generated_at desc, id desc
        limit 1
        """,
        tuple(fallback_params),
    ).fetchone()


def community_evidence_method_versions(conn: sqlite3.Connection, symbol: str, trade_day: str) -> list[str]:
    rows = conn.execute(
        """
        select method_version, max(analyzed_at) as latest_analyzed_at
        from sentiment_evidence
        where symbol = ?
          and sentiment_type = 'community'
          and source_table = 'community_posts'
          and lower(source) not like '%mock%'
          and coalesce(nullif(substr(event_date, 1, 10), ''), substr(analyzed_at, 1, 10)) = ?
        group by method_version
        order by latest_analyzed_at desc
        """,
        (symbol, trade_day),
    ).fetchall()
    versions = [str(row["method_version"]) for row in rows if row["method_version"]]
    if SENTIMENT_METHOD_VERSION in versions:
        return [SENTIMENT_METHOD_VERSION] + [version for version in versions if version != SENTIMENT_METHOD_VERSION]
    return versions


def sentiment_evidence_day(item: dict[str, Any]) -> str:
    event_date = str(item.get("event_date") or "").strip()
    if event_date:
        return event_date[:10]
    analyzed_at = str(item.get("analyzed_at") or "").strip()
    return analyzed_at[:10] if analyzed_at else ""


def evidence_sentiment_label(item: dict[str, Any]) -> str:
    label = str(item.get("sentiment_label") or "")
    if label in {"positive", "mild_positive", "neutral", "mild_negative", "negative"}:
        return label
    if str(item.get("sentiment_type") or "") == "community":
        return community_sentiment_label(item.get("sentiment_score"))
    return sentiment_label(item.get("sentiment_score") or 0)


def sentiment_group_score(sentiment_type: str, items: list[dict[str, Any]], window_days: int) -> dict[str, float]:
    if sentiment_type == "community":
        return community_average_score(items)
    return weighted_score(items, window_days)


def community_average_score(items: list[dict[str, Any]]) -> dict[str, float]:
    if not items:
        return {"score": 0.0, "confidence": 0.0}
    scores = [normalize_community_score(item.get("sentiment_score")) for item in items]
    confidences = [clamp_float(item.get("confidence"), 0.0, 1.0) for item in items]
    class_counts = community_class_counts(items)
    return {
        "score": sum(scores) / len(scores),
        "confidence": sum(confidences) / len(confidences),
        "class_counts": class_counts,
        "positive_count": class_counts["正面"],
        "mild_positive_count": class_counts["偏正面"],
        "neutral_count": class_counts["中性"],
        "mild_negative_count": class_counts["偏负面"],
        "negative_count": class_counts["负面"],
    }


def community_source_breakdown(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        source = str(item.get("source") or "community").strip() or "community"
        grouped.setdefault(source, []).append(item)
    source_order = {"xueqiu": 0}
    rows: list[dict[str, Any]] = []
    for source, source_items in grouped.items():
        stats = community_average_score(source_items)
        rows.append(
            {
                "source": source,
                "score": stats.get("score"),
                "confidence": stats.get("confidence"),
                "count": len(source_items),
                "class_counts": stats.get("class_counts", {}),
            }
        )
    rows.sort(key=lambda item: (source_order.get(str(item.get("source") or ""), 99), -int(item.get("count") or 0), str(item.get("source") or "")))
    return rows


def community_class_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"正面": 0, "偏正面": 0, "中性": 0, "偏负面": 0, "负面": 0}
    for item in items:
        evidence = parse_json(item.get("evidence_json"), {}) if "evidence_json" in item else dict(item.get("evidence") or {})
        sentiment_class = evidence.get("sentiment_class")
        if not sentiment_class:
            sentiment_class = community_class_from_score(item.get("sentiment_score"))
        normalized, _ = community_sentiment_class_score(sentiment_class)
        counts[normalized] = counts.get(normalized, 0) + 1
    return counts


def weighted_score(items: list[dict[str, Any]], window_days: int) -> dict[str, float]:
    weighted_total = 0.0
    weight_total = 0.0
    confidence_total = 0.0
    for item in items:
        score = float(item.get("sentiment_score") or 0.0)
        confidence = clamp_float(item.get("confidence"), 0.0, 1.0)
        recency = recency_weight(str(item.get("event_date") or item.get("analyzed_at") or ""), window_days)
        weight = max(0.1, confidence) * recency
        weighted_total += score * weight
        confidence_total += confidence * weight
        weight_total += weight
    if weight_total <= 0:
        return {"score": 0.0, "confidence": 0.0}
    return {
        "score": clamp_score(weighted_total / weight_total),
        "confidence": clamp_float(confidence_total / weight_total, 0.0, 1.0),
    }


def sentiment_evidence_payload(conn: sqlite3.Connection, symbol: str, days: int = 30, limit: int = 30) -> dict[str, list[dict[str, Any]]]:
    cutoff = cutoff_date(days)
    rows = conn.execute(
        """
        select *
        from sentiment_evidence
        where symbol = ?
          and method_version = ?
          and lower(source) not like '%mock%'
          and coalesce(nullif(substr(event_date, 1, 10), ''), substr(analyzed_at, 1, 10)) >= ?
        order by coalesce(nullif(event_date, ''), analyzed_at) desc, abs(sentiment_score) desc, id desc
        limit ?
        """,
        (symbol, SENTIMENT_METHOD_VERSION, cutoff, clean_limit(limit, 200)),
    ).fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {"filing_news": [], "community": [], "market": []}
    for row in rows:
        item = row_to_dict(row)
        if item["sentiment_type"] == "community" and sentiment_evidence_day(item) != community_analysis_day():
            continue
        item["keywords"] = parse_json(item.pop("keywords_json"), [])
        item["evidence"] = parse_json(item.pop("evidence_json"), {})
        grouped.setdefault(item["sentiment_type"], []).append(item)
    grouped["community"] = current_community_evidence_rows(
        conn,
        symbol,
        limit=clean_limit(limit, 200),
        parse_payload=True,
    )
    return grouped


def decode_snapshot(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    item["source_counts"] = parse_json(item.pop("source_counts_json"), {})
    item["raw"] = parse_json(item.pop("raw_json"), {})
    return item


def current_community_evidence_rows(
    conn: sqlite3.Connection,
    symbol: str,
    limit: int | None = None,
    parse_payload: bool = False,
) -> list[dict[str, Any]]:
    trade_day = latest_community_evidence_day(conn, symbol, community_analysis_day()) or community_analysis_day()
    for method_version in community_evidence_method_versions(conn, symbol, trade_day):
        rows = _fetch_community_evidence_rows(
            conn,
            symbol,
            trade_day,
            method_version,
            limit=limit,
        )
        if rows:
            return _parse_community_evidence_rows(rows, parse_payload=parse_payload)
    return []


def latest_community_evidence_day(conn: sqlite3.Connection, symbol: str, preferred_day: str) -> str:
    row = conn.execute(
        """
        select coalesce(nullif(substr(event_date, 1, 10), ''), substr(analyzed_at, 1, 10)) as evidence_day
        from sentiment_evidence
        where symbol = ?
          and sentiment_type = 'community'
          and source_table = 'community_posts'
          and lower(source) not like '%mock%'
          and coalesce(nullif(substr(event_date, 1, 10), ''), substr(analyzed_at, 1, 10)) <= ?
        group by evidence_day
        order by evidence_day desc
        limit 1
        """,
        (symbol, preferred_day),
    ).fetchone()
    return str(row["evidence_day"] or "") if row else ""


def _fetch_community_evidence_rows(
    conn: sqlite3.Connection,
    symbol: str,
    trade_day: str,
    method_version: str,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    params: list[Any] = [symbol, method_version, trade_day]
    limit_sql = ""
    if limit:
        limit_sql = "limit ?"
        params.append(clean_limit(limit, 200))
    return conn.execute(
        f"""
        select se.*, cp.title as source_title, cp.content as source_content, cp.raw_json as source_raw_json
        from sentiment_evidence se
        left join community_posts cp
          on se.source_table = 'community_posts'
         and se.source_id = cast(cp.id as text)
        where se.symbol = ?
          and se.sentiment_type = 'community'
          and se.source_table = 'community_posts'
          and se.method_version = ?
          and lower(se.source) not like '%mock%'
          and coalesce(nullif(substr(se.event_date, 1, 10), ''), substr(se.analyzed_at, 1, 10)) = ?
        order by coalesce(nullif(se.event_date, ''), se.analyzed_at) desc, se.analyzed_at desc, se.id desc
        {limit_sql}
        """,
        tuple(params),
    ).fetchall()


def _parse_community_evidence_rows(
    rows: list[sqlite3.Row],
    parse_payload: bool = False,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen_source_ids: set[str] = set()
    for row in rows:
        item = row_to_dict(row)
        source_title = item.pop("source_title", "")
        source_content = item.pop("source_content", "")
        source_raw = parse_json(item.pop("source_raw_json", "{}"), {})
        has_source_content = bool(str(source_content or "").strip())
        item["source_text"] = community_post_text(source_title or item.get("title"), source_content)
        item["source_text_kind"] = "detail_text" if has_source_content else "list_title"
        item["source_content_available"] = has_source_content
        item["source_detail_error"] = str(source_raw.get("detail_error") or "")
        item["source_original_verified"] = has_source_content
        source_id = str(item.get("source_id") or "")
        if source_id and source_id in seen_source_ids:
            continue
        if source_id:
            seen_source_ids.add(source_id)
        if failed_text_llm_evidence(item):
            continue
        if parse_payload:
            item["keywords"] = parse_json(item.pop("keywords_json"), [])
            item["evidence"] = parse_json(item.pop("evidence_json"), {})
        item["sentiment_score"] = normalize_community_score(item.get("sentiment_score"))
        items.append(item)
    return items


def apply_current_community_snapshot(conn: sqlite3.Connection, snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not snapshot:
        return snapshot
    symbol = str(snapshot.get("symbol") or "").upper()
    if not symbol:
        return snapshot
    current_rows = current_community_evidence_rows(conn, symbol)
    source_counts = dict(snapshot.get("source_counts") or {})
    raw = dict(snapshot.get("raw") or {})
    type_scores = dict(raw.get("type_scores") or {})
    if current_rows:
        community_stats = community_average_score(current_rows)
        community_sources = community_source_breakdown(current_rows)
        source_counts["community"] = len(current_rows)
        type_scores["community"] = community_stats
        snapshot["community_score"] = community_stats["score"]
    else:
        community_sources = []
        source_counts["community"] = 0
        type_scores.pop("community", None)
        snapshot["community_score"] = None
    raw["type_scores"] = type_scores
    raw["source_counts"] = source_counts
    raw["community_sources"] = community_sources
    raw["community_scope"] = {
        "day": community_analysis_day(),
        "prompt_version": SENTIMENT_PROMPT_VERSION,
        "method_version": SENTIMENT_METHOD_VERSION,
        "current_count": len(current_rows),
        "sources": community_sources,
        "score_method": "today community LLM sentiment_score (-100 to 100) average with sentiment_class counts",
    }
    snapshot["source_counts"] = source_counts
    snapshot["raw"] = raw
    recompute_snapshot_scores(snapshot)
    return snapshot


def recompute_snapshot_scores(snapshot: dict[str, Any]) -> None:
    raw = dict(snapshot.get("raw") or {})
    type_scores = dict(raw.get("type_scores") or {})
    score_fields = {
        "filing_news": "filing_news_score",
        "community": "community_score",
        "market": "market_score",
    }
    weights = {"filing_news": 0.40, "community": 0.25, "market": 0.35}
    available: dict[str, dict[str, float]] = {}
    for key, score_field in score_fields.items():
        stats = type_scores.get(key) if isinstance(type_scores.get(key), dict) else {}
        score_value = number(stats.get("score") if stats else snapshot.get(score_field))
        if score_value is None:
            continue
        confidence_value = number(stats.get("confidence") if stats else None, snapshot.get("confidence") or 0.0)
        available[key] = {
            "score": score_value,
            "confidence": clamp_float(confidence_value, 0.0, 1.0),
        }
    weight_sum = sum(weights[key] for key in available) or 1.0
    composite = sum(available[key]["score"] * weights[key] for key in available) / weight_sum
    confidence = sum(available[key]["confidence"] * weights[key] for key in available) / weight_sum
    snapshot["composite_score"] = composite
    snapshot["confidence"] = clamp_float(confidence, 0.0, 1.0)
    snapshot["sentiment_label"] = sentiment_label(composite)


def score_financial_metrics(item: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    revenue_growth = percentish(item.get("revenue_growth"))
    roe = percentish(item.get("roe"))
    gross_margin = percentish(item.get("gross_margin"))
    net_margin = percentish(item.get("net_margin"))
    debt_ratio = percentish(item.get("debt_ratio") if item.get("debt_ratio") is not None else item.get("liability_to_asset"))
    net_profit = number(item.get("net_profit"))
    score = 0.0
    details = {
        "revenue_growth": revenue_growth,
        "roe": roe,
        "gross_margin": gross_margin,
        "net_margin": net_margin,
        "debt_ratio": debt_ratio,
        "net_profit": net_profit,
    }
    if revenue_growth is not None:
        score += clamp_float(revenue_growth, -60, 80) * 0.35
    if roe is not None:
        score += (roe - 8) * 1.4
    if net_margin is not None:
        score += (net_margin - 5) * 0.8
    elif gross_margin is not None:
        score += (gross_margin - 20) * 0.35
    if debt_ratio is not None and debt_ratio > 70:
        score -= (debt_ratio - 70) * 0.8
    if net_profit is not None and net_profit < 0:
        score -= 24
    return clamp_score(score), details


def financial_metric_text(item: dict[str, Any]) -> str:
    score, details = score_financial_metrics(item)
    fields = [f"{key}={value}" for key, value in details.items() if value is not None]
    return f"{item.get('report_period')} {item.get('provider')} 基本面评分 {score:.1f}; " + "; ".join(fields)


def normalize_financial_event_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return "-".join(match.groups())
    match = re.search(r"(\d{4})(\d{2})(\d{2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"
    match = re.search(r"(\d{4})\s*[Qq]\s*([1-4])", text)
    if match:
        year = int(match.group(1))
        quarter = int(match.group(2))
        month = quarter * 3
        day = {3: 31, 6: 30, 9: 30, 12: 31}[month]
        return date(year, month, day).isoformat()
    return text[:10] if parse_date(text) else ""


def llm_analyze_text(text: str, title: str = "", category: str = "", timeout: int | None = None, community: bool = False) -> dict[str, Any]:
    config = preferred_llm_config()
    if not config["configured"]:
        raise RuntimeError("No LLM API key configured")
    return chat_completion_analyze_text(
        endpoint=config["endpoint"],
        api_key=config["api_key"],
        model=config["model"],
        text=text,
        title=title,
        category=category,
        timeout=timeout or llm_timeout_seconds(community=community),
        community=community,
    )


def llm_analyze_text_batch(
    items: list[dict[str, Any]],
    timeout: int | None = None,
    community: bool = False,
) -> list[dict[str, Any]]:
    config = preferred_llm_config()
    if not config["configured"]:
        raise RuntimeError("No LLM API key configured")
    return chat_completion_analyze_text_batch(
        endpoint=config["endpoint"],
        api_key=config["api_key"],
        model=config["model"],
        items=items,
        timeout=timeout or llm_timeout_seconds(community=community),
        community=community,
    )


def glm_analyze_text(text: str, title: str = "", category: str = "", timeout: int = 25) -> dict[str, Any]:
    api_key = glm_api_key()
    if not api_key:
        raise RuntimeError("GLM_API_KEY is not configured")
    return chat_completion_analyze_text(
        endpoint=glm_endpoint(),
        api_key=api_key,
        model=glm_model(),
        text=text,
        title=title,
        category=category,
        timeout=timeout,
    )


def deepseek_analyze_text(text: str, title: str = "", category: str = "", timeout: int = 25) -> dict[str, Any]:
    api_key = deepseek_api_key()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    return chat_completion_analyze_text(
        endpoint=deepseek_endpoint(),
        api_key=api_key,
        model=deepseek_model(),
        text=text,
        title=title,
        category=category,
        timeout=timeout,
    )


def chat_completion_analyze_text(
    endpoint: str,
    api_key: str,
    model: str,
    text: str,
    title: str = "",
    category: str = "",
    timeout: int = 25,
    community: bool = False,
) -> dict[str, Any]:
    compact_text = re.sub(r"\s+", " ", text or "").strip()[:3500]
    prompt = sentiment_llm_prompt(community=community, batch=False)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "prompt_version": SENTIMENT_PROMPT_VERSION,
                        "title": title,
                        "category_hint": category,
                        "text": compact_text,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"LLM request failed: {exc}") from exc
    payload = json.loads(body)
    content = str(payload.get("choices", [{}])[0].get("message", {}).get("content") or "{}")
    return parse_json_object(content)


def sentiment_llm_prompt(community: bool = False, batch: bool = True) -> str:
    if community:
        output_shape = (
            "请只返回JSON对象，格式为"
            "{\"items\":[{\"id\":\"\",\"index\":0,\"sentiment_score\":0,\"sentiment_class\":\"中性\","
            "\"confidence\":0.5,\"keywords\":[]}]}。"
            if batch
            else "请只返回JSON对象，字段包括 sentiment_score, sentiment_class, confidence, keywords, reason。"
        )
        return (
            "你是A股股吧短帖情绪分类器。核心任务：判断文本对“这只股票/股价后续表现”的情绪，"
            "不要把发帖人的个人心情直接当作股票情绪。股吧短帖常有反话、黑话和省略语，必须按投资语义解释。"
            "输入会提供stock_name/current_price/change_pct等上下文，表示评论所在股吧对应标的；"
            "change_pct是最近交易日涨跌幅(%)，必须结合名称、现价与涨跌幅判断，不要把评论里提到的其他股票名误当成目标股。"
            f"{output_shape}"
            "批量输入时，每个输出项必须保留输入项的id，并按输入顺序返回；不要漏项、不要新增项。"
            "sentiment_score范围-100到100，由你直接给出，正数偏利好股价、负数偏利空、0为中性，"
            "分数应反映强弱程度（例如明显利好可给60到90，轻微偏正约10到30）。"
            "sentiment_class只能是：正面、偏正面、中性、偏负面、负面，必须与sentiment_score方向一致。"
            "confidence范围0到1，keywords提取1到5个原文情绪词或短语。"
            "社区语义规则："
            "1. “卖飞、卖早了、踏空、后悔卖了、没拿住”表示股票涨得比卖出者预期强，通常是偏正面或正面；"
            "不要因为“遗憾、后悔”给股票负分。"
            "2. “可以了、可以可以、舒服、满意、起飞、飞、突破、指标线还没跟上、指标滞后”通常表达上涨强势或满意，"
            "应偏正面；只有同时明确出现“别追、见顶、危险、诱多、出货”等才降为中性或负面。"
            "3. “甩下车、洗盘、震仓、散户下车、拿不住”在股吧语境常表示强势上涨/主力洗盘叙事，通常中性偏正面；"
            "不要自动归为风险提示。"
            "4. 只有明确出现“出货、诱多、见顶、高位别追、崩、跌停、割肉、套牢、亏麻、利空、处罚、退市、暴雷”等，"
            "才给明显负分，sentiment_class应为偏负面或负面。"
            "5. 短文本或语义不完整时降低confidence；不要为了一个孤立词给极端分。"
        )
    output_shape = (
        "请只返回JSON对象，格式为"
        "{\"items\":[{\"id\":\"community:community_posts:123\",\"index\":0,\"sentiment_score\":0,\"confidence\":0.5,"
        "\"category\":\"neutral\",\"impact_horizon\":\"1w\",\"keywords\":[],\"reason\":\"\"}]}。"
        if batch
        else "请只返回JSON对象，字段包括 sentiment_score, confidence, category, impact_horizon, keywords, reason。"
    )
    common = (
        f"{output_shape}"
        "批量输入时，每个输出项必须保留输入项的id，并按输入顺序返回；不要漏项、不要新增项。"
        "sentiment_score范围-100到100，confidence范围0到1，impact_horizon只能是1d/1w/1m/1q。"
        "keywords提取1到8个情绪面关键词或短语，优先使用原文中的词；不要只返回股票名、公司名或宽泛行业名。"
        "reason用一句中文说明判定依据，不要给买卖建议。"
    )
    return (
        "你是A股公告、新闻和财报文本情绪分类器。核心任务：判断文本事实对上市公司/股票投资情绪的影响，"
        "不要只按单个情绪词打分，要看事件本身。"
        f"{common}"
        "公告/新闻语义规则：业绩增长、回购、增持、中标、分红、审核通过、订单合同通常偏正面；"
        "减持、监管处罚、立案、问询、亏损、违约、债务逾期、诉讼、退市风险通常偏负面；"
        "普通披露、例行报告、无方向信息保持中性。"
    )


def chat_completion_analyze_text_batch(
    endpoint: str,
    api_key: str,
    model: str,
    items: list[dict[str, Any]],
    timeout: int = 45,
    community: bool = False,
) -> list[dict[str, Any]]:
    compact_items = []
    for index, item in enumerate(items):
        compact_text = re.sub(r"\s+", " ", str(item.get("text") or item.get("title") or "")).strip()
        compact_text = compact_text[:llm_text_limit(community=community)]
        if community:
            compact_item = {
                "id": llm_item_id(item),
                "index": index,
                "text": compact_text,
            }
            stock_context = community_llm_stock_context(item)
            if stock_context:
                compact_item.update(stock_context)
            compact_items.append(compact_item)
        else:
            compact_items.append(
                {
                    "id": llm_item_id(item),
                    "index": index,
                    "title": str(item.get("title") or "")[:220],
                    "category_hint": str(item.get("category") or "")[:80],
                    "source": str(item.get("source") or "")[:80],
                    "source_table": str(item.get("source_table") or "")[:80],
                    "sentiment_type": str(item.get("sentiment_type") or "")[:80],
                    "text": compact_text,
                }
            )
    prompt = sentiment_llm_prompt(community=community, batch=True)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "prompt_version": SENTIMENT_PROMPT_VERSION,
                        "mode": "community_posts" if community else "filing_news",
                        "items": compact_items,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"LLM batch request failed: {exc}") from exc
    payload = json.loads(body)
    content = str(payload.get("choices", [{}])[0].get("message", {}).get("content") or "{}")
    parsed = parse_json_object(content)
    rows = parsed.get("items") or parsed.get("results") or []
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def deepseek_api_key() -> str:
    for name in DEEPSEEK_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    values = dotenv_values()
    for name in DEEPSEEK_ENV_NAMES:
        value = values.get(name, "").strip()
        if value:
            os.environ[name] = value
            return value
    return ""


def deepseek_model() -> str:
    return os.environ.get("DEEPSEEK_MODEL", "").strip() or dotenv_values().get("DEEPSEEK_MODEL", "").strip() or "deepseek-chat"


def deepseek_endpoint() -> str:
    return os.environ.get("DEEPSEEK_API_BASE", "").strip() or dotenv_values().get("DEEPSEEK_API_BASE", "").strip() or DEEPSEEK_ENDPOINT


def glm_api_key() -> str:
    for name in GLM_ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    values = dotenv_values()
    for name in GLM_ENV_NAMES:
        value = values.get(name, "").strip()
        if value:
            os.environ[name] = value
            return value
    return ""


def glm_model() -> str:
    return os.environ.get("GLM_MODEL", "").strip() or dotenv_values().get("GLM_MODEL", "").strip() or "glm-4.5-air"


def glm_endpoint() -> str:
    return os.environ.get("GLM_API_BASE", "").strip() or dotenv_values().get("GLM_API_BASE", "").strip() or GLM_ENDPOINT


def preferred_llm_config() -> dict[str, Any]:
    glm_key = glm_api_key()
    if glm_key:
        return {
            "provider": "glm",
            "configured": True,
            "api_key": glm_key,
            "model": glm_model(),
            "endpoint": glm_endpoint(),
        }
    deepseek_key = deepseek_api_key()
    if deepseek_key:
        return {
            "provider": "deepseek",
            "configured": True,
            "api_key": deepseek_key,
            "model": deepseek_model(),
            "endpoint": deepseek_endpoint(),
        }
    return {"provider": "", "configured": False, "api_key": "", "model": "", "endpoint": ""}


def llm_config_status(mask: bool = True) -> dict[str, Any]:
    preferred = preferred_llm_config()
    return {
        "preferred_provider": preferred["provider"],
        "preferred_configured": bool(preferred["configured"]),
        "glm": glm_config_status(mask=mask),
        "deepseek": deepseek_config_status(mask=mask),
    }


def glm_config_status(mask: bool = True) -> dict[str, Any]:
    key = glm_api_key()
    return {
        "configured": bool(key),
        "credential_hint": mask_secret(key) if key and mask else "",
        "env_names": list(GLM_ENV_NAMES),
        "model": glm_model(),
        "endpoint": glm_endpoint(),
    }


def deepseek_config_status(mask: bool = True) -> dict[str, Any]:
    key = deepseek_api_key()
    return {
        "configured": bool(key),
        "credential_hint": mask_secret(key) if key and mask else "",
        "env_names": list(DEEPSEEK_ENV_NAMES),
        "model": deepseek_model(),
        "endpoint": deepseek_endpoint(),
    }


def dotenv_values(path: Path = ENV_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def normalize_symbols(conn: sqlite3.Connection, symbols: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in symbols:
        symbol = normalize_symbol(conn, raw)
        if symbol and symbol not in seen:
            normalized.append(symbol)
            seen.add(symbol)
    return normalized


def normalize_symbol(conn: sqlite3.Connection, raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    resolved = resolve_symbol(conn, text, "all")
    if resolved:
        return str(resolved["symbol"]).upper()
    return (infer_symbol(text.upper()) or text.upper()).strip()


def sentiment_account_id(account_id: str | None = None) -> str:
    explicit = str(account_id or os.environ.get("KEIKO_SENTIMENT_ACCOUNT_ID", "")).strip()
    return explicit or DEFAULT_SENTIMENT_ACCOUNT_ID


def resolve_sentiment_target_symbols(
    conn: sqlite3.Connection,
    symbols: list[str],
    *,
    days: int = 30,
    limit: int = 80,
    account_id: str | None = None,
    favorites_only: bool = False,
) -> tuple[list[str], str]:
    target_symbols = normalize_symbols(conn, symbols)
    if target_symbols:
        return target_symbols, "requested"
    favorite_symbols = normalize_symbols(
        conn,
        favorite_symbols_for_accounts(conn, sentiment_account_id(account_id)),
    )
    if favorite_symbols:
        return favorite_symbols, "account_favorites"
    if favorites_only:
        return [], "account_favorites_empty"
    return sentiment_candidate_symbols(conn, limit=limit, days=days), "recent_activity"


def sentiment_candidate_symbols(conn: sqlite3.Connection, limit: int = 80, days: int = 30) -> list[str]:
    cutoff = cutoff_date(days)
    rows = conn.execute(
        """
        select symbol, max(latest_at) as latest_at
        from (
          select symbol, max(published_at) as latest_at from filings_history where substr(published_at, 1, 10) >= ? group by symbol
          union all
          select symbol, max(fetched_at) as latest_at from community_posts where substr(fetched_at, 1, 10) >= ? group by symbol
          union all
          select symbol, max(trade_date) as latest_at from daily_bars where trade_date >= ? group by symbol
        )
        group by symbol
        order by latest_at desc
        limit ?
        """,
        (cutoff, cutoff, cutoff, clean_limit(limit, 500)),
    ).fetchall()
    return [str(row["symbol"]).upper() for row in rows]


def scalar_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"select count(*) as count from {table}").fetchone()["count"])


def new_llm_inventory() -> dict[str, dict[str, int]]:
    return {
        "community": {"total": 0, "cache_hits": 0, "uncached": 0},
        "filing_news": {"total": 0, "cache_hits": 0, "uncached": 0},
    }


def new_sentiment_performance() -> dict[str, Any]:
    llm = preferred_llm_config()
    return {
        "total_ms": 0,
        "steps": [],
        "llm": {
            "provider": llm["provider"],
            "model": llm["model"],
            "configured": bool(llm["configured"]),
            "batch_size": llm_batch_size(),
            "community_batch_size": llm_batch_size(community=True),
            "community_retry_batch_size": llm_retry_batch_size(community=True),
            "concurrency": llm_concurrency(),
            "timeout_seconds": llm_timeout_seconds(),
            "community_timeout_seconds": llm_timeout_seconds(community=True),
            "requests": 0,
            "items": 0,
            "cache_hits": 0,
            "duration_ms": 0,
            "errors": 0,
            "fallback_items": 0,
            "daily_conclusion_requests": 0,
            "inventory": new_llm_inventory(),
        },
    }


def record_sentiment_step(
    performance: dict[str, Any],
    step: str,
    started: float,
    extra: dict[str, Any] | None = None,
) -> None:
    item = {"step": step, "duration_ms": elapsed_ms(started)}
    if extra:
        item.update(extra)
    performance.setdefault("steps", []).append(item)


def merge_sentiment_performance(target: dict[str, Any], source: dict[str, Any], symbol: str = "") -> None:
    for step in source.get("steps") or []:
        item = dict(step)
        if symbol:
            item["symbol"] = symbol
        target.setdefault("steps", []).append(item)
    merge_llm_stats(target.setdefault("llm", {}), source.get("llm") or {})


def merge_llm_stats(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key in ("requests", "items", "cache_hits", "duration_ms", "errors", "fallback_items", "daily_conclusion_requests"):
        target[key] = int(target.get(key) or 0) + int(source.get(key) or 0)
    source_inventory = source.get("inventory") or {}
    if source_inventory:
        target_inventory = target.setdefault("inventory", new_llm_inventory())
        for channel, values in source_inventory.items():
            bucket = target_inventory.setdefault(channel, {"total": 0, "cache_hits": 0, "uncached": 0})
            for field in ("total", "cache_hits", "uncached"):
                bucket[field] = int(bucket.get(field) or 0) + int((values or {}).get(field) or 0)
    for key in (
        "provider",
        "model",
        "configured",
        "batch_size",
        "community_batch_size",
        "community_retry_batch_size",
        "concurrency",
        "timeout_seconds",
        "community_timeout_seconds",
    ):
        if key not in target or target.get(key) in ("", None, False):
            target[key] = source.get(key)


def record_llm_cache_hits(stats: dict[str, Any] | None, count: int) -> None:
    if not stats or count <= 0:
        return
    stats["cache_hits"] = int(stats.get("cache_hits") or 0) + int(count)


def record_llm_inventory(stats: dict[str, Any] | None, channel: str, total: int, cache_hits: int) -> None:
    if not stats:
        return
    total = max(0, int(total or 0))
    cache_hits = max(0, min(int(cache_hits or 0), total))
    uncached = max(0, total - cache_hits)
    inventory = stats.setdefault("inventory", new_llm_inventory())
    bucket = inventory.setdefault(channel, {"total": 0, "cache_hits": 0, "uncached": 0})
    bucket["total"] = int(bucket.get("total") or 0) + total
    bucket["cache_hits"] = int(bucket.get("cache_hits") or 0) + cache_hits
    bucket["uncached"] = int(bucket.get("uncached") or 0) + uncached
    record_llm_cache_hits(stats, cache_hits)


def record_daily_conclusion_request(stats: dict[str, Any] | None, duration_ms: int = 0) -> None:
    if not stats:
        return
    stats["daily_conclusion_requests"] = int(stats.get("daily_conclusion_requests") or 0) + 1
    stats["requests"] = int(stats.get("requests") or 0) + 1
    stats["items"] = int(stats.get("items") or 0) + 1
    stats["duration_ms"] = int(stats.get("duration_ms") or 0) + int(duration_ms or 0)


def summarize_llm_usage(llm_stats: dict[str, Any] | None) -> dict[str, Any]:
    stats = dict(llm_stats or {})
    inventory = stats.get("inventory") or new_llm_inventory()
    total_items = sum(int((bucket or {}).get("total") or 0) for bucket in inventory.values())
    inventory_cache_hits = sum(int((bucket or {}).get("cache_hits") or 0) for bucket in inventory.values())
    inventory_uncached = sum(int((bucket or {}).get("uncached") or 0) for bucket in inventory.values())
    cache_hits = int(stats.get("cache_hits") or 0)
    llm_requests = int(stats.get("requests") or 0)
    llm_request_items = int(stats.get("items") or 0)
    daily_conclusion_requests = int(stats.get("daily_conclusion_requests") or 0)
    comment_llm_requests = max(0, llm_requests - daily_conclusion_requests)
    comment_llm_items = max(0, llm_request_items - daily_conclusion_requests)
    return {
        "provider": stats.get("provider"),
        "model": stats.get("model"),
        "configured": bool(stats.get("configured")),
        "inventory": inventory,
        "cache_hits": cache_hits,
        "llm_requests": llm_requests,
        "llm_request_items": llm_request_items,
        "comment_llm_requests": comment_llm_requests,
        "comment_llm_items": comment_llm_items,
        "daily_conclusion_requests": daily_conclusion_requests,
        "fallback_items": int(stats.get("fallback_items") or 0),
        "errors": int(stats.get("errors") or 0),
        "duration_ms": int(stats.get("duration_ms") or 0),
        "totals": {
            "items": total_items,
            "cache_hits": inventory_cache_hits,
            "uncached": inventory_uncached,
        },
        "accounting": {
            "cache_hits_match_inventory": cache_hits == inventory_cache_hits,
            "inventory_balanced": inventory_cache_hits + inventory_uncached == total_items,
            "uncached_covers_llm_items": comment_llm_items <= inventory_uncached,
        },
    }


def build_agent_usage(result: dict[str, Any]) -> dict[str, Any]:
    sentiment = result.get("sentiment") or {}
    performance = sentiment.get("performance") or {}
    llm_usage = summarize_llm_usage(performance.get("llm") or {})
    sentiment_counts = sentiment.get("counts") or {}
    daily = result.get("daily") or {}
    live = result.get("live_refresh") or {}
    cleanup = result.get("cleanup") or {}
    llm_usage["cycle"] = {
        "symbol_source": result.get("symbol_source"),
        "account_id": result.get("account_id"),
        "symbols": len(result.get("symbols") or []),
        "skipped": bool(result.get("skipped")),
        "timed_out": bool(result.get("timed_out")),
        "cycle_timeout_seconds": result.get("cycle_timeout_seconds"),
        "parallel_batch_size": int((sentiment.get("parallel_batch_size") or 0) or 0) or None,
        "community_posts_crawled": int(sentiment_counts.get("community_posts_crawled") or sentiment_counts.get("community_posts") or 0),
        "community_posts_today": int(sentiment_counts.get("community_posts_today") or sentiment_counts.get("community_evidence") or 0),
        "community_evidence": int(sentiment_counts.get("community_evidence") or 0),
        "filing_news_evidence": int(sentiment_counts.get("filing_news_evidence") or 0),
        "market_evidence": int(sentiment_counts.get("market_evidence") or 0),
        "snapshots": int(sentiment_counts.get("snapshots") or 0),
        "daily_summaries": int((daily.get("counts") or {}).get("symbols") or 0),
        "duration_ms": int(performance.get("total_ms") or 0),
    }
    llm_usage["live_refresh"] = live.get("counts") or {}
    llm_usage["cleanup"] = cleanup.get("deleted") or {}
    llm_usage["method_version"] = result.get("method_version")
    llm_usage["prompt_version"] = result.get("prompt_version")
    return llm_usage


def collect_cycle_errors(result: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for key in ("live_refresh", "sentiment", "daily"):
        payload = result.get(key) or {}
        for item in payload.get("errors") or []:
            if isinstance(item, dict):
                errors.append({str(k): str(v) for k, v in item.items()})
    return errors


def recent_sentiment_agent_runs(conn: sqlite3.Connection, limit: int = 10) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select id, provider, scope, status, started_at, finished_at, requested_symbols,
               updated_symbols, counts_json, errors_json
        from ingestion_runs
        where provider = 'community-sentiment-agent'
        order by id desc
        limit ?
        """,
        (clean_limit(limit, 50),),
    ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_dict(row)
        item["requested_symbols"] = parse_json(item.pop("requested_symbols", "[]"), [])
        item["updated_symbols"] = parse_json(item.pop("updated_symbols", "[]"), [])
        item["counts"] = parse_json(item.pop("counts_json", "{}"), {})
        item["errors"] = parse_json(item.pop("errors_json", "[]"), [])
        item["usage"] = item["counts"] if isinstance(item["counts"], dict) else {}
        items.append(item)
    return items


def record_llm_fallbacks(stats: dict[str, Any] | None, count: int) -> None:
    if not stats or count <= 0:
        return
    stats["fallback_items"] = int(stats.get("fallback_items") or 0) + int(count)


def record_llm_request(stats: dict[str, Any] | None, item_count: int, duration_ms: int, error: str = "") -> None:
    if not stats:
        return
    stats["requests"] = int(stats.get("requests") or 0) + 1
    stats["items"] = int(stats.get("items") or 0) + int(item_count)
    stats["duration_ms"] = int(stats.get("duration_ms") or 0) + int(duration_ms)
    if error:
        stats["errors"] = int(stats.get("errors") or 0) + 1


def clean_days(days: int) -> int:
    return max(1, min(int(days or 30), 365))


def clean_limit(limit: int, upper: int) -> int:
    return max(1, min(int(limit or upper), upper))


def llm_batch_size(community: bool = False) -> int:
    if community:
        value = os.environ.get("KEIKO_SENTIMENT_COMMUNITY_LLM_BATCH_SIZE", "").strip()
        default = LLM_COMMUNITY_BATCH_SIZE
        upper = 200
    else:
        value = os.environ.get("KEIKO_SENTIMENT_LLM_BATCH_SIZE", "").strip()
        default = LLM_BATCH_SIZE
        upper = 50
    try:
        parsed = int(value)
    except ValueError:
        parsed = default
    return max(1, min(parsed, upper))


def llm_retry_batch_size(community: bool = False) -> int:
    if not community:
        return llm_batch_size(community=False)
    value = os.environ.get("KEIKO_SENTIMENT_COMMUNITY_LLM_RETRY_BATCH_SIZE", "").strip()
    try:
        parsed = int(value)
    except ValueError:
        parsed = LLM_COMMUNITY_RETRY_BATCH_SIZE
    return max(1, min(parsed, llm_batch_size(community=True)))


def llm_text_limit(community: bool = False) -> int:
    if community:
        value = os.environ.get("KEIKO_SENTIMENT_COMMUNITY_TEXT_LIMIT", "").strip()
        default = LLM_COMMUNITY_TEXT_LIMIT
        upper = 2000
    else:
        value = os.environ.get("KEIKO_SENTIMENT_TEXT_LIMIT", "").strip()
        default = 900
        upper = 3500
    try:
        parsed = int(value)
    except ValueError:
        parsed = default
    return max(120 if community else 300, min(parsed, upper))


def llm_timeout_seconds(community: bool = False) -> int:
    if community:
        value = os.environ.get("KEIKO_SENTIMENT_COMMUNITY_LLM_TIMEOUT", "").strip()
        default = LLM_COMMUNITY_TIMEOUT_SECONDS
    else:
        value = os.environ.get("KEIKO_SENTIMENT_LLM_TIMEOUT", "").strip()
        default = LLM_BATCH_TIMEOUT_SECONDS
    try:
        parsed = int(value)
    except ValueError:
        parsed = default
    return max(5, min(parsed, 120))


def sentiment_symbol_batch_size() -> int:
    value = os.environ.get("KEIKO_SENTIMENT_SYMBOL_BATCH_SIZE", "").strip()
    try:
        parsed = int(value)
    except ValueError:
        parsed = SENTIMENT_SYMBOL_BATCH_SIZE
    return max(1, min(parsed, 20))


def chunked_symbols(symbols: list[str], size: int) -> list[list[str]]:
    batch_size = max(1, size)
    return [symbols[index : index + batch_size] for index in range(0, len(symbols), batch_size)]


def sentiment_cycle_timeout_seconds() -> float:
    value = os.environ.get("KEIKO_SENTIMENT_CYCLE_TIMEOUT_SECONDS", "").strip()
    try:
        parsed = float(value)
    except ValueError:
        parsed = SENTIMENT_CYCLE_TIMEOUT_SECONDS
    return max(60.0, min(parsed, 7200.0))


def resolve_cycle_timeout_seconds(cycle_timeout_seconds: float | None) -> float | None:
    if cycle_timeout_seconds is not None:
        if cycle_timeout_seconds <= 0:
            return None
        return max(60.0, min(float(cycle_timeout_seconds), 7200.0))
    return sentiment_cycle_timeout_seconds()


def cycle_deadline_from_timeout(cycle_timeout_seconds: float | None) -> tuple[float | None, float | None]:
    resolved = resolve_cycle_timeout_seconds(cycle_timeout_seconds)
    if resolved is None:
        return None, None
    return time.monotonic() + resolved, resolved


def cycle_deadline_exceeded(cycle_deadline: float | None) -> bool:
    return cycle_deadline is not None and time.monotonic() >= cycle_deadline


def cycle_timeout_error(
    cycle_deadline: float | None,
    scope: str,
    *,
    pending_symbols: list[str] | None = None,
    configured_timeout_seconds: float | None = None,
) -> dict[str, str]:
    configured = configured_timeout_seconds or resolve_cycle_timeout_seconds(None) or SENTIMENT_CYCLE_TIMEOUT_SECONDS
    pending = [str(symbol) for symbol in (pending_symbols or []) if str(symbol).strip()]
    message = f"{scope} stopped after {configured:.0f}s cycle timeout"
    if pending:
        preview = ", ".join(pending[:8])
        suffix = f" (+{len(pending) - 8} more)" if len(pending) > 8 else ""
        message = f"{message}; pending={preview}{suffix}"
    return {
        "scope": scope,
        "error": message,
        "pending_symbols": ",".join(pending),
        "timeout_seconds": str(int(configured)),
    }


def llm_concurrency() -> int:
    value = os.environ.get("KEIKO_SENTIMENT_LLM_CONCURRENCY", "").strip()
    try:
        parsed = int(value)
    except ValueError:
        parsed = LLM_MAX_CONCURRENCY
    return max(1, min(parsed, 4))


def elapsed_ms(started: float) -> int:
    return int(round((time.monotonic() - started) * 1000))


def cutoff_date(days: int) -> str:
    return (date.today() - timedelta(days=clean_days(days))).isoformat()


def parse_json(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    try:
        return json.loads(str(value))
    except (TypeError, json.JSONDecodeError):
        return fallback


def parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", value, flags=re.S)
        if not match:
            return {}
        return json.loads(match.group(0))


def sentiment_label(score: Any) -> str:
    value = float(score or 0.0)
    if value >= 35:
        return "positive"
    if value <= -35:
        return "negative"
    if value >= 12:
        return "mild_positive"
    if value <= -12:
        return "mild_negative"
    return "neutral"


def clamp_score(value: Any) -> float:
    return clamp_float(value, -100.0, 100.0)


def clamp_float(value: Any, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 0.0
    if math.isnan(parsed) or math.isinf(parsed):
        parsed = 0.0
    return max(low, min(high, parsed))


def number(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def percentish(value: Any) -> float | None:
    parsed = number(value)
    if parsed is None:
        return None
    if -1.5 <= parsed <= 1.5:
        return parsed * 100
    return parsed


def pct_change(latest: float | None, previous: float | None) -> float:
    if latest is None or previous in (None, 0):
        return 0.0
    return (latest / previous - 1) * 100


def latest_ratio(bars: list[dict[str, Any]], key: str, lookback: int = 20) -> float:
    latest = number(bars[-1].get(key), 0.0) or 0.0
    previous = [number(bar.get(key)) for bar in bars[-lookback - 1 : -1]]
    usable = [item for item in previous if item not in (None, 0)]
    if not usable:
        return 1.0
    average = sum(float(item) for item in usable) / len(usable)
    return latest / average if average else 1.0


def max_drawdown(bars: list[dict[str, Any]]) -> float:
    peak: float | None = None
    drawdown = 0.0
    for bar in bars:
        close = number(bar.get("close"))
        if close is None:
            continue
        peak = close if peak is None else max(peak, close)
        if peak:
            drawdown = min(drawdown, (close / peak - 1) * 100)
    return drawdown


def market_keywords(details: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    if details.get("change_1d", 0) >= 3:
        keywords.append("单日强势")
    if details.get("change_1d", 0) <= -3:
        keywords.append("单日走弱")
    if details.get("amount_ratio_20d", 1) >= 2:
        keywords.append("放量")
    if details.get("limit_up_days", 0):
        keywords.append("涨停")
    if details.get("limit_down_days", 0):
        keywords.append("跌停")
    if details.get("max_drawdown", 0) <= -18:
        keywords.append("回撤较大")
    return keywords


def recency_weight(value: str, window_days: int) -> float:
    parsed = parse_date(value)
    if not parsed:
        return 0.55
    days_ago = max(0, (date.today() - parsed).days)
    return max(0.35, 1.0 - days_ago / max(1, window_days * 1.3))


def parse_date(value: str) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def latest_as_of(rows: list[sqlite3.Row]) -> str:
    dates = [str(row["event_date"] or "")[:10] for row in rows if parse_date(str(row["event_date"] or ""))]
    return max(dates) if dates else ""


def safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()][:20]


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "********"
    return f"{value[:3]}...{value[-4:]}"
