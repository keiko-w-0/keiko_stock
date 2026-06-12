from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import HTTPException

from .db import now_iso, row_to_dict
from .schemas import AnomalyInput


def shared_cache_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    return {
        "symbols": scalar_count(conn, "symbols"),
        "market_snapshots": scalar_count(conn, "market_snapshots"),
        "financial_snapshots": scalar_count(conn, "financial_snapshots"),
        "news_items": scalar_count(conn, "news_items"),
        "community_posts": scalar_count(conn, "community_posts"),
        "sentiment_evidence": scalar_count(conn, "sentiment_evidence"),
        "sentiment_snapshots": scalar_count(conn, "sentiment_snapshots"),
        "claims": scalar_count(conn, "claims"),
        "factor_runs": scalar_count(conn, "factor_runs"),
        "stock_analysis_runs": scalar_count(conn, "stock_analysis_runs"),
        "anomaly_runs": scalar_count(conn, "anomaly_runs"),
        "stock_memories": scalar_count(conn, "stock_memories"),
        "visibility": "shared_across_accounts",
    }


def latest_stock_analysis(conn: sqlite3.Connection, symbol: str) -> dict[str, Any]:
    normalized = symbol.upper()
    symbol_row = conn.execute("select * from symbols where symbol = ?", (normalized,)).fetchone()
    if not symbol_row:
        raise HTTPException(status_code=404, detail="symbol not found")

    analysis = conn.execute(
        """
        select * from stock_analysis_runs
        where symbol = ?
        order by created_at desc, id desc
        limit 1
        """,
        (normalized,),
    ).fetchone()
    memory = conn.execute(
        """
        select * from stock_memories
        where symbol = ?
        order by created_at desc, id desc
        limit 1
        """,
        (normalized,),
    ).fetchone()

    return {
        "symbol": row_to_dict(symbol_row),
        "analysis": decode_analysis(analysis) if analysis else None,
        "memory": decode_memory(memory) if memory else None,
        "scope": "shared",
    }


def create_anomaly_run(conn: sqlite3.Connection, payload: AnomalyInput) -> dict[str, Any]:
    report = {
        "title": "异动解释",
        "question": payload.question,
        "summary": "已按系统性风险、板块扩散、资金流和消息真实性拆解。真实版本会替换为实时行情和公告数据。",
        "max_reflection_rounds": 3,
    }
    evidence = {
        "sources": ["market-snapshot", "news-sentiment", "sector-breadth"],
        "freshness_status": "provider-cache",
    }
    created_at = now_iso()
    cursor = conn.execute(
        """
        insert into anomaly_runs (scope_type, scope_key, question, as_of, report_json, evidence_json, created_at)
        values (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.scope_type,
            payload.scope_key,
            payload.question,
            created_at,
            json.dumps(report, ensure_ascii=False),
            json.dumps(evidence, ensure_ascii=False),
            created_at,
        ),
    )
    return {"id": cursor.lastrowid, "scope": "shared", "report": report, "evidence": evidence}


def decode_analysis(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    item["reflection_json"] = json.loads(item["reflection_json"])
    return item


def decode_memory(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    item["reusable_json"] = json.loads(item["reusable_json"])
    item["must_refresh_json"] = json.loads(item["must_refresh_json"])
    item["invalidated_by"] = json.loads(item["invalidated_by"])
    return item


def scalar_count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"select count(*) as count from {table}").fetchone()["count"]
