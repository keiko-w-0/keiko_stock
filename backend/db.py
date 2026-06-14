from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from . import seed_data
from .pinyin import pinyin_initials
from .providers import MockProviderSet


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("KEIKO_DATA_DIR", ROOT_DIR / "data")).expanduser()
DB_PATH = DATA_DIR / "keiko_mock.db"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma busy_timeout = 30000")
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def upsert_financial_metrics_history(conn: sqlite3.Connection, payload: dict[str, Any]) -> None:
    columns = [
        "symbol",
        "report_period",
        "provider",
        "announce_date",
        "revenue_growth",
        "roe",
        "fcf_margin",
        "debt_ratio",
        "gross_margin",
        "net_margin",
        "net_profit",
        "raw_json",
        "fetched_at",
    ]
    row = {column: payload.get(column) for column in columns}
    row["announce_date"] = row.get("announce_date") or ""
    row["raw_json"] = financial_raw_json_text(row.get("raw_json"))
    row["fetched_at"] = row.get("fetched_at") or now_iso()
    placeholders = ", ".join(f":{column}" for column in columns)
    updates = ", ".join(
        f"{column} = excluded.{column}"
        for column in columns
        if column not in {"symbol", "report_period", "provider"}
    )
    conn.execute(
        f"""
        insert into financial_metrics_history ({", ".join(columns)})
        values ({placeholders})
        on conflict(symbol, report_period, provider) do update set
          {updates}
        """,
        row,
    )


def financial_raw_json_text(value: Any) -> str:
    if isinstance(value, str):
        return value or "{}"
    return json.dumps(value or {}, ensure_ascii=False, default=str)


def init_db() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with get_db() as conn:
        conn.execute("pragma journal_mode = wal")
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

            create table if not exists symbol_aliases (
              alias text not null,
              normalized_alias text not null,
              symbol text not null references symbols(symbol),
              source text not null default 'system',
              updated_at text not null,
              primary key (normalized_alias, symbol)
            );

            create table if not exists daily_bars (
              symbol text not null references symbols(symbol),
              trade_date text not null,
              provider text not null,
              adjust text not null default '',
              open real,
              high real,
              low real,
              close real not null,
              pre_close real,
              change_pct real,
              volume real,
              amount real,
              turnover_rate real,
              pe_ttm real,
              pb real,
              ps_ttm real,
              pcf_ncf_ttm real,
              is_st integer,
              trade_status text,
              raw_json text not null default '{}',
              fetched_at text not null,
              primary key (symbol, trade_date, provider, adjust)
            );

            create table if not exists financial_metrics_history (
              symbol text not null references symbols(symbol),
              report_period text not null,
              provider text not null,
              announce_date text,
              revenue_growth real,
              roe real,
              fcf_margin real,
              debt_ratio real,
              gross_margin real,
              net_margin real,
              net_profit real,
              eps_ttm real,
              mb_revenue real,
              total_share real,
              liqa_share real,
              nr_turn_ratio real,
              nr_turn_days real,
              inv_turn_ratio real,
              inv_turn_days real,
              ca_turn_ratio real,
              asset_turn_ratio real,
              yoy_equity real,
              yoy_asset real,
              yoy_ni real,
              yoy_eps_basic real,
              yoy_pni real,
              current_ratio real,
              quick_ratio real,
              cash_ratio real,
              yoy_liability real,
              liability_to_asset real,
              asset_to_equity real,
              ca_to_asset real,
              tangible_asset_to_asset real,
              ebit_to_interest real,
              operating_cash_flow_to_asset real,
              operating_cash_flow_to_debt real,
              dupont_roe real,
              dupont_asset_to_equity real,
              dupont_asset_turn real,
              dupont_pnitoni real,
              dupont_nitogr real,
              dupont_tax_burden real,
              dupont_int_burden real,
              dupont_ebit_to_gr real,
              raw_json text not null default '{}',
              fetched_at text not null,
              primary key (symbol, report_period, provider)
            );

            create table if not exists company_reports_history (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              report_period text not null,
              provider text not null,
              report_type text not null,
              report_key text not null,
              published_at text not null default '',
              title text not null default '',
              summary text not null default '',
              raw_json text not null default '{}',
              fetched_at text not null,
              unique (provider, symbol, report_type, report_key)
            );

            create table if not exists filings_history (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              source text not null,
              published_at text not null,
              title text not null,
              url text not null,
              category text not null default '',
              source_tier text not null default 'S',
              raw_json text not null default '{}',
              fetched_at text not null,
              unique (source, symbol, url)
            );

            create table if not exists filing_refresh_state (
              symbol text not null references symbols(symbol),
              source text not null,
              start_date text not null,
              end_date text not null,
              status text not null,
              document_count integer not null default 0,
              last_error text not null default '',
              fetched_at text not null,
              primary key (symbol, source)
            );

            create table if not exists ingestion_runs (
              id integer primary key autoincrement,
              provider text not null,
              scope text not null,
              status text not null,
              started_at text not null,
              finished_at text,
              requested_symbols text not null default '[]',
              updated_symbols text not null default '[]',
              counts_json text not null default '{}',
              errors_json text not null default '[]'
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

            create table if not exists community_posts (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              source text not null,
              source_post_id text not null,
              title text not null default '',
              content text not null default '',
              author text not null default '',
              url text not null default '',
              published_at text not null default '',
              metrics_json text not null default '{}',
              raw_json text not null default '{}',
              fetched_at text not null,
              unique (source, symbol, source_post_id)
            );

            create table if not exists sentiment_evidence (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              sentiment_type text not null,
              source_table text not null,
              source_id text not null,
              source text not null default '',
              event_date text not null default '',
              title text not null default '',
              url text not null default '',
              category text not null default '',
              sentiment_score real not null,
              sentiment_label text not null,
              confidence real not null,
              impact_horizon text not null default '',
              keywords_json text not null default '[]',
              evidence_json text not null default '{}',
              model_provider text not null default 'local',
              model_name text not null default 'rule-v1',
              method_version text not null,
              analyzed_at text not null,
              unique (sentiment_type, source_table, source_id, method_version)
            );

            create table if not exists sentiment_snapshots (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              as_of text not null,
              window_days integer not null,
              filing_news_score real,
              community_score real,
              market_score real,
              composite_score real not null,
              sentiment_label text not null,
              confidence real not null,
              source_counts_json text not null default '{}',
              raw_json text not null default '{}',
              method_version text not null,
              generated_at text not null,
              unique (symbol, as_of, window_days, method_version)
            );

            create table if not exists community_sentiment_daily (
              id integer primary key autoincrement,
              symbol text not null references symbols(symbol),
              source text not null default 'eastmoney_guba',
              trade_date text not null,
              analyzed_count integer not null default 0,
              positive_count integer not null default 0,
              negative_count integer not null default 0,
              neutral_count integer not null default 0,
              sentiment_score real not null default 0,
              sentiment_label text not null default 'neutral',
              confidence real not null default 0,
              conclusion text not null default '',
              label_counts_json text not null default '{}',
              keyword_counts_json text not null default '{}',
              model_provider text not null default 'local',
              model_name text not null default 'fallback-v1',
              method_version text not null,
              generated_at text not null,
              raw_json text not null default '{}',
              unique (symbol, source, trade_date, method_version)
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

            create index if not exists idx_symbols_market_name
            on symbols(market, name);

            create index if not exists idx_symbol_aliases_symbol
            on symbol_aliases(symbol);

            create index if not exists idx_daily_bars_symbol_date
            on daily_bars(symbol, trade_date desc);

            create index if not exists idx_daily_bars_date_amount
            on daily_bars(trade_date, amount desc);

            create index if not exists idx_daily_bars_pe
            on daily_bars(trade_date, pe_ttm);

            create index if not exists idx_financial_metrics_symbol_period
            on financial_metrics_history(symbol, report_period desc);

            create index if not exists idx_filings_symbol_published
            on filings_history(symbol, published_at desc);

            create index if not exists idx_filing_refresh_state_fetched
            on filing_refresh_state(source, fetched_at);

            create index if not exists idx_company_reports_symbol_period
            on company_reports_history(symbol, report_period desc, published_at desc);

            create index if not exists idx_community_posts_symbol_published
            on community_posts(symbol, published_at desc);

            create index if not exists idx_sentiment_evidence_symbol_type_date
            on sentiment_evidence(symbol, sentiment_type, event_date desc);

            create index if not exists idx_sentiment_snapshots_symbol_generated
            on sentiment_snapshots(symbol, generated_at desc);

            create index if not exists idx_community_sentiment_daily_symbol_date
            on community_sentiment_daily(symbol, trade_date desc);
            """
        )
        seed_if_empty(conn)
        sync_seed_symbols(conn)
        sync_seed_analysis_runs(conn)
        sync_seed_memories(conn)
        seed_admin_account(conn)
        migrate_account_scoped_data_sources(conn)
        migrate_daily_bars_extra_metrics(conn)
        migrate_financial_metrics_history_columns(conn)
        migrate_tushare_legacy_fcf_margin(conn)
        seed_shared_snapshots_if_empty(conn)
        seed_data_sources(conn)
        sync_symbol_aliases(conn)
        backfill_warehouse_from_snapshots(conn)


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


def sync_symbol_aliases(conn: sqlite3.Connection) -> None:
    updated_at = now_iso()
    rows = conn.execute("select symbol, name from symbols").fetchall()
    aliases: list[dict[str, str]] = []
    for row in rows:
        symbol = row["symbol"]
        code = symbol.split(".")[0]
        name = row["name"]
        for alias in {symbol, symbol.upper(), code, name, pinyin_initials(name)}:
            normalized = normalize_alias(alias)
            if normalized:
                aliases.append(
                    {
                        "alias": alias,
                        "normalized_alias": normalized,
                        "symbol": symbol,
                        "source": "symbol-sync",
                        "updated_at": updated_at,
                    }
                )
    conn.executemany(
        """
        insert into symbol_aliases (alias, normalized_alias, symbol, source, updated_at)
        values (:alias, :normalized_alias, :symbol, :source, :updated_at)
        on conflict(normalized_alias, symbol) do update set
          alias = excluded.alias,
          source = excluded.source,
          updated_at = excluded.updated_at
        """,
        aliases,
    )


def normalize_alias(value: str) -> str:
    return value.strip().lower().replace(" ", "")


def backfill_warehouse_from_snapshots(conn: sqlite3.Connection) -> None:
    fetched_at = now_iso()
    for row in conn.execute("select * from market_snapshots"):
        raw = json.loads(row["raw_json"] or "{}")
        trade_date = snapshot_as_of_to_trade_date(row["as_of"])
        if not trade_date:
            continue
        conn.execute(
            """
            insert into daily_bars (
              symbol, trade_date, provider, adjust, open, high, low, close, pre_close,
              change_pct, volume, amount, turnover_rate, pe_ttm, pb, ps_ttm,
              pcf_ncf_ttm, is_st, trade_status, raw_json, fetched_at
            )
            values (?, ?, ?, '', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(symbol, trade_date, provider, adjust) do update set
              open = excluded.open,
              high = excluded.high,
              low = excluded.low,
              close = excluded.close,
              pre_close = excluded.pre_close,
              change_pct = excluded.change_pct,
              volume = excluded.volume,
              amount = excluded.amount,
              turnover_rate = excluded.turnover_rate,
              pe_ttm = excluded.pe_ttm,
              pb = excluded.pb,
              ps_ttm = excluded.ps_ttm,
              pcf_ncf_ttm = excluded.pcf_ncf_ttm,
              is_st = excluded.is_st,
              trade_status = excluded.trade_status,
              raw_json = excluded.raw_json,
              fetched_at = excluded.fetched_at
            """,
            (
                row["symbol"],
                trade_date,
                row["provider"],
                float_from_raw(raw, ["daily", "open"], row["price"]),
                float_from_raw(raw, ["daily", "high"], row["price"]),
                float_from_raw(raw, ["daily", "low"], row["price"]),
                row["price"],
                float_from_raw(raw, ["daily", "pre_close"], None),
                raw.get("change"),
                row["volume"],
                row["amount"],
                row["turnover_rate"],
                raw.get("pe"),
                raw.get("pb"),
                raw.get("ps_ttm") or raw.get("ps"),
                raw.get("pcf_ncf_ttm"),
                raw.get("is_st"),
                raw.get("trade_status"),
                row["raw_json"],
                row["fetched_at"] or fetched_at,
            ),
        )

    for row in conn.execute("select * from financial_snapshots"):
        fcf_margin = row["fcf_margin"]
        raw_json = str(row["raw_json"] or "")
        if row["provider"] == "tushare-financial":
            fcf_margin = tushare_snapshot_fcf_margin_for_history(raw_json, fcf_margin)
        conn.execute(
            """
            insert into financial_metrics_history (
              symbol, report_period, provider, announce_date, revenue_growth, roe,
              fcf_margin, debt_ratio, raw_json, fetched_at
            )
            values (?, ?, ?, '', ?, ?, ?, ?, ?, ?)
            on conflict(symbol, report_period, provider) do update set
              revenue_growth = excluded.revenue_growth,
              roe = excluded.roe,
              fcf_margin = excluded.fcf_margin,
              debt_ratio = excluded.debt_ratio,
              raw_json = excluded.raw_json,
              fetched_at = excluded.fetched_at
            """,
            (
                row["symbol"],
                row["period"],
                row["provider"],
                row["revenue_growth"],
                row["roe"],
                fcf_margin,
                row["debt_ratio"],
                row["raw_json"],
                fetched_at,
            ),
        )


def snapshot_as_of_to_trade_date(value: str) -> str:
    text = str(value or "")
    if len(text) >= 10:
        return text[:10]
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return ""


def float_from_raw(raw: dict[str, Any], path: list[str], default: Any) -> Any:
    value: Any = raw
    for key in path:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value in (None, "") else value


def tushare_snapshot_fcf_margin_for_history(raw_json: str, fallback: Any) -> Any:
    try:
        raw = json.loads(raw_json or "{}")
    except json.JSONDecodeError:
        raw = {}
    if isinstance(raw, dict) and raw.get("fcf_margin_source"):
        return raw.get("fcf_margin")
    if "fcf_margin_source" not in raw_json and "cashflow" not in raw_json:
        return None
    return fallback


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
    favorite_count = conn.execute(
        "select count(*) as count from account_favorites where account_id = 'acct-admin'"
    ).fetchone()["count"]
    if favorite_count:
        return
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


def migrate_daily_bars_extra_metrics(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("pragma table_info(daily_bars)")}
    additions = [
        ("ps_ttm", "real"),
        ("pcf_ncf_ttm", "real"),
        ("is_st", "integer"),
        ("trade_status", "text"),
    ]
    for name, column_type in additions:
        if name not in columns:
            conn.execute(f"alter table daily_bars add column {name} {column_type}")

    conn.execute(
        """
        update daily_bars
        set
          ps_ttm = case
            when ps_ttm is null and provider = 'baostock-market' and nullif(json_extract(raw_json, '$.psTTM'), '') is not null
            then cast(json_extract(raw_json, '$.psTTM') as real)
            when ps_ttm is null and provider = 'baostock-market' and nullif(json_extract(raw_json, '$.daily.psTTM'), '') is not null
            then cast(json_extract(raw_json, '$.daily.psTTM') as real)
            when ps_ttm is null and provider = 'tushare-market' and nullif(json_extract(raw_json, '$.daily_basic.ps_ttm'), '') is not null
            then cast(json_extract(raw_json, '$.daily_basic.ps_ttm') as real)
            when ps_ttm is null and provider = 'tushare-market' and nullif(json_extract(raw_json, '$.daily_basic.ps'), '') is not null
            then cast(json_extract(raw_json, '$.daily_basic.ps') as real)
            else ps_ttm
          end,
          pcf_ncf_ttm = case
            when pcf_ncf_ttm is null and provider = 'baostock-market' and nullif(json_extract(raw_json, '$.pcfNcfTTM'), '') is not null
            then cast(json_extract(raw_json, '$.pcfNcfTTM') as real)
            when pcf_ncf_ttm is null and provider = 'baostock-market' and nullif(json_extract(raw_json, '$.daily.pcfNcfTTM'), '') is not null
            then cast(json_extract(raw_json, '$.daily.pcfNcfTTM') as real)
            else pcf_ncf_ttm
          end,
          is_st = case
            when is_st is null and provider = 'baostock-market' and nullif(json_extract(raw_json, '$.isST'), '') is not null
            then cast(json_extract(raw_json, '$.isST') as integer)
            when is_st is null and provider = 'baostock-market' and nullif(json_extract(raw_json, '$.daily.isST'), '') is not null
            then cast(json_extract(raw_json, '$.daily.isST') as integer)
            else is_st
          end,
          trade_status = case
            when trade_status is null and provider = 'baostock-market' and nullif(json_extract(raw_json, '$.tradestatus'), '') is not null
            then cast(json_extract(raw_json, '$.tradestatus') as text)
            when trade_status is null and provider = 'baostock-market' and nullif(json_extract(raw_json, '$.daily.tradestatus'), '') is not null
            then cast(json_extract(raw_json, '$.daily.tradestatus') as text)
            else trade_status
          end
        where json_valid(raw_json)
          and (
            ps_ttm is null
            or pcf_ncf_ttm is null
            or is_st is null
            or trade_status is null
          )
        """
    )


def migrate_financial_metrics_history_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("pragma table_info(financial_metrics_history)")}
    additions = [
        ("net_profit", "real"),
        ("eps_ttm", "real"),
        ("mb_revenue", "real"),
        ("total_share", "real"),
        ("liqa_share", "real"),
        ("nr_turn_ratio", "real"),
        ("nr_turn_days", "real"),
        ("inv_turn_ratio", "real"),
        ("inv_turn_days", "real"),
        ("ca_turn_ratio", "real"),
        ("asset_turn_ratio", "real"),
        ("yoy_equity", "real"),
        ("yoy_asset", "real"),
        ("yoy_ni", "real"),
        ("yoy_eps_basic", "real"),
        ("yoy_pni", "real"),
        ("current_ratio", "real"),
        ("quick_ratio", "real"),
        ("cash_ratio", "real"),
        ("yoy_liability", "real"),
        ("liability_to_asset", "real"),
        ("asset_to_equity", "real"),
        ("ca_to_asset", "real"),
        ("tangible_asset_to_asset", "real"),
        ("ebit_to_interest", "real"),
        ("operating_cash_flow_to_asset", "real"),
        ("operating_cash_flow_to_debt", "real"),
        ("dupont_roe", "real"),
        ("dupont_asset_to_equity", "real"),
        ("dupont_asset_turn", "real"),
        ("dupont_pnitoni", "real"),
        ("dupont_nitogr", "real"),
        ("dupont_tax_burden", "real"),
        ("dupont_int_burden", "real"),
        ("dupont_ebit_to_gr", "real"),
    ]
    for name, column_type in additions:
        if name not in columns:
            conn.execute(f"alter table financial_metrics_history add column {name} {column_type}")
    conn.execute(
        """
        create table if not exists company_reports_history (
          id integer primary key autoincrement,
          symbol text not null references symbols(symbol),
          report_period text not null,
          provider text not null,
          report_type text not null,
          report_key text not null,
          published_at text not null default '',
          title text not null default '',
          summary text not null default '',
          raw_json text not null default '{}',
          fetched_at text not null,
          unique (provider, symbol, report_type, report_key)
        )
        """
    )
    conn.execute(
        """
        create index if not exists idx_company_reports_symbol_period
        on company_reports_history(symbol, report_period desc, published_at desc)
        """
    )


def migrate_tushare_legacy_fcf_margin(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        update financial_metrics_history
        set fcf_margin = null
        where provider = 'tushare-financial'
          and (
            (instr(coalesce(raw_json, ''), 'fcf_margin_source') = 0 and instr(coalesce(raw_json, ''), 'cashflow') = 0)
            or instr(coalesce(raw_json, ''), 'missing_cashflow_or_revenue') > 0
            or instr(coalesce(raw_json, ''), '"fcf_margin": null') > 0
          )
        """
    )
    conn.execute(
        """
        update financial_snapshots
        set fcf_margin = 0
        where provider = 'tushare-financial'
          and (
            (instr(coalesce(raw_json, ''), 'fcf_margin_source') = 0 and instr(coalesce(raw_json, ''), 'cashflow') = 0)
            or instr(coalesce(raw_json, ''), 'missing_cashflow_or_revenue') > 0
            or instr(coalesce(raw_json, ''), '"fcf_margin": null') > 0
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
