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
from backend.history import dedupe_warehouse, scan_warehouse_duplicates, warehouse_summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove duplicate warehouse rows (filings by title, market_snapshots, shadowed daily_bars)."
    )
    parser.add_argument("symbols", nargs="*", help="Optional symbols for filing title dedupe only.")
    parser.add_argument("--scan-only", action="store_true", help="Report duplicate counts without deleting.")
    parser.add_argument("--no-filings", action="store_true", help="Skip filing title dedupe.")
    parser.add_argument("--no-market-snapshots", action="store_true", help="Skip market_snapshots dedupe.")
    parser.add_argument("--no-daily-bars", action="store_true", help="Skip daily_bars unadjust cleanup.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    init_db()
    with get_db() as conn:
        if args.scan_only:
            payload = {
                "mode": "warehouse-dedupe-scan",
                "duplicates": scan_warehouse_duplicates(conn),
                "warehouse": warehouse_summary(conn),
            }
        else:
            result = dedupe_warehouse(
                conn,
                symbols=list(args.symbols),
                filings=not args.no_filings,
                market_snapshots=not args.no_market_snapshots,
                daily_bars=not args.no_daily_bars,
            )
            conn.commit()
            payload = {
                "mode": "warehouse-dedupe",
                "status": "ok",
                **result,
                "warehouse": warehouse_summary(conn),
            }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.scan_only:
        dup = payload["duplicates"]
        print(
            "warehouse dedupe scan "
            f"daily_bars_pk_dup_groups={dup.get('daily_bars_pk_duplicate_groups', 0)} "
            f"daily_bars_shadowed_unadjust={dup.get('daily_bars_shadowed_unadjust_rows', 0)} "
            f"market_snapshot_dup_groups={dup.get('market_snapshot_duplicate_groups', 0)} "
            f"market_snapshot_extra_rows={dup.get('market_snapshot_extra_rows', 0)} "
            f"filing_title_dup_groups={dup.get('filing_title_duplicate_groups', 0)}"
        )
        return 0

    steps = payload.get("steps") or {}
    filings = steps.get("filings_by_title") or {}
    snapshots = steps.get("market_snapshots") or {}
    bars = steps.get("daily_bars_shadowed_unadjust") or {}
    after = payload.get("after") or {}
    print(
        "warehouse dedupe "
        f"filings_deleted={filings.get('filings_deleted', 0)} "
        f"filing_evidence_deleted={filings.get('sentiment_evidence_deleted', 0)} "
        f"market_snapshots_deleted={snapshots.get('rows_deleted', 0)} "
        f"daily_bars_deleted={bars.get('rows_deleted', 0)} "
        f"remaining_shadowed_unadjust={after.get('daily_bars_shadowed_unadjust_rows', 0)} "
        f"remaining_market_snapshot_extra={after.get('market_snapshot_extra_rows', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
