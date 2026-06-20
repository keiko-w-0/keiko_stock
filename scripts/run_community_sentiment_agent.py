#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_db, init_db
from backend.sentiment import run_community_sentiment_cycle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the community sentiment agent (Eastmoney Guba + Xueqiu). Watchlist mode refreshes every 30 minutes between 08:00-24:00 Asia/Shanghai."
    )
    parser.add_argument("symbols", nargs="*", help="Optional symbols or names. Empty means account watchlist only.")
    parser.add_argument("--account-id", default="", help="Account whose favorites to refresh when symbols are omitted. Defaults to acct-admin.")
    parser.add_argument(
        "--all-active",
        action="store_true",
        help="When symbols are omitted, fall back to recent activity instead of watchlist-only.",
    )
    parser.add_argument("--interval-minutes", type=float, default=30.0, help="Loop interval when not using --once.")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit. Useful for launchd StartInterval.")
    parser.add_argument(
        "--ignore-schedule",
        action="store_true",
        help="Run watchlist refresh even outside the 08:00-24:00 window.",
    )
    parser.add_argument("--community-limit", type=int, default=120, help="Community posts per symbol per cycle (each source, when source=all).")
    parser.add_argument("--evidence-limit", type=int, default=120, help="Community evidence rows per symbol to analyze.")
    parser.add_argument("--analysis-days", type=int, default=30, help="Lookback window for sentiment snapshots.")
    parser.add_argument("--retention-days", type=int, default=3, help="Days to keep per-comment analysis details; raw community posts are preserved.")
    parser.add_argument("--market-days", type=int, default=20, help="Short K-line refresh window per cycle.")
    parser.add_argument("--no-market-refresh", action="store_true", help="Do not refresh K-line data in the cycle.")
    parser.add_argument("--no-filing-refresh", action="store_true", help="Do not check announcements in the cycle.")
    parser.add_argument("--use-llm", dest="use_llm", action="store_true", default=True, help="Use configured GLM/DeepSeek.")
    parser.add_argument("--no-llm", dest="use_llm", action="store_false", help="Disable LLM and use local fallback.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--cycle-timeout-seconds",
        type=float,
        default=None,
        help="Max seconds for one agent cycle (default: KEIKO_SENTIMENT_CYCLE_TIMEOUT_SECONDS or 1200). Use 0 to disable.",
    )
    args = parser.parse_args()

    init_db()
    while True:
        started = time.monotonic()
        with get_db() as conn:
            result = run_community_sentiment_cycle(
                conn,
                symbols=list(args.symbols),
                use_llm=args.use_llm,
                community_limit=args.community_limit,
                evidence_limit=args.evidence_limit,
                analysis_days=args.analysis_days,
                retention_days=args.retention_days,
                refresh_market=not args.no_market_refresh,
                refresh_filings=not args.no_filing_refresh,
                market_days=args.market_days,
                account_id=args.account_id or None,
                favorites_only=not args.all_active,
                respect_watchlist_schedule=not args.ignore_schedule and not args.symbols,
                cycle_timeout_seconds=args.cycle_timeout_seconds,
            )
        print_result(result, json_output=args.json)
        if args.once:
            return 0
        elapsed = time.monotonic() - started
        sleep_seconds = max(1.0, args.interval_minutes * 60 - elapsed)
        time.sleep(sleep_seconds)


def print_result(result: dict, json_output: bool = False) -> None:
    if json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        return
    usage = result.get("usage") or {}
    totals = usage.get("totals") or {}
    accounting = usage.get("accounting") or {}
    cycle = usage.get("cycle") or {}
    sentiment_counts = result.get("sentiment", {}).get("counts", {})
    if result.get("skipped"):
        print(
            "community-cycle skipped "
            f"source={result.get('symbol_source')} "
            f"account={result.get('account_id')} "
            f"reason={result.get('reason')} "
            f"run_id={result.get('run_id')}",
            flush=True,
        )
        return
    print(
        "community-cycle "
        f"run_id={result.get('run_id')} "
        f"source={result.get('symbol_source')} "
        f"account={result.get('account_id')} "
        f"symbols={cycle.get('symbols', len(result.get('symbols') or []))} "
        f"timed_out={bool(result.get('timed_out') or cycle.get('timed_out'))} "
        f"timeout_s={result.get('cycle_timeout_seconds') or cycle.get('cycle_timeout_seconds') or ''} "
        f"posts={cycle.get('community_posts_crawled', sentiment_counts.get('community_posts', 0))} "
        f"community_evidence={cycle.get('community_evidence', sentiment_counts.get('community_evidence', 0))} "
        f"llm_requests={usage.get('llm_requests', 0)} "
        f"llm_items={usage.get('llm_request_items', 0)} "
        f"cache_hits={usage.get('cache_hits', 0)} "
        f"uncached={totals.get('uncached', 0)} "
        f"daily_conclusion={usage.get('daily_conclusion_requests', 0)} "
        f"accounting_ok={all(bool(v) for v in accounting.values()) if accounting else True}",
        flush=True,
    )
    errors = []
    for key in ("live_refresh", "sentiment", "daily"):
        errors.extend((result.get(key) or {}).get("errors") or [])
    for item in errors[-5:]:
        print(json.dumps(item, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
