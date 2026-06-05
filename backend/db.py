from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from . import seed_data


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("KEIKO_DATA_DIR", ROOT_DIR / "data")).expanduser()
DB_PATH = DATA_DIR / "keiko_mock.db"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def init_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with get_db() as conn:
        conn.executescript(
            """
            create table if not exists users (
              id text primary key,
              email text not null,
              display_name text not null,
              created_at text not null
            );

            create table if not exists accounts (
              id text primary key,
              user_id text not null references users(id),
              name text not null,
              base_currency text not null,
              created_at text not null
            );

            create table if not exists symbols (
              symbol text primary key,
              market text not null,
              name text not null,
              currency text not null,
              exchange text not null,
              sector text not null,
              industry text not null
            );

            create table if not exists stock_analysis_runs (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              as_of text not null,
              analysis_version text not null,
              input_snapshot_hash text not null,
              conclusion text not null,
              action text not null,
              confidence real not null,
              reflection_json text not null,
              created_at text not null
            );

            create table if not exists anomaly_runs (
              id integer primary key autoincrement,
              scope_type text not null,
              scope_key text not null,
              question text,
              as_of text not null,
              report_json text not null,
              evidence_json text not null,
              created_at text not null
            );

            create table if not exists stock_memories (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              memory_version text not null,
              reusable_json text not null,
              must_refresh_json text not null,
              invalidated_by text not null,
              source_run_id integer,
              created_at text not null
            );

            create table if not exists account_favorites (
              account_id text not null references accounts(id),
              symbol text not null references symbols(symbol),
              created_at text not null,
              note text not null default '',
              primary key (account_id, symbol)
            );

            create table if not exists account_trades (
              id integer primary key autoincrement,
              account_id text not null references accounts(id),
              symbol text not null references symbols(symbol),
              side text not null check (side in ('BUY', 'SELL')),
              trade_date text not null,
              quantity real not null,
              price real not null,
              fee real not null default 0,
              currency text not null,
              broker text not null default 'manual',
              note text not null default '',
              created_at text not null
            );

            create table if not exists account_positions_cache (
              account_id text not null references accounts(id),
              symbol text not null references symbols(symbol),
              quantity real not null,
              avg_cost real not null,
              realized_pnl real not null,
              unrealized_pnl real not null,
              return_rate real not null,
              computed_at text not null,
              primary key (account_id, symbol)
            );
            """
        )
        seed_if_empty(conn)


def seed_if_empty(conn: sqlite3.Connection) -> None:
    exists = conn.execute("select count(*) as count from symbols").fetchone()["count"]
    if exists:
        return

    created_at = now_iso()
    conn.executemany(
        "insert into users (id, email, display_name, created_at) values (:id, :email, :display_name, :created_at)",
        [{**item, "created_at": created_at} for item in seed_data.USERS],
    )
    conn.executemany(
        """
        insert into accounts (id, user_id, name, base_currency, created_at)
        values (:id, :user_id, :name, :base_currency, :created_at)
        """,
        [{**item, "created_at": created_at} for item in seed_data.ACCOUNTS],
    )
    conn.executemany(
        """
        insert into symbols (symbol, market, name, currency, exchange, sector, industry)
        values (:symbol, :market, :name, :currency, :exchange, :sector, :industry)
        """,
        seed_data.SYMBOLS,
    )

    for item in seed_data.ANALYSIS_RUNS:
        conn.execute(
            """
            insert into stock_analysis_runs (
              symbol, as_of, analysis_version, input_snapshot_hash, conclusion, action,
              confidence, reflection_json, created_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["symbol"],
                "2026-06-05T15:00:00+08:00",
                "mock-v1",
                item["input_snapshot_hash"],
                item["conclusion"],
                item["action"],
                item["confidence"],
                json.dumps(
                    [
                        {"round": 1, "gate": "data", "status": "pass"},
                        {"round": 2, "gate": "evidence", "status": "pass"},
                        {"round": 3, "gate": "logic", "status": "needs_review"},
                    ],
                    ensure_ascii=False,
                ),
                created_at,
            ),
        )

    conn.executemany(
        """
        insert into stock_memories (
          symbol, memory_version, reusable_json, must_refresh_json, invalidated_by, source_run_id, created_at
        )
        values (:symbol, :memory_version, :reusable_json, :must_refresh_json, :invalidated_by, null, :created_at)
        """,
        [
            {
                **item,
                "reusable_json": json.dumps(item["reusable_json"], ensure_ascii=False),
                "must_refresh_json": json.dumps(item["must_refresh_json"], ensure_ascii=False),
                "invalidated_by": json.dumps(item["invalidated_by"], ensure_ascii=False),
                "created_at": created_at,
            }
            for item in seed_data.MEMORIES
        ],
    )
    conn.executemany(
        """
        insert into account_favorites (account_id, symbol, created_at, note)
        values (:account_id, :symbol, :created_at, :note)
        """,
        [{**item, "created_at": created_at} for item in seed_data.FAVORITES],
    )
    conn.executemany(
        """
        insert into account_trades (
          id, account_id, symbol, side, trade_date, quantity, price, fee, currency, created_at
        )
        values (:id, :account_id, :symbol, :side, :trade_date, :quantity, :price, :fee, :currency, :created_at)
        """,
        [{**item, "created_at": created_at} for item in seed_data.TRADES],
    )

    conn.execute(
        """
        insert into anomaly_runs (scope_type, scope_key, question, as_of, report_json, evidence_json, created_at)
        values (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "market",
            "demo-universe",
            "为什么今天大盘跳水",
            "2026-06-05T15:00:00+08:00",
            json.dumps({"title": "大盘异动解释", "severity": 78, "mode": "mock"}, ensure_ascii=False),
            json.dumps({"sources": ["mock-market", "mock-news"], "truth_gate": "needs_refresh"}, ensure_ascii=False),
            created_at,
        ),
    )
