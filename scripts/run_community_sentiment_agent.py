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
    parser = argparse.ArgumentParser(description="Run the half-hour Eastmoney Guba sentiment agent.")
    parser.add_argument("symbols", nargs="*", help="Optional symbols or names. Empty means recent local candidates.")
    parser.add_argument("--interval-minutes", type=float, default=30.0, help="Loop interval when not using --once.")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit. Useful for launchd StartInterval.")
    parser.add_argument("--community-limit", type=int, default=120, help="Guba posts per symbol per cycle.")
    parser.add_argument("--evidence-limit", type=int, default=120, help="Community evidence rows per symbol to analyze.")
    parser.add_argument("--analysis-days", type=int, default=30, help="Lookback window for sentiment snapshots.")
    parser.add_argument("--retention-days", type=int, default=3, help="Days to keep per-comment raw text and analysis.")
    parser.add_argument("--market-days", type=int, default=20, help="Short K-line refresh window per cycle.")
    parser.add_argument("--no-market-refresh", action="store_true", help="Do not refresh K-line data in the cycle.")
    parser.add_argument("--no-filing-refresh", action="store_true", help="Do not check announcements in the cycle.")
    parser.add_argument("--use-llm", dest="use_llm", action="store_true", default=True, help="Use configured GLM/DeepSeek.")
    parser.add_argument("--no-llm", dest="use_llm", action="store_false", help="Disable LLM and use local fallback.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
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
    sentiment_counts = result.get("sentiment", {}).get("counts", {})
    daily_counts = result.get("daily", {}).get("counts", {})
    cleanup_deleted = result.get("cleanup", {}).get("deleted", {})
    print(
        "community-cycle "
        f"symbols={len(result.get('symbols') or [])} "
        f"posts={sentiment_counts.get('community_posts', 0)} "
        f"community_evidence={sentiment_counts.get('community_evidence', 0)} "
        f"daily_summaries={daily_counts.get('symbols', 0)} "
        f"deleted_posts={cleanup_deleted.get('community_posts', 0)} "
        f"deleted_evidence={cleanup_deleted.get('community_evidence', 0)}",
        flush=True,
    )
    errors = []
    for key in ("live_refresh", "sentiment", "daily"):
        errors.extend((result.get(key) or {}).get("errors") or [])
    for item in errors[-5:]:
        print(json.dumps(item, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
