#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_db, init_db
from backend.history import (
    create_market_rescan_job,
    ingestion_run_payload,
    market_rescan_symbols,
    repair_akshare_bars_from_baostock,
    repair_akshare_volume_units,
    run_market_rescan_job,
    warehouse_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rescan recent market data for all symbols (favorites -> stocks -> indices)."
    )
    parser.add_argument("symbols", nargs="*", help="Optional symbols. Empty means tier/universe rescan.")
    parser.add_argument(
        "--tier",
        choices=["all", "favorites", "stocks", "indices"],
        default="all",
        help="Rescan tier order when symbols are omitted.",
    )
    parser.add_argument("--days", type=int, default=30, help="Lookback calendar days to refresh.")
    parser.add_argument("--batch-size", type=int, default=20, help="Symbols per batch.")
    parser.add_argument("--repair-only", action="store_true", help="Only repair akshare volume units in DB.")
    parser.add_argument("--no-akshare", action="store_true", help="Skip AKShare refresh.")
    parser.add_argument("--no-baostock", action="store_true", help="Skip BaoStock refresh.")
    parser.add_argument("--no-repair", action="store_true", help="Skip akshare volume repair before rescan.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    init_db()
    if args.repair_only:
        with get_db() as conn:
            repaired_units = repair_akshare_volume_units(conn)
            repaired_bars = repair_akshare_bars_from_baostock(conn, since_date=(date.today() - timedelta(days=30)).isoformat())
            conn.commit()
            payload = {
                "repaired_akshare_volume_rows": repaired_units,
                "repaired_akshare_bar_rows": repaired_bars,
                "warehouse": warehouse_summary(conn),
            }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(
                f"repaired_akshare_volume_rows={payload['repaired_akshare_volume_rows']} "
                f"repaired_akshare_bar_rows={payload['repaired_akshare_bar_rows']}"
            )
        return 0

    with get_db() as conn:
        preview = market_rescan_symbols(conn, args.tier) if not args.symbols else args.symbols
        job = create_market_rescan_job(
            conn,
            list(args.symbols),
            tier=args.tier,
            days=args.days,
            batch_size=args.batch_size,
        )

    if job.get("already_running"):
        if args.json:
            print(json.dumps(job, ensure_ascii=False, indent=2))
        else:
            print(f"already_running run_id={job['run_id']}")
        return 0

    if not args.json:
        print(
            f"starting run_id={job['run_id']} tier={args.tier} symbols={len(preview)} "
            f"days={args.days} batch_size={args.batch_size}"
        )

    run_market_rescan_job(
        int(job["run_id"]),
        list(args.symbols),
        tier=args.tier,
        days=args.days,
        batch_size=args.batch_size,
        use_akshare=not args.no_akshare,
        use_baostock=not args.no_baostock,
        repair_volume=not args.no_repair,
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
            f"daily_bars={counts.get('daily_bars', 0)} "
            f"market_snapshots={counts.get('market_snapshots', 0)} "
            f"batches={counts.get('batches', 0)} "
            f"repaired={counts.get('repaired_akshare_volume_rows', 0)} "
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
