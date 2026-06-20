#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.accounts import favorite_symbols_for_accounts
from backend.data_sources import DEFAULT_ACCOUNT_ID
from backend.db import get_db, init_db
from backend.history import is_index_like_symbol, normalize_symbols
from backend.providers.iwencai_profile import (
    IWENCAI_HEXIN_JS_URL,
    IWENCAI_PROFILE_DB_PATH,
    IwencaiProfileClient,
    extract_iwencai_profile,
    finish_iwencai_run,
    get_iwencai_db,
    init_iwencai_profile_db,
    mark_iwencai_state,
    start_iwencai_run,
    upsert_iwencai_profile,
)


Target = dict[str, str]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crawl iWenCai profile sections into a standalone local SQLite DB."
    )
    parser.add_argument("symbols", nargs="*", help="Optional symbols/names. Empty means tier crawl.")
    parser.add_argument(
        "--tier",
        choices=["all", "favorites", "stocks", "indices"],
        default="all",
        help="Crawl tier. all means favorites -> stocks -> indices.",
    )
    parser.add_argument("--account-id", default=DEFAULT_ACCOUNT_ID, help="Account whose favorites are crawled first.")
    parser.add_argument("--iwencai-db", default=str(IWENCAI_PROFILE_DB_PATH), help="Output SQLite DB path.")
    parser.add_argument("--limit", type=int, default=0, help="Max total targets to crawl after tier ordering.")
    parser.add_argument("--per-tier-limit", type=int, default=0, help="Max targets from each tier before dedupe.")
    parser.add_argument("--sleep", type=float, default=0.8, help="Seconds to sleep between requests.")
    parser.add_argument("--jitter", type=float, default=0.4, help="Random extra sleep seconds between requests.")
    parser.add_argument("--timeout", type=float, default=25, help="HTTP timeout seconds.")
    parser.add_argument("--max-retries", type=int, default=3, help="HTTP retries per target.")
    parser.add_argument(
        "--circuit-403-threshold",
        type=int,
        default=0,
        help="Pause after this many consecutive iWenCai 403 failures. 0 disables the circuit breaker.",
    )
    parser.add_argument(
        "--circuit-cooldown-seconds",
        type=float,
        default=7200,
        help="Seconds to pause after the consecutive-403 circuit breaker trips.",
    )
    parser.add_argument(
        "--circuit-max-cooldowns",
        type=int,
        default=0,
        help="Max circuit-breaker cooldown pauses. 0 means unlimited.",
    )
    parser.add_argument(
        "--stale-hours",
        type=float,
        default=24 * 7,
        help="Skip ok/no_sections rows fetched within this many hours. Use 0 to disable.",
    )
    parser.add_argument("--force", action="store_true", help="Refresh even when a recent row exists.")
    parser.add_argument("--hexin-js", default="", help="Path to cached pywencai hexin-v.bundle.js.")
    parser.add_argument("--hexin-js-url", default=IWENCAI_HEXIN_JS_URL, help="Download URL for hexin-v script.")
    parser.add_argument("--node", default="", help="Node.js executable path.")
    parser.add_argument("--status-every", type=int, default=10, help="Print progress every N processed targets.")
    parser.add_argument(
        "--failed-cooldown-hours",
        type=float,
        default=0,
        help="Skip symbols whose latest failed crawl is a 403 within this many hours. 0 disables.",
    )
    parser.add_argument(
        "--disable-circuit-probe",
        action="store_true",
        help="Disable the last-success probe before a consecutive-403 cooldown.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only print target order; do not request iWenCai.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable final JSON.")
    args = parser.parse_args()

    try:
        init_db()
    except sqlite3.OperationalError as exc:
        if "locked" not in str(exc).lower():
            raise
        if not args.json:
            print("source db is locked during init; continuing with existing schema")
    with get_db() as source_conn:
        targets = build_targets(
            source_conn,
            args.symbols,
            tier=args.tier,
            account_id=args.account_id,
            per_tier_limit=args.per_tier_limit,
        )

    if args.limit > 0:
        targets = targets[: args.limit]

    if args.dry_run:
        payload = {"count": len(targets), "targets": targets}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    iwencai_db_path = Path(args.iwencai_db).expanduser()
    candidate_count = len(targets)
    counts: dict[str, int] = {
        "profiles": 0,
        "highlights": 0,
        "important_events": 0,
        "concepts": 0,
        "ok": 0,
        "no_sections": 0,
        "skipped_recent": 0,
        "skipped_recent_failed": 0,
        "failed": 0,
        "circuit_403_probes": 0,
        "circuit_403_probe_passes": 0,
    }
    errors: list[dict[str, Any]] = []
    processed = 0
    status = "ok"
    consecutive_403 = 0
    cooldown_count = 0
    last_success_question = ""
    last_success_target: Target | None = None

    with get_iwencai_db(iwencai_db_path) as iwencai_conn:
        init_iwencai_profile_db(iwencai_conn)
        if not args.force:
            targets, prefilter_counts = prefilter_iwencai_targets(
                iwencai_conn,
                targets,
                stale_hours=args.stale_hours,
                failed_cooldown_hours=args.failed_cooldown_hours,
            )
            for key, value in prefilter_counts.items():
                counts[key] = counts.get(key, 0) + value
            processed = counts.get("skipped_recent", 0) + counts.get("skipped_recent_failed", 0)
            print_prefilter_summary(args, candidate_count, len(targets), counts)
        run_id = start_iwencai_run(iwencai_conn, run_scope(args), run_tier_order(args), candidate_count)
        iwencai_conn.commit()

    client = (
        new_iwencai_client(args)
        if targets
        else None
    )

    try:
        with get_iwencai_db(iwencai_db_path) as iwencai_conn:
            init_iwencai_profile_db(iwencai_conn)
            for index, target in enumerate(targets, start=1):
                symbol = target["symbol"]
                question = question_for_target(target)
                try:
                    if client is None:
                        raise RuntimeError("iwencai client is not initialized")
                    payload = client.fetch_robot_data(question)
                    extracted = extract_iwencai_profile(
                        payload,
                        symbol=symbol,
                        name=target["name"],
                        market=target["market"],
                        target_type=target["target_type"],
                        question=question,
                    )
                    upsert_counts = upsert_iwencai_profile(iwencai_conn, extracted)
                    for key, value in upsert_counts.items():
                        counts[key] = counts.get(key, 0) + value
                    extracted_status = str(extracted.get("status") or "ok")
                    counts[extracted_status] = counts.get(extracted_status, 0) + 1
                    iwencai_conn.commit()
                    processed += 1
                    consecutive_403 = 0
                    last_success_question = question
                    last_success_target = target
                    print_progress(args, index, len(targets), target, extracted_status, counts)
                except Exception as exc:  # noqa: BLE001 - per-symbol crawler should continue.
                    error = str(exc)
                    counts["failed"] += 1
                    errors.append({"symbol": symbol, "name": target["name"], "target_type": target["target_type"], "error": error})
                    mark_iwencai_state(
                        iwencai_conn,
                        symbol=symbol,
                        name=target["name"],
                        market=target["market"],
                        target_type=target["target_type"],
                        status="failed",
                        error=error,
                    )
                    iwencai_conn.commit()
                    processed += 1
                    print_progress(args, index, len(targets), target, "failed", counts)
                    if is_iwencai_403(error):
                        consecutive_403 += 1
                    else:
                        consecutive_403 = 0

                    if should_pause_for_403(args, consecutive_403, cooldown_count):
                        should_cooldown = True
                        if client is not None and last_success_question and not args.disable_circuit_probe:
                            counts["circuit_403_probes"] = counts.get("circuit_403_probes", 0) + 1
                            probe_client, probe_ok, probe_error = probe_iwencai_circuit(args, last_success_question)
                            print_circuit_probe(
                                args,
                                consecutive_403,
                                target,
                                last_success_target,
                                probe_ok=probe_ok,
                                probe_error=probe_error,
                            )
                            if probe_ok and probe_client is not None:
                                client = probe_client
                                counts["circuit_403_probe_passes"] = counts.get("circuit_403_probe_passes", 0) + 1
                                consecutive_403 = 0
                                should_cooldown = False
                        if should_cooldown:
                            cooldown_count += 1
                            print_circuit_pause(args, consecutive_403, cooldown_count, target)
                            time.sleep(max(0.0, args.circuit_cooldown_seconds))
                            client = new_iwencai_client(args)
                            consecutive_403 = 0

                if index < len(targets):
                    sleep_seconds = max(0.0, args.sleep) + random.random() * max(0.0, args.jitter)
                    if sleep_seconds:
                        time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        status = "partial"
        errors.append({"scope": "keyboard_interrupt", "error": "interrupted by user"})
    finally:
        with get_iwencai_db(iwencai_db_path) as iwencai_conn:
            finish_iwencai_run(
                iwencai_conn,
                run_id,
                final_status(status, counts),
                updated_count=counts.get("profiles", 0),
                skipped_count=counts.get("skipped_recent", 0) + counts.get("skipped_recent_failed", 0),
                failed_count=counts.get("failed", 0),
                counts={
                    **counts,
                    "processed": processed,
                    "requested": candidate_count,
                    "active_requested": len(targets),
                    "circuit_403_cooldowns": cooldown_count,
                },
                errors=errors,
            )
            iwencai_conn.commit()

    result = {
        "run_id": run_id,
        "status": final_status(status, counts),
        "db": str(iwencai_db_path),
        "requested": candidate_count,
        "active_requested": len(targets),
        "processed": processed,
        "counts": counts,
        "errors": errors[-10:],
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"run_id={run_id} status={result['status']} db={iwencai_db_path} "
            f"requested={candidate_count} active={len(targets)} processed={processed} "
            f"ok={counts.get('ok', 0)} no_sections={counts.get('no_sections', 0)} "
            f"skipped={counts.get('skipped_recent', 0)} "
            f"skipped_failed={counts.get('skipped_recent_failed', 0)} failed={counts.get('failed', 0)} "
            f"events={counts.get('important_events', 0)} concepts={counts.get('concepts', 0)}"
        )
        if errors:
            print("last_errors:")
            for item in errors[-5:]:
                print(json.dumps(item, ensure_ascii=False))
    return 130 if status == "partial" else 0


def build_targets(
    conn: sqlite3.Connection,
    symbols: list[str],
    *,
    tier: str,
    account_id: str,
    per_tier_limit: int,
) -> list[Target]:
    if symbols:
        normalized = normalize_symbols(conn, symbols)
        return rows_for_symbols(conn, normalized, "custom")

    clean_tier = tier.lower()
    tiers = ["favorites", "stocks", "indices"] if clean_tier == "all" else [clean_tier]
    seen: set[str] = set()
    targets: list[Target] = []
    for item in tiers:
        rows = tier_targets(conn, item, account_id)
        if per_tier_limit > 0:
            rows = rows[:per_tier_limit]
        for row in rows:
            symbol = row["symbol"]
            if symbol in seen:
                continue
            seen.add(symbol)
            targets.append(row)
    return targets


def tier_targets(conn: sqlite3.Connection, tier: str, account_id: str) -> list[Target]:
    favorites = set(favorite_symbols_for_accounts(conn, account_id))
    if tier == "favorites":
        symbols = favorite_symbols_for_accounts(conn, account_id)
        return rows_for_symbols(conn, symbols, "favorite")

    universe = [
        str(row["symbol"]).upper()
        for row in conn.execute(
            """
            select symbol
            from symbols
            where market = 'A'
              and (symbol like '%.SH' or symbol like '%.SZ')
            order by symbol
            """
        )
    ]
    if tier == "stocks":
        symbols = [
            symbol
            for symbol in universe
            if symbol not in favorites and not is_index_like_symbol(conn, symbol)
        ]
        return rows_for_symbols(conn, symbols, "stock")
    if tier == "indices":
        symbols = [symbol for symbol in universe if symbol not in favorites and is_index_like_symbol(conn, symbol)]
        return rows_for_symbols(conn, symbols, "index")
    raise ValueError(f"unsupported tier: {tier}")


def rows_for_symbols(conn: sqlite3.Connection, symbols: list[str], target_type: str) -> list[Target]:
    if not symbols:
        return []
    rows: list[Target] = []
    for symbol in symbols:
        row = conn.execute(
            """
            select symbol, name, market
            from symbols
            where symbol = ?
            """,
            (symbol,),
        ).fetchone()
        if not row:
            continue
        rows.append(
            {
                "symbol": str(row["symbol"]).upper(),
                "name": str(row["name"] or ""),
                "market": str(row["market"] or ""),
                "target_type": target_type,
            }
        )
    return rows


def prefilter_iwencai_targets(
    conn: sqlite3.Connection,
    targets: list[Target],
    *,
    stale_hours: float,
    failed_cooldown_hours: float,
) -> tuple[list[Target], dict[str, int]]:
    counts = {"skipped_recent": 0, "skipped_recent_failed": 0}
    if not targets:
        return [], counts

    symbols = [target["symbol"] for target in targets]
    fresh_symbols = recent_profile_symbols(conn, symbols, stale_hours)
    recent_failed_symbols = recent_403_failed_symbols(conn, symbols, failed_cooldown_hours)
    active: list[Target] = []
    for target in targets:
        symbol = target["symbol"]
        if symbol in fresh_symbols:
            counts["skipped_recent"] += 1
        elif symbol in recent_failed_symbols:
            counts["skipped_recent_failed"] += 1
        else:
            active.append(target)
    return active, counts


def recent_profile_symbols(conn: sqlite3.Connection, symbols: list[str], stale_hours: float) -> set[str]:
    if stale_hours <= 0 or not symbols:
        return set()
    rows = query_iwencai_rows_by_symbols(
        conn,
        """
        select symbol, status, fetched_at
        from iwencai_profiles
        where symbol in ({placeholders})
        """,
        symbols,
    )
    return {
        str(row["symbol"])
        for row in rows
        if row["status"] in {"ok", "no_sections"} and iso_time_is_recent(row["fetched_at"], stale_hours)
    }


def recent_403_failed_symbols(conn: sqlite3.Connection, symbols: list[str], cooldown_hours: float) -> set[str]:
    if cooldown_hours <= 0 or not symbols:
        return set()
    rows = query_iwencai_rows_by_symbols(
        conn,
        """
        select symbol, status, last_error, updated_at
        from iwencai_crawl_state
        where symbol in ({placeholders})
          and status = 'failed'
        """,
        symbols,
    )
    return {
        str(row["symbol"])
        for row in rows
        if is_iwencai_403(str(row["last_error"] or "")) and iso_time_is_recent(row["updated_at"], cooldown_hours)
    }


def query_iwencai_rows_by_symbols(
    conn: sqlite3.Connection,
    sql_template: str,
    symbols: list[str],
    *,
    chunk_size: int = 800,
) -> list[sqlite3.Row]:
    rows: list[sqlite3.Row] = []
    for batch in chunked(symbols, chunk_size):
        placeholders = ",".join("?" for _ in batch)
        rows.extend(conn.execute(sql_template.format(placeholders=placeholders), batch).fetchall())
    return rows


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), max(1, size))]


def iso_time_is_recent(value: Any, hours: float) -> bool:
    if hours <= 0 or not value:
        return False
    try:
        observed = datetime.fromisoformat(str(value))
    except ValueError:
        return False
    return (datetime.now() - observed).total_seconds() < hours * 3600


def question_for_target(target: Target) -> str:
    name = str(target.get("name") or "").strip()
    if name:
        return name
    symbol = str(target.get("symbol") or "").strip()
    return symbol.split(".", 1)[0] if "." in symbol else symbol


def new_iwencai_client(args: argparse.Namespace) -> IwencaiProfileClient:
    return IwencaiProfileClient(
        hexin_js_path=args.hexin_js or None,
        hexin_js_url=args.hexin_js_url,
        node_path=args.node or None,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )


def run_scope(args: argparse.Namespace) -> str:
    if args.symbols:
        return "custom"
    return args.tier


def run_tier_order(args: argparse.Namespace) -> list[str]:
    if args.symbols:
        return ["custom"]
    return ["favorites", "stocks", "indices"] if args.tier == "all" else [args.tier]


def final_status(status: str, counts: dict[str, int]) -> str:
    if status == "partial":
        return "partial"
    if counts.get("failed", 0) and not counts.get("ok", 0) and not counts.get("no_sections", 0):
        return "failed"
    if counts.get("failed", 0):
        return "partial"
    return "ok"


def is_iwencai_403(error: str) -> bool:
    text = str(error or "").lower()
    return "403" in text and ("forbidden" in text or "client error" in text)


def should_pause_for_403(args: argparse.Namespace, consecutive_403: int, cooldown_count: int) -> bool:
    threshold = max(0, int(args.circuit_403_threshold or 0))
    if threshold <= 0 or consecutive_403 < threshold:
        return False
    max_cooldowns = max(0, int(args.circuit_max_cooldowns or 0))
    return max_cooldowns == 0 or cooldown_count < max_cooldowns


def probe_iwencai_circuit(args: argparse.Namespace, question: str) -> tuple[IwencaiProfileClient | None, bool, str]:
    try:
        client = new_iwencai_client(args)
        client.fetch_robot_data(question)
        return client, True, ""
    except Exception as exc:  # noqa: BLE001 - probe only decides whether to cool down.
        return None, False, str(exc)


def print_circuit_pause(
    args: argparse.Namespace,
    consecutive_403: int,
    cooldown_count: int,
    target: Target,
) -> None:
    if args.json:
        return
    seconds = max(0.0, float(args.circuit_cooldown_seconds or 0))
    resume_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + seconds))
    print(
        f"[circuit-breaker] consecutive_403={consecutive_403} cooldown_count={cooldown_count} "
        f"last={target['symbol']} {target['name']} pause_seconds={seconds:.0f} resume_at={resume_at}",
        flush=True,
    )


def print_circuit_probe(
    args: argparse.Namespace,
    consecutive_403: int,
    target: Target,
    probe_target: Target | None,
    *,
    probe_ok: bool,
    probe_error: str,
) -> None:
    if args.json:
        return
    probe_symbol = (probe_target or {}).get("symbol", "")
    if probe_ok:
        print(
            f"[circuit-probe] consecutive_403={consecutive_403} last={target['symbol']} {target['name']} "
            f"probe={probe_symbol} ok -> continue_without_cooldown",
            flush=True,
        )
    else:
        print(
            f"[circuit-probe] consecutive_403={consecutive_403} last={target['symbol']} {target['name']} "
            f"probe={probe_symbol} failed={probe_error[:180]}",
            flush=True,
        )


def print_prefilter_summary(
    args: argparse.Namespace,
    candidate_count: int,
    active_count: int,
    counts: dict[str, int],
) -> None:
    if args.json:
        return
    skipped_recent = counts.get("skipped_recent", 0)
    skipped_failed = counts.get("skipped_recent_failed", 0)
    if not skipped_recent and not skipped_failed:
        return
    print(
        f"[prefilter] candidates={candidate_count} active={active_count} "
        f"skipped_recent={skipped_recent} skipped_recent_403_failed={skipped_failed}",
        flush=True,
    )


def print_progress(
    args: argparse.Namespace,
    index: int,
    total: int,
    target: Target,
    status: str,
    counts: dict[str, int],
) -> None:
    if args.json:
        return
    every = max(1, args.status_every)
    if index != 1 and index != total and index % every != 0 and status not in {"failed", "no_sections"}:
        return
    print(
        f"[{index}/{total}] {target['target_type']} {target['symbol']} {target['name']} "
        f"status={status} ok={counts.get('ok', 0)} no_sections={counts.get('no_sections', 0)} "
        f"failed={counts.get('failed', 0)} skipped={counts.get('skipped_recent', 0)}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
