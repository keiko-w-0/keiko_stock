from __future__ import annotations

import json
import sqlite3
from typing import Any

from .db import now_iso, row_to_dict


MAX_ITEMS_PER_SURFACE = 30


def record_search(
    conn: sqlite3.Connection,
    *,
    account_id: str,
    surface: str,
    query: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    clean_query = normalize_query(query)
    clean_surface = normalize_surface(surface)
    if not clean_query or not clean_surface:
        return None

    normalized = clean_query.lower()
    created_at = now_iso()
    conn.execute(
        """
        delete from search_history
        where account_id = ? and surface = ? and normalized_query = ?
        """,
        (account_id, clean_surface, normalized),
    )
    cursor = conn.execute(
        """
        insert into search_history (
          account_id, surface, query, normalized_query, metadata_json, created_at
        )
        values (?, ?, ?, ?, ?, ?)
        """,
        (
            account_id,
            clean_surface,
            clean_query,
            normalized,
            json.dumps(metadata or {}, ensure_ascii=False),
            created_at,
        ),
    )
    conn.execute(
        """
        delete from search_history
        where id in (
          select id
          from search_history
          where account_id = ? and surface = ?
          order by created_at desc, id desc
          limit -1 offset ?
        )
        """,
        (account_id, clean_surface, MAX_ITEMS_PER_SURFACE),
    )
    row = conn.execute("select * from search_history where id = ?", (cursor.lastrowid,)).fetchone()
    return decode_history_row(row) if row else None


def list_search_history(
    conn: sqlite3.Connection,
    *,
    account_id: str,
    surface: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    clean_surface = normalize_surface(surface)
    capped_limit = max(1, min(int(limit), 120))
    if clean_surface:
        rows = conn.execute(
            """
            select *
            from search_history
            where account_id = ? and surface = ?
            order by created_at desc, id desc
            limit ?
            """,
            (account_id, clean_surface, capped_limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            select *
            from search_history
            where account_id = ?
            order by created_at desc, id desc
            limit ?
            """,
            (account_id, capped_limit),
        ).fetchall()
    items = [decode_history_row(row) for row in rows]
    return {
        "mode": "account-search-history",
        "account_id": account_id,
        "surface": clean_surface or "all",
        "count": len(items),
        "items": items,
    }


def decode_history_row(row: sqlite3.Row) -> dict[str, Any]:
    item = row_to_dict(row)
    try:
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    except json.JSONDecodeError:
        item["metadata"] = {}
    return item


def normalize_surface(surface: str) -> str:
    return surface.strip().lower().replace(" ", "_")[:80]


def normalize_query(query: str) -> str:
    return " ".join(str(query).strip().split())[:240]
