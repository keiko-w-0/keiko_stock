#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_db, init_db
from backend.sentiment import crawl_community_for_symbols, refresh_sentiment


def main() -> int:
    parser = argparse.ArgumentParser(description="Crawl community discussion posts and optionally refresh sentiment.")
    parser.add_argument("symbols", nargs="+", help="Symbols or names to crawl, for example 600519.SH or 贵州茅台.")
    parser.add_argument("--source", default="eastmoney_guba", help="Community source. Default: eastmoney_guba.")
    parser.add_argument("--limit", type=int, default=40, help="Posts per symbol.")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout seconds.")
    parser.add_argument("--sleep-seconds", type=float, default=0.8, help="Delay after each symbol request.")
    parser.add_argument("--days", type=int, default=30, help="Sentiment lookback window.")
    parser.add_argument("--no-analysis", action="store_true", help="Only crawl posts, do not refresh sentiment snapshots.")
    parser.add_argument("--use-llm", action="store_true", help="Use GLM first, then DeepSeek, when local API keys are configured.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    init_db()
    with get_db() as conn:
        crawl = crawl_community_for_symbols(
            conn,
            list(args.symbols),
            source=args.source,
            limit=args.limit,
            timeout=args.timeout,
            sleep_seconds=args.sleep_seconds,
        )
        sentiment = None
        if not args.no_analysis:
            sentiment = refresh_sentiment(
                conn,
                crawl["symbols"],
                days=args.days,
                use_llm=args.use_llm,
                crawl_community=False,
            )

    payload = {"crawl": crawl, "sentiment": sentiment}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"crawl symbols={crawl['counts']['symbols']} posts={crawl['counts']['posts']} "
            f"errors={len(crawl['errors'])}"
        )
        if sentiment:
            print(json.dumps(sentiment["counts"], ensure_ascii=False))
        for item in crawl["errors"][-5:]:
            print(json.dumps(item, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
