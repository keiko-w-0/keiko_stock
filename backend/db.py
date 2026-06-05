from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from . import seed_data
from .providers import MockProviderSet


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

            create table if not exists market_snapshots (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              provider text not null,
              as_of text not null,
              fetched_at text not null,
              price real not null,
              volume real not null,
              amount real not null,
              turnover_rate real not null,
              spread_bps real not null,
              raw_json text not null,
              freshness_status text not null
            );

            create table if not exists financial_snapshots (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              period text not null,
              provider text not null,
              revenue_growth real not null,
              roe real not null,
              fcf_margin real not null,
              debt_ratio real not null,
              pe real not null,
              pb real not null,
              raw_json text not null
            );

            create table if not exists news_items (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              source text not null,
              source_tier text not null,
              title text not null,
              url text not null,
              published_at text not null,
              summary text not null,
              sentiment_score real not null,
              raw_text_hash text not null
            );

            create table if not exists claims (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              claim_text text not null,
              claim_type text not null,
              source_tier text not null,
              source text not null,
              source_url text not null,
              confidence real not null,
              truth_status text not null,
              raw_json text not null,
              created_at text not null
            );

            create table if not exists factor_runs (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              as_of text not null,
              factor_name text not null,
              score real not null,
              inputs_json text not null,
              method_version text not null,
              provider_set_hash text not null
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

            create table if not exists data_source_configs (
              id text primary key,
              market text not null,
              label text not null,
              provider text not null,
              source_kind text not null,
              requires_key integer not null,
              credential_label text not null,
              enabled integer not null,
              configured integer not null,
              credential_hint text not null default '',
              last_configured_at text,
              updated_at text not null
            );

            create table if not exists data_source_account_settings (
              account_id text not null references accounts(id),
              source_id text not null references data_source_configs(id),
              enabled integer not null,
              updated_at text not null,
              primary key (account_id, source_id)
            );

            create table if not exists data_source_credentials (
              account_id text not null references accounts(id),
              source_id text not null references data_source_configs(id),
              credential_value text not null,
              credential_hint text not null,
              updated_at text not null,
              primary key (account_id, source_id)
            );

            create table if not exists search_history (
              id integer primary key autoincrement,
              account_id text not null references accounts(id),
              surface text not null,
              query text not null,
              normalized_query text not null,
              metadata_json text not null default '{}',
              created_at text not null
            );

            create index if not exists idx_search_history_account_surface_created
            on search_history(account_id, surface, created_at desc);
            """
        )
        seed_if_empty(conn)
        sync_seed_symbols(conn)
        sync_seed_analysis_runs(conn)
        sync_seed_memories(conn)
        seed_admin_account(conn)
        migrate_account_scoped_data_sources(conn)
        seed_shared_snapshots_if_empty(conn)
        seed_data_sources(conn)


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


def sync_seed_symbols(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        insert into symbols (symbol, market, name, currency, exchange, sector, industry)
        values (:symbol, :market, :name, :currency, :exchange, :sector, :industry)
        on conflict(symbol) do update set
          market = excluded.market,
          name = excluded.name,
          currency = excluded.currency,
          exchange = excluded.exchange,
          sector = excluded.sector,
          industry = excluded.industry
        """,
        seed_data.SYMBOLS,
    )


def sync_seed_analysis_runs(conn: sqlite3.Connection) -> None:
    created_at = now_iso()
    for item in seed_data.ANALYSIS_RUNS:
        conn.execute(
            """
            insert into stock_analysis_runs (
              symbol, as_of, analysis_version, input_snapshot_hash, conclusion, action,
              confidence, reflection_json, created_at
            )
            select ?, ?, ?, ?, ?, ?, ?, ?, ?
            where not exists (
              select 1 from stock_analysis_runs
              where symbol = ? and input_snapshot_hash = ?
            )
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
                item["symbol"],
                item["input_snapshot_hash"],
            ),
        )


def sync_seed_memories(conn: sqlite3.Connection) -> None:
    created_at = now_iso()
    for item in seed_data.MEMORIES:
        conn.execute(
            """
            insert into stock_memories (
              symbol, memory_version, reusable_json, must_refresh_json, invalidated_by, source_run_id, created_at
            )
            select ?, ?, ?, ?, ?, null, ?
            where not exists (
              select 1 from stock_memories
              where symbol = ? and memory_version = ?
            )
            """,
            (
                item["symbol"],
                item["memory_version"],
                json.dumps(item["reusable_json"], ensure_ascii=False),
                json.dumps(item["must_refresh_json"], ensure_ascii=False),
                json.dumps(item["invalidated_by"], ensure_ascii=False),
                created_at,
                item["symbol"],
                item["memory_version"],
            ),
        )


def seed_admin_account(conn: sqlite3.Connection) -> None:
    created_at = now_iso()
    conn.execute(
        """
        insert into users (id, email, display_name, created_at)
        values (?, ?, ?, ?)
        on conflict(id) do update set
          email = excluded.email,
          display_name = excluded.display_name
        """,
        ("user-admin", "admin@example.local", "Admin", created_at),
    )
    conn.execute(
        """
        insert into accounts (id, user_id, name, base_currency, created_at)
        values (?, ?, ?, ?, ?)
        on conflict(id) do update set
          name = excluded.name,
          base_currency = excluded.base_currency
        """,
        ("acct-admin", "user-admin", "Admin 管理账户", "CNY", created_at),
    )
    conn.executemany(
        """
        insert into account_favorites (account_id, symbol, created_at, note)
        values ('acct-admin', ?, ?, ?)
        on conflict(account_id, symbol) do nothing
        """,
        [
            ("NVDA", created_at, "Finnhub 美股观察"),
            ("AAPL", created_at, "Finnhub 美股观察"),
        ],
    )


def migrate_account_scoped_data_sources(conn: sqlite3.Connection) -> None:
    credential_columns = [
        row["name"]
        for row in conn.execute("pragma table_info(data_source_credentials)")
    ]
    if "account_id" not in credential_columns:
        conn.execute("alter table data_source_credentials rename to data_source_credentials_legacy")
        conn.execute(
            """
            create table data_source_credentials (
              account_id text not null references accounts(id),
              source_id text not null references data_source_configs(id),
              credential_value text not null,
              credential_hint text not null,
              updated_at text not null,
              primary key (account_id, source_id)
            )
            """
        )
        conn.execute(
            """
            insert or replace into data_source_credentials (
              account_id, source_id, credential_value, credential_hint, updated_at
            )
            select 'acct-admin', source_id, credential_value, credential_hint, updated_at
            from data_source_credentials_legacy
            """
        )
        conn.execute("drop table data_source_credentials_legacy")

    conn.execute(
        """
        create table if not exists data_source_account_settings (
          account_id text not null references accounts(id),
          source_id text not null references data_source_configs(id),
          enabled integer not null,
          updated_at text not null,
          primary key (account_id, source_id)
        )
        """
    )


def seed_shared_snapshots_if_empty(conn: sqlite3.Connection) -> None:
    exists = conn.execute("select count(*) as count from market_snapshots").fetchone()["count"]
    if exists:
        return

    provider_set = MockProviderSet()
    fetched_at = now_iso()
    conn.executemany(
        """
        insert into market_snapshots (
          symbol, provider, as_of, fetched_at, price, volume, amount, turnover_rate,
          spread_bps, raw_json, freshness_status
        )
        values (
          :symbol, :provider, :as_of, :fetched_at, :price, :volume, :amount, :turnover_rate,
          :spread_bps, :raw_json, :freshness_status
        )
        """,
        [
            {**item, "raw_json": json.dumps(item["raw_json"], ensure_ascii=False)}
            for item in provider_set.market.snapshots(fetched_at)
        ],
    )
    conn.executemany(
        """
        insert into financial_snapshots (
          symbol, period, provider, revenue_growth, roe, fcf_margin, debt_ratio, pe, pb, raw_json
        )
        values (
          :symbol, :period, :provider, :revenue_growth, :roe, :fcf_margin, :debt_ratio, :pe, :pb, :raw_json
        )
        """,
        [
            {**item, "raw_json": json.dumps(item["raw_json"], ensure_ascii=False)}
            for item in provider_set.financial.snapshots()
        ],
    )
    conn.executemany(
        """
        insert into news_items (
          symbol, source, source_tier, title, url, published_at, summary, sentiment_score, raw_text_hash
        )
        values (
          :symbol, :source, :source_tier, :title, :url, :published_at, :summary, :sentiment_score, :raw_text_hash
        )
        """,
        provider_set.news.news_items(),
    )
    conn.executemany(
        """
        insert into claims (
          symbol, claim_text, claim_type, source_tier, source, source_url,
          confidence, truth_status, raw_json, created_at
        )
        values (
          :symbol, :claim_text, :claim_type, :source_tier, :source, :source_url,
          :confidence, :truth_status, :raw_json, :created_at
        )
        """,
        [
            {**item, "raw_json": json.dumps(item["raw_json"], ensure_ascii=False), "created_at": fetched_at}
            for item in provider_set.news.claims()
        ],
    )
    conn.executemany(
        """
        insert into factor_runs (
          symbol, as_of, factor_name, score, inputs_json, method_version, provider_set_hash
        )
        values (
          :symbol, :as_of, :factor_name, :score, :inputs_json, :method_version, :provider_set_hash
        )
        """,
        [
            {**item, "inputs_json": json.dumps(item["inputs_json"], ensure_ascii=False)}
            for item in provider_set.factor_runs("2026-06-05T15:00:00+08:00")
        ],
    )


def seed_data_sources(conn: sqlite3.Connection) -> None:
    updated_at = now_iso()
    for item in seed_data.DATA_SOURCE_CONFIGS:
        conn.execute(
            """
            insert into data_source_configs (
              id, market, label, provider, source_kind, requires_key, credential_label,
              enabled, configured, credential_hint, last_configured_at, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?)
            on conflict(id) do update set
              market = excluded.market,
              label = excluded.label,
              provider = excluded.provider,
              source_kind = excluded.source_kind,
              requires_key = excluded.requires_key,
              credential_label = excluded.credential_label,
              enabled = excluded.enabled,
              updated_at = excluded.updated_at
            """,
            (
                item["id"],
                item["market"],
                item["label"],
                item["provider"],
                item["source_kind"],
                int(item["requires_key"]),
                item["credential_label"],
                int(item["enabled"]),
                int(item["configured"]),
                updated_at if item["configured"] else None,
                updated_at,
            ),
        )
