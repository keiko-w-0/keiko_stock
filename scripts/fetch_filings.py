#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.filings import search_filing_documents  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch official CNINFO/SSE/SZSE/HKEXnews filings.")
    parser.add_argument("symbol", help="Examples: 600519.SH, 002594.SZ, 0700.HK")
    parser.add_argument("--source", default="auto", help="auto, all, cninfo, sse, szse, hkexnews")
    parser.add_argument("--start-date", default=None, help="YYYY-MM-DD, default: 90 days ago")
    parser.add_argument("--end-date", default=None, help="YYYY-MM-DD, default: today")
    parser.add_argument("--keyword", default="", help="Filter by title keyword where supported.")
    parser.add_argument("--category", default="", help="annual, semiannual, quarter, periodic, temporary, or source-specific id.")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--json", action="store_true", help="Print full JSON response.")
    args = parser.parse_args()

    payload = search_filing_documents(
        symbol=args.symbol,
        source=args.source,
        start_date=args.start_date,
        end_date=args.end_date,
        keyword=args.keyword,
        category=args.category,
        page=args.page,
        page_size=args.page_size,
        timeout=args.timeout,
    )

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_summary(payload)
    return 0 if not payload.get("errors") else 2


def print_summary(payload: dict[str, Any]) -> None:
    query = payload["query"]
    print(
        f"{query['symbol']} {query['start_date']}~{query['end_date']} "
        f"source={query['source']} count={payload['count']}"
    )
    for item in payload["documents"]:
        published_at = (item.get("published_at") or "")[:19]
        print(f"- [{item['source']}] {published_at} {item.get('title', '')}")
        if item.get("url"):
            print(f"  {item['url']}")

    for error in payload.get("errors", []):
        print(f"[error] {error['source']}: {error['message']}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
