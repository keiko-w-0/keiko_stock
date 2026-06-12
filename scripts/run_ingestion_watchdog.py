#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_db, init_db
from backend.history import (
    A_SHARE_FILING_BACKGROUND_STALE_MINUTES,
    A_SHARE_FILING_PROVIDER,
    A_SHARE_FILING_SCRIPT_NAMES,
    BAOSTOCK_BACKGROUND_STALE_MINUTES,
    BAOSTOCK_DAILY_SCRIPT_NAMES,
    BAOSTOCK_FINANCIAL_SCRIPT_NAMES,
    ingestion_heartbeat_is_stale,
    mark_stale_running_ingestions,
    parse_json_value,
)
from backend.job_monitor import running_script_processes, start_detached_python_script, terminate_script_processes


@dataclass(frozen=True)
class WatchJob:
    name: str
    provider: str
    scope_prefix: str
    script: str
    script_names: list[str]
    args: list[str]
    stdout_path: str
    stderr_path: str
    stale_minutes: int
    restart_cooldown_minutes: int
    max_process_age_minutes: int


WATCH_JOBS = (
    WatchJob(
        name="baostock-daily",
        provider="baostock",
        scope_prefix="a-share-history-background",
        script="scripts/run_baostock_backfill.py",
        script_names=BAOSTOCK_DAILY_SCRIPT_NAMES,
        args=["--days", "260", "--batch-size", "30", "--max-batches", "8", "--no-universe-refresh", "--json"],
        stdout_path=str(ROOT_DIR / "logs" / "baostock-nightly.log"),
        stderr_path=str(ROOT_DIR / "logs" / "baostock-nightly.err.log"),
        stale_minutes=BAOSTOCK_BACKGROUND_STALE_MINUTES,
        restart_cooldown_minutes=10,
        max_process_age_minutes=240,
    ),
    WatchJob(
        name="baostock-financial",
        provider="baostock",
        scope_prefix="a-share-quarterly-financials-background",
        script="scripts/run_baostock_financial_backfill.py",
        script_names=BAOSTOCK_FINANCIAL_SCRIPT_NAMES,
        args=["--quarters", "4", "--batch-size", "3", "--max-batches", "4", "--no-universe-refresh", "--json"],
        stdout_path=str(ROOT_DIR / "logs" / "baostock-financial-nightly.log"),
        stderr_path=str(ROOT_DIR / "logs" / "baostock-financial-nightly.err.log"),
        stale_minutes=BAOSTOCK_BACKGROUND_STALE_MINUTES,
        restart_cooldown_minutes=15,
        max_process_age_minutes=360,
    ),
    WatchJob(
        name="a-share-filings",
        provider=A_SHARE_FILING_PROVIDER,
        scope_prefix="a-share-filings-background",
        script="scripts/run_a_share_filings_backfill.py",
        script_names=A_SHARE_FILING_SCRIPT_NAMES,
        args=["--source", "all", "--days", "180", "--batch-size", "10", "--max-batches", "6", "--no-universe-refresh", "--json"],
        stdout_path=str(ROOT_DIR / "logs" / "a-share-filings-nightly.log"),
        stderr_path=str(ROOT_DIR / "logs" / "a-share-filings-nightly.err.log"),
        stale_minutes=A_SHARE_FILING_BACKGROUND_STALE_MINUTES,
        restart_cooldown_minutes=10,
        max_process_age_minutes=180,
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch local ingestion jobs and resume stale or incomplete runs.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect jobs without killing processes or starting new work.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    init_db()
    payload = {"mode": "ingestion-watchdog", "dry_run": args.dry_run, "checked_at": datetime.now().isoformat(timespec="seconds"), "jobs": []}
    started_this_run = False
    with get_db() as conn:
        for job in WATCH_JOBS:
            item = check_job(conn, job, dry_run=args.dry_run, allow_start=args.dry_run or not started_this_run)
            payload["jobs"].append(item)
            if item["action"] == "start":
                started_this_run = True

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for item in payload["jobs"]:
            print(
                f"{item['name']} action={item['action']} reason={item['reason']} "
                f"running_runs={len(item['running_runs'])} processes={len(item['processes'])}"
            )
    return 0


def check_job(conn: Any, job: WatchJob, *, dry_run: bool = False, allow_start: bool = True) -> dict[str, Any]:
    running_rows = running_ingestions(conn, job)
    processes = running_script_processes(job.script_names)
    stale_run_ids = stale_running_ids(running_rows, job.stale_minutes)
    orphan_old_processes = [
        process
        for process in processes
        if not running_rows and process.age_seconds >= job.max_process_age_minutes * 60
    ]
    killed: list[dict[str, Any]] = []

    if (stale_run_ids or orphan_old_processes) and not dry_run:
        marked = mark_stale_running_ingestions(conn, job.provider, job.scope_prefix, job.stale_minutes)
        stale_run_ids = sorted(set(stale_run_ids) | set(marked))
        killed = terminate_script_processes(job.script_names)
        conn.commit()
        running_rows = running_ingestions(conn, job)
        processes = running_script_processes(job.script_names)

    latest = latest_ingestion(conn, job)
    should_start, reason = should_start_job(latest, running_rows, processes, job)
    action = "start" if should_start else "none"
    started: dict[str, Any] | None = None
    if should_start and not allow_start:
        action = "defer"
        reason = "watchdog-started-another-job-this-run"
        should_start = False
    if should_start and not dry_run:
        started = start_detached_python_script(
            job.script,
            job.args,
            stdout_path=job.stdout_path,
            stderr_path=job.stderr_path,
        )

    return {
        "name": job.name,
        "action": action,
        "reason": reason,
        "stale_run_ids": stale_run_ids,
        "killed_processes": killed,
        "started": started,
        "latest_run": summarize_run(latest) if latest else None,
        "running_runs": [summarize_run(row) for row in running_rows],
        "processes": [process.__dict__ for process in processes],
    }


def running_ingestions(conn: Any, job: WatchJob) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        select *
        from ingestion_runs
        where provider = ?
          and scope like ?
          and status = 'running'
        order by id
        """,
        (job.provider, f"{job.scope_prefix}%"),
    ).fetchall()
    return [dict(row) for row in rows]


def latest_ingestion(conn: Any, job: WatchJob) -> dict[str, Any] | None:
    row = conn.execute(
        """
        select *
        from ingestion_runs
        where provider = ?
          and scope like ?
        order by id desc
        limit 1
        """,
        (job.provider, f"{job.scope_prefix}%"),
    ).fetchone()
    return dict(row) if row else None


def stale_running_ids(rows: list[dict[str, Any]], stale_minutes: int) -> list[int]:
    ids: list[int] = []
    for row in rows:
        counts = parse_json_value(row.get("counts_json"), {})
        heartbeat = str(counts.get("last_progress_at") or row.get("started_at") or "")
        if ingestion_heartbeat_is_stale(heartbeat, stale_minutes):
            ids.append(int(row["id"]))
    return ids


def should_start_job(
    latest: dict[str, Any] | None,
    running_rows: list[dict[str, Any]],
    processes: list[Any],
    job: WatchJob,
) -> tuple[bool, str]:
    if running_rows:
        return False, "db-run-still-running"
    if processes:
        return False, "script-process-still-running"
    if not latest:
        return True, "no-run-history"

    status = str(latest.get("status") or "")
    counts = parse_json_value(latest.get("counts_json"), {})
    remaining = int(counts.get("remaining_candidates") or 0)
    if status == "ok" and remaining <= 0:
        return False, "latest-run-complete"
    if remaining <= 0 and status not in {"failed", "interrupted"}:
        return False, "no-remaining-candidates"
    if not cooldown_elapsed(latest, counts, job.restart_cooldown_minutes):
        return False, "restart-cooldown"
    if status in {"partial", "failed", "interrupted", "running"}:
        return True, f"latest-run-{status}-remaining-{remaining}"
    return False, f"latest-run-status-{status}"


def cooldown_elapsed(row: dict[str, Any], counts: dict[str, Any], minutes: int) -> bool:
    value = str(row.get("finished_at") or counts.get("last_progress_at") or row.get("started_at") or "")
    if not value:
        return True
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return True
    return datetime.now() - parsed >= timedelta(minutes=minutes)


def summarize_run(row: dict[str, Any]) -> dict[str, Any]:
    counts = parse_json_value(row.get("counts_json"), {})
    return {
        "id": row.get("id"),
        "provider": row.get("provider"),
        "scope": row.get("scope"),
        "status": row.get("status"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "remaining_candidates": counts.get("remaining_candidates"),
        "last_progress_at": counts.get("last_progress_at"),
    }


if __name__ == "__main__":
    raise SystemExit(main())
