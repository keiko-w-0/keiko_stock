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
from backend.history import (
    create_a_share_filings_backfill_job,
    dedupe_filing_history_by_title,
    ingestion_run_payload,
    run_a_share_filings_backfill_job,
    warehouse_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a resumable A-share official filings backfill.")
    parser.add_argument("symbols", nargs="*", help="Optional symbols or names. Empty means all A-share filing candidates.")
    parser.add_argument("--source", default="all", help="all, auto, cninfo, sse, or szse. Default all covers CNINFO plus exchange filings.")
    parser.add_argument("--days", type=int, default=180, help="Lookback calendar days for missing filing checks.")
    parser.add_argument("--batch-size", type=int, default=20, help="Symbols per filing batch.")
    parser.add_argument("--max-batches", type=int, default=0, help="Stop after this many batches. 0 means run until no candidates remain.")
    parser.add_argument("--no-universe-refresh", action="store_true", help="Skip BaoStock query_all_stock before filing backfill.")
    parser.add_argument("--dedupe-only", action="store_true", help="Only remove duplicate filings by symbol/title; do not fetch new documents.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    init_db()
    if args.dedupe_only:
        with get_db() as conn:
            cleanup = dedupe_filing_history_by_title(conn, list(args.symbols))
            conn.commit()
            payload = {
                "mode": "a-share-filings-dedupe",
                "status": "ok",
                "cleanup": cleanup,
                "warehouse": warehouse_summary(conn),
            }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(
                "filing dedupe "
                f"checked_rows={cleanup.get('checked_rows', 0)} "
                f"duplicate_groups={cleanup.get('duplicate_groups', 0)} "
                f"filings_deleted={cleanup.get('filings_deleted', 0)} "
                f"sentiment_evidence_deleted={cleanup.get('sentiment_evidence_deleted', 0)}"
            )
        return 0

    refresh_universe = not args.no_universe_refresh
    with get_db() as conn:
        job = create_a_share_filings_backfill_job(
            conn,
            list(args.symbols),
            refresh_universe=refresh_universe,
            source=args.source,
            days=args.days,
            batch_size=args.batch_size,
        )

    if not job.get("already_running"):
        run_a_share_filings_backfill_job(
            int(job["run_id"]),
            list(args.symbols),
            refresh_universe=refresh_universe,
            source=args.source,
            days=args.days,
            batch_size=args.batch_size,
            max_batches=args.max_batches or None,
        )

    with get_db() as conn:
        payload = ingestion_run_payload(conn, int(job["run_id"]))
        payload["warehouse"] = warehouse_summary(conn)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"run_id={payload['id']} status={payload['status']} provider={payload['provider']} scope={payload['scope']}")
        counts = payload.get("counts", {})
        print(
            "counts "
            f"symbols={counts.get('symbols', 0)} "
            f"filings={counts.get('filings', 0)} "
            f"symbols_refreshed={counts.get('symbols_refreshed', 0)} "
            f"no_data_symbols={counts.get('no_data_symbols', 0)} "
            f"failed_symbols={counts.get('failed_symbols', 0)} "
            f"batches={counts.get('batches', 0)} "
            f"duplicate_filings_deleted={counts.get('duplicate_filings_deleted', 0)} "
            f"remaining_candidates={counts.get('remaining_candidates', 0)} "
            f"last_progress_at={counts.get('last_progress_at', '')}"
        )
        errors = payload.get("errors") or []
        print(f"errors={len(errors)}")
        if errors:
            for item in errors[-5:]:
                print(json.dumps(item, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
