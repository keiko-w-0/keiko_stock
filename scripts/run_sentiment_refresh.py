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
from backend.sentiment import refresh_sentiment, sentiment_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh filing/news, community, and market sentiment snapshots.")
    parser.add_argument("symbols", nargs="*", help="Optional symbols or names. Empty means recent local candidates.")
    parser.add_argument("--days", type=int, default=30, help="Sentiment lookback window in calendar days.")
    parser.add_argument("--use-llm", dest="use_llm", action="store_true", default=True, help="Use GLM first, then DeepSeek, when local API keys are configured.")
    parser.add_argument("--no-llm", dest="use_llm", action="store_false", help="Disable LLM analysis and use local rules only.")
    parser.add_argument("--crawl-community", action="store_true", help="Crawl community posts before sentiment analysis.")
    parser.add_argument("--community-limit", type=int, default=120, help="Community posts per symbol when crawling.")
    parser.add_argument("--evidence-limit", type=int, default=120, help="Text evidence rows per symbol/type.")
    parser.add_argument("--show-symbol", default="", help="Print one symbol sentiment payload after refresh.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    init_db()
    with get_db() as conn:
        result = refresh_sentiment(
            conn,
            list(args.symbols),
            days=args.days,
            use_llm=args.use_llm,
            crawl_community=args.crawl_community,
            community_limit=args.community_limit,
            evidence_limit=args.evidence_limit,
        )
        detail = sentiment_payload(conn, args.show_symbol, days=args.days) if args.show_symbol else None

    if args.json:
        print(json.dumps({"result": result, "detail": detail}, ensure_ascii=False, indent=2))
    else:
        print(
            f"status=ok symbols={len(result['symbols'])} days={result['days']} "
            f"use_llm={result['use_llm']} llm_configured={result['llm_configured']}"
        )
        print(json.dumps(result["counts"], ensure_ascii=False))
        if result["errors"]:
            print(f"errors={len(result['errors'])}")
            for item in result["errors"][-5:]:
                print(json.dumps(item, ensure_ascii=False))
        if detail:
            print(json.dumps(detail["snapshot"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
