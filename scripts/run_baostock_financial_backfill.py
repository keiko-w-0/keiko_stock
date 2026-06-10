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
    create_baostock_financial_backfill_job,
    ingestion_run_payload,
    run_baostock_financial_backfill_job,
    warehouse_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a resumable BaoStock quarterly financial/report backfill.")
    parser.add_argument("symbols", nargs="*", help="Optional symbols or names. Empty means all A-share candidates.")
    parser.add_argument("--quarters", type=int, default=12, help="Recent quarters to backfill.")
    parser.add_argument("--batch-size", type=int, default=10, help="Symbols per BaoStock financial batch.")
    parser.add_argument("--max-batches", type=int, default=0, help="Stop after this many batches. 0 means run until complete.")
    parser.add_argument("--no-universe-refresh", action="store_true", help="Skip query_all_stock before backfill.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    init_db()
    refresh_universe = not args.no_universe_refresh
    with get_db() as conn:
        job = create_baostock_financial_backfill_job(
            conn,
            list(args.symbols),
            refresh_universe=refresh_universe,
            quarters=args.quarters,
            batch_size=args.batch_size,
        )

    if not job.get("already_running"):
        run_baostock_financial_backfill_job(
            int(job["run_id"]),
            list(args.symbols),
            refresh_universe=refresh_universe,
            quarters=args.quarters,
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
            f"financial_metrics={counts.get('financial_metrics', 0)} "
            f"company_reports={counts.get('company_reports', 0)} "
            f"batches={counts.get('batches', 0)} "
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
