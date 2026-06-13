#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import DB_PATH, row_to_dict  # noqa: E402
from backend.sentiment import (  # noqa: E402
    SENTIMENT_METHOD_VERSION,
    clamp_float,
    cutoff_date,
    failed_text_llm_evidence,
    parse_json,
    recency_weight,
    weighted_score,
)


BASE_TYPE_WEIGHTS = {
    "filing_news": 0.40,
    "community": 0.25,
    "market": 0.35,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only sentiment evidence debugger. Shows raw source rows, parsed LLM results, and score math."
    )
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite database path. Defaults to backend DB_PATH.")
    parser.add_argument("--source-table", default="community_posts", help="Evidence source table. Default: community_posts.")
    parser.add_argument("--source-id", help="Evidence source_id, e.g. 771 for community_posts.id = 771.")
    parser.add_argument("--symbol", help="Symbol to recompute, e.g. 688114.SH. Inferred from --source-id when omitted.")
    parser.add_argument("--sentiment-type", help="Evidence type to list, e.g. community. Inferred from --source-id.")
    parser.add_argument("--method-version", default=SENTIMENT_METHOD_VERSION, help="Sentiment method version to recompute.")
    parser.add_argument("--days", type=int, default=30, help="Snapshot window days. Default: 30.")
    parser.add_argument("--limit", type=int, default=20, help="Evidence rows to print for the selected type.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    conn = sqlite3.connect(Path(args.db).expanduser())
    conn.row_factory = sqlite3.Row
    try:
        payload = build_debug_payload(
            conn,
            source_table=args.source_table,
            source_id=args.source_id,
            symbol=args.symbol,
            sentiment_type=args.sentiment_type,
            method_version=args.method_version,
            days=args.days,
            limit=args.limit,
        )
    finally:
        conn.close()

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print_human(payload)


def build_debug_payload(
    conn: sqlite3.Connection,
    *,
    source_table: str,
    source_id: str | None,
    symbol: str | None,
    sentiment_type: str | None,
    method_version: str,
    days: int,
    limit: int,
) -> dict[str, Any]:
    source = source_row(conn, source_table, source_id) if source_id else None
    evidence_versions = evidence_rows(conn, source_table, source_id) if source_id else []
    selected = selected_evidence(evidence_versions, method_version)
    selected_item = row_to_debug_item(selected) if selected else None

    resolved_symbol = (symbol or (selected_item or {}).get("symbol") or (source or {}).get("symbol") or "").upper()
    resolved_type = sentiment_type or (selected_item or {}).get("sentiment_type") or "community"
    if not resolved_symbol:
        raise SystemExit("Provide --symbol or --source-id so the script can recompute a snapshot.")

    snapshot = snapshot_breakdown(conn, resolved_symbol, method_version=method_version, days=days, limit=limit)
    selected_calc = None
    if selected_item:
        selected_calc = evidence_calculation(selected_item, days)

    return {
        "db": str(conn.execute("pragma database_list").fetchone()["file"]),
        "method_version": method_version,
        "current_backend_method_version": SENTIMENT_METHOD_VERSION,
        "days": days,
        "source_table": source_table,
        "source_id": source_id,
        "source_row": source,
        "evidence_versions": [decode_evidence(row) for row in evidence_versions],
        "selected_evidence": selected_item,
        "selected_evidence_calculation": selected_calc,
        "symbol": resolved_symbol,
        "sentiment_type": resolved_type,
        "snapshot_breakdown": snapshot,
        "type_evidence_rows": snapshot["rows_by_type"].get(resolved_type, [])[: max(0, limit)],
        "note": (
            "The database stores the parsed LLM result, not the full raw HTTP response body. "
            "For GLM rows, evidence_json.llm_id links the parsed result back to the prompt item id."
        ),
    }


def source_row(conn: sqlite3.Connection, source_table: str, source_id: str | None) -> dict[str, Any] | None:
    if not source_id:
        return None
    table = checked_table_name(conn, source_table)
    columns = [row["name"] for row in conn.execute(f"pragma table_info({quote_identifier(table)})")]
    if "id" not in columns:
        return None
    row = conn.execute(f"select * from {quote_identifier(table)} where id = ?", (source_id,)).fetchone()
    if not row:
        return None
    item = row_to_dict(row)
    for key in ("metrics_json", "raw_json"):
        if key in item:
            item[key.replace("_json", "")] = parse_json(item.get(key), {})
    return item


def evidence_rows(conn: sqlite3.Connection, source_table: str, source_id: str | None) -> list[sqlite3.Row]:
    if not source_id:
        return []
    return conn.execute(
        """
        select *
        from sentiment_evidence
        where source_table = ?
          and source_id = ?
        order by analyzed_at, id
        """,
        (source_table, str(source_id)),
    ).fetchall()


def selected_evidence(rows: list[sqlite3.Row], method_version: str) -> sqlite3.Row | None:
    for row in rows:
        if row["method_version"] == method_version:
            return row
    return rows[-1] if rows else None


def snapshot_breakdown(
    conn: sqlite3.Connection,
    symbol: str,
    *,
    method_version: str,
    days: int,
    limit: int,
) -> dict[str, Any]:
    cutoff = cutoff_date(days)
    rows = conn.execute(
        """
        select *
        from sentiment_evidence
        where symbol = ?
          and method_version = ?
          and lower(source) not like '%mock%'
          and coalesce(nullif(substr(event_date, 1, 10), ''), substr(analyzed_at, 1, 10)) >= ?
        order by coalesce(nullif(event_date, ''), analyzed_at) desc, id desc
        """,
        (symbol, method_version, cutoff),
    ).fetchall()

    grouped: dict[str, list[dict[str, Any]]] = {"filing_news": [], "community": [], "market": []}
    failed_counts: dict[str, int] = {"filing_news": 0, "community": 0, "market": 0}
    rows_by_type: dict[str, list[dict[str, Any]]] = {"filing_news": [], "community": [], "market": []}

    for row in rows:
        item = row_to_debug_item(row)
        item_type = str(item.get("sentiment_type") or "")
        if failed_text_llm_evidence(item):
            failed_counts[item_type] = failed_counts.get(item_type, 0) + 1
            continue
        calc = evidence_calculation(item, days)
        item.update(calc)
        grouped.setdefault(item_type, []).append(item)
        rows_by_type.setdefault(item_type, []).append(item)

    type_scores = {key: weighted_score(items, days) for key, items in grouped.items() if items}
    type_totals = {key: type_total(items) for key, items in grouped.items() if items}
    available_weights = {
        key: BASE_TYPE_WEIGHTS[key] if key in type_scores else 0.0
        for key in BASE_TYPE_WEIGHTS
    }
    weight_sum = sum(available_weights.values()) or 1.0
    effective_weights = {
        key: available_weights[key] / weight_sum
        for key in BASE_TYPE_WEIGHTS
        if available_weights[key] > 0
    }
    composite = sum(type_scores[key]["score"] * available_weights.get(key, 0.0) for key in type_scores) / weight_sum
    confidence = sum(type_scores[key]["confidence"] * available_weights.get(key, 0.0) for key in type_scores) / weight_sum

    return {
        "symbol": symbol,
        "method_version": method_version,
        "cutoff": cutoff,
        "input_rows": len(rows),
        "source_counts": {key: len(value) for key, value in grouped.items()},
        "failed_counts": {key: value for key, value in failed_counts.items() if value},
        "type_scores": type_scores,
        "type_totals": type_totals,
        "base_weights": BASE_TYPE_WEIGHTS,
        "effective_weights": effective_weights,
        "composite_score": composite,
        "confidence": clamp_float(confidence, 0.0, 1.0),
        "rows_by_type": {
            key: sorted(value, key=lambda item: (str(item.get("event_date") or ""), int(item.get("id") or 0)), reverse=True)[
                : max(0, limit)
            ]
            for key, value in rows_by_type.items()
        },
    }


def row_to_debug_item(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    item["keywords"] = parse_json(item.pop("keywords_json", "[]"), [])
    item["evidence"] = parse_json(item.pop("evidence_json", "{}"), {})
    return item


def decode_evidence(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return row_to_debug_item(row) if row else None


def evidence_calculation(item: dict[str, Any], days: int) -> dict[str, float]:
    score = float(item.get("sentiment_score") or 0.0)
    confidence = clamp_float(item.get("confidence"), 0.0, 1.0)
    recency = recency_weight(str(item.get("event_date") or item.get("analyzed_at") or ""), days)
    evidence_weight = max(0.1, confidence) * recency
    return {
        "recency_weight": recency,
        "evidence_weight": evidence_weight,
        "weighted_contribution": score * evidence_weight,
    }


def type_total(items: list[dict[str, Any]]) -> dict[str, float]:
    weighted_total = sum(float(item.get("weighted_contribution") or 0.0) for item in items)
    weight_total = sum(float(item.get("evidence_weight") or 0.0) for item in items)
    return {
        "weighted_total": weighted_total,
        "weight_total": weight_total,
        "score": weighted_total / weight_total if weight_total else 0.0,
    }


def checked_table_name(conn: sqlite3.Connection, value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value or ""):
        raise SystemExit(f"Unsafe table name: {value!r}")
    row = conn.execute("select name from sqlite_master where type = 'table' and name = ?", (value,)).fetchone()
    if not row:
        raise SystemExit(f"Unknown table: {value}")
    return value


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def print_human(payload: dict[str, Any]) -> None:
    print(f"DB: {payload['db']}")
    print(f"method_version: {payload['method_version']}")
    print(f"symbol: {payload['symbol']}  days: {payload['days']}  type: {payload['sentiment_type']}")
    print()

    if payload.get("source_row"):
        print("SOURCE ROW")
        print(json.dumps(payload["source_row"], ensure_ascii=False, indent=2, default=str))
        print()

    if payload.get("evidence_versions"):
        print("EVIDENCE VERSIONS")
        for item in payload["evidence_versions"]:
            print(
                "  "
                f"id={item['id']} method={item['method_version']} "
                f"model={item['model_provider']}/{item['model_name']} "
                f"score={float(item['sentiment_score']):.4g} confidence={float(item['confidence']):.4g} "
                f"keywords={item.get('keywords')}"
            )
            if item.get("evidence"):
                print(f"    evidence={json.dumps(item['evidence'], ensure_ascii=False, default=str)}")
        print()

    selected = payload.get("selected_evidence")
    selected_calc = payload.get("selected_evidence_calculation")
    if selected and selected_calc:
        print("SELECTED ITEM MATH")
        print(
            f"  score={float(selected['sentiment_score']):.4g} "
            f"confidence={float(selected['confidence']):.4g} "
            f"recency={selected_calc['recency_weight']:.4g} "
            f"evidence_weight=max(0.1, confidence)*recency={selected_calc['evidence_weight']:.4g}"
        )
        print(f"  weighted_contribution=score*evidence_weight={selected_calc['weighted_contribution']:.4g}")
        print()

    snapshot = payload["snapshot_breakdown"]
    print("SNAPSHOT MATH")
    print(f"  input_rows={snapshot['input_rows']} cutoff={snapshot['cutoff']}")
    print(f"  source_counts={snapshot['source_counts']} failed_counts={snapshot['failed_counts']}")
    print(f"  base_weights={snapshot['base_weights']}")
    print(f"  effective_weights={snapshot['effective_weights']}")
    for key, stats in snapshot["type_scores"].items():
        totals = snapshot["type_totals"][key]
        print(
            f"  {key}: score={stats['score']:.6g} confidence={stats['confidence']:.6g} "
            f"weighted_total={totals['weighted_total']:.6g} weight_total={totals['weight_total']:.6g}"
        )
    print(f"  composite_score={snapshot['composite_score']:.6g} confidence={snapshot['confidence']:.6g}")
    print()

    rows = payload.get("type_evidence_rows") or []
    if rows:
        print(f"{payload['sentiment_type'].upper()} ROWS")
        for item in rows:
            print(
                "  "
                f"id={item['id']} source_id={item['source_id']} date={item.get('event_date') or item.get('analyzed_at')} "
                f"score={float(item['sentiment_score']):.4g} conf={float(item['confidence']):.4g} "
                f"recency={item['recency_weight']:.4g} weight={item['evidence_weight']:.4g} "
                f"contribution={item['weighted_contribution']:.4g} title={item.get('title')!r}"
            )
    print()
    print(f"NOTE: {payload['note']}")


if __name__ == "__main__":
    main()
