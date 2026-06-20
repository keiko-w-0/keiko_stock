#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.iwencai_recall import search_iwencai_recall, sync_iwencai_recall_index


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Daily sync for the iWenCai keyword + BGE/Qdrant recall index."
    )
    parser.add_argument("--force", action="store_true", help="Rebuild even when no new iWenCai profile symbols exist.")
    parser.add_argument("--dry-run", action="store_true", help="Only check whether a rebuild is needed.")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding/upload batch size.")
    parser.add_argument("--no-cleanup", action="store_true", help="Keep old Qdrant collections after a successful rebuild.")
    parser.add_argument("--query", default="", help="Optional query to run after sync, useful for smoke tests.")
    parser.add_argument("--limit", type=int, default=10, help="Search limit when --query is used.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    try:
        result = sync_iwencai_recall_index(
            force=args.force,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            cleanup_old_collections=not args.no_cleanup,
        )
        if args.query.strip() and not args.dry_run:
            result["smoke_search"] = search_iwencai_recall(args.query, limit=args.limit)
    except Exception as exc:  # noqa: BLE001 - CLI should print actionable failure.
        result = {
            "mode": "iwencai-recall-daily-sync",
            "status": "failed",
            "error": str(exc),
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"status={result.get('status')} reason={result.get('reason', '')} "
            f"symbols={result.get('source', {}).get('symbol_count', 0)} "
            f"documents={result.get('source', {}).get('document_count', result.get('document_count', 0))} "
            f"collection={result.get('qdrant_collection', '')}"
        )
        if result.get("smoke_search"):
            search = result["smoke_search"]
            print(f"search_count={search.get('count', 0)} query={args.query}")
            for item in (search.get("results") or [])[: args.limit]:
                print(
                    f"{item.get('symbol')} {item.get('name')} "
                    f"score={item.get('score')} terms={','.join(item.get('matched_terms') or [])}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
