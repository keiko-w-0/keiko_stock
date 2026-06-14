#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import DB_PATH  # noqa: E402
from backend.history import (  # noqa: E402
    BAOSTOCK_FINANCIAL_PROVIDER,
    BAOSTOCK_MARKET_PROVIDER,
    baostock_daily_backfill_plan,
    baostock_history_start_date,
    baostock_financial_backfill_plan,
    financial_storage_periods,
    latest_baostock_daily_trade_date,
    quarter_period_key,
    quarter_end_date,
    recent_quarter_periods,
    scan_warehouse_duplicates,
)


PROVIDER = "baostock-market"


def main() -> None:
    parser = argparse.ArgumentParser(description="Debug the local stock history warehouse.")
    parser.add_argument("--db", default=str(DB_PATH), help="SQLite database path. Defaults to backend DB_PATH.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a simple table.")
    parser.add_argument("--raw", action="store_true", help="Print a single selected column without table formatting.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("summary", help="Warehouse totals and latest dates.")
    subparsers.add_parser("tables", help="Row counts for all tables.")
    subparsers.add_parser("providers", help="daily_bars coverage grouped by provider.")
    subparsers.add_parser("coverage", help="Universe vs BaoStock K-line coverage and latest backfill status.")
    subparsers.add_parser("backfill-status", help="BaoStock daily target coverage and latest run progress.")
    subparsers.add_parser("duplicates", help="Duplicate daily_bars rows by symbol/date/provider.")
    dedupe_scan = subparsers.add_parser("dedupe-scan", help="Scan warehouse duplicate patterns (filings/market_snapshots/daily_bars).")
    subparsers.add_parser("pe", help="PE/PB coverage and latest PE samples.")
    subparsers.add_parser("financials", help="Quarterly financial metrics coverage grouped by provider.")

    daily_symbol = subparsers.add_parser("daily-symbol", help="Show BaoStock daily-bar incremental request plan for one symbol or name.")
    daily_symbol.add_argument("query")
    daily_symbol.add_argument("--days", type=int, default=260)

    financial_symbol = subparsers.add_parser("financial-symbol", help="Show BaoStock quarterly financial gaps for one symbol or name.")
    financial_symbol.add_argument("query")
    financial_symbol.add_argument("--quarters", type=int, default=12)

    missing = subparsers.add_parser("missing-bars", help="Symbols without enough BaoStock daily bars.")
    missing.add_argument("--min-bars", type=int, default=120)
    missing.add_argument("--limit", type=int, default=80)

    symbol = subparsers.add_parser("symbol", help="Show warehouse rows for one symbol or name.")
    symbol.add_argument("query")
    symbol.add_argument("--limit", type=int, default=20)

    runs = subparsers.add_parser("runs", help="Recent ingestion runs.")
    runs.add_argument("--limit", type=int, default=10)

    sql = subparsers.add_parser("sql", help="Run a read-only SQL statement.")
    sql.add_argument("statement")
    sql.add_argument("--limit", type=int, default=200)

    args = parser.parse_args()
    conn = sqlite3.connect(Path(args.db).expanduser())
    conn.row_factory = sqlite3.Row
    try:
        if args.command == "summary":
            rows = summary(conn)
        elif args.command == "tables":
            rows = table_counts(conn)
        elif args.command == "providers":
            rows = providers(conn)
        elif args.command == "coverage":
            rows = coverage(conn)
        elif args.command == "backfill-status":
            rows = coverage(conn)
        elif args.command == "duplicates":
            rows = duplicates(conn)
        elif args.command == "dedupe-scan":
            payload = scan_warehouse_duplicates(conn)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
                return
            rows = [{"metric": key, "value": value} for key, value in payload.items() if key != "notes"]
        elif args.command == "pe":
            rows = pe_coverage(conn)
        elif args.command == "financials":
            rows = financial_coverage(conn)
        elif args.command == "daily-symbol":
            rows = daily_symbol_rows(conn, args.query, args.days)
        elif args.command == "financial-symbol":
            rows = financial_symbol_rows(conn, args.query, args.quarters)
        elif args.command == "missing-bars":
            rows = missing_bars(conn, args.min_bars, args.limit)
        elif args.command == "symbol":
            rows = symbol_rows(conn, args.query, args.limit)
        elif args.command == "runs":
            rows = ingestion_runs(conn, args.limit)
        elif args.command == "sql":
            rows = readonly_sql(conn, args.statement, args.limit)
        else:
            raise SystemExit(f"unknown command: {args.command}")
        print_rows(rows, as_json=args.json, raw=args.raw)
    finally:
        conn.close()


def summary(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return query(
        conn,
        """
        select 'symbols' metric, count(*) value, null detail from symbols
        union all select 'symbol_aliases', count(*), null from symbol_aliases
        union all select 'daily_bars', count(*), max(trade_date) from daily_bars
        union all select 'baostock_symbols_with_bars', count(distinct symbol), max(trade_date)
          from daily_bars where provider = ?
        union all select 'baostock_positive_pe_rows',
          sum(case when pe_ttm is not null and pe_ttm > 0 then 1 else 0 end), null
          from daily_bars where provider = ?
        union all select 'market_snapshots', count(*), max(as_of) from market_snapshots
        union all select 'filings_history', count(*), max(published_at) from filings_history
        union all select 'financial_metrics_history', count(*), max(report_period) from financial_metrics_history
        union all select 'company_reports_history', count(*), max(report_period) from company_reports_history
        """,
        (PROVIDER, PROVIDER),
    )


def table_counts(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    names = [
        row["name"]
        for row in conn.execute(
            "select name from sqlite_master where type = 'table' and name not like 'sqlite_%' order by name"
        )
    ]
    return [{"table": name, "rows": scalar(conn, f"select count(*) from {quote_identifier(name)}")} for name in names]


def providers(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return query(
        conn,
        """
        select
          provider,
          count(*) rows,
          count(distinct symbol) symbols,
          min(trade_date) min_date,
          max(trade_date) max_date,
          sum(case when pe_ttm is not null and pe_ttm > 0 then 1 else 0 end) pe_rows,
          sum(case when pb is not null and pb > 0 then 1 else 0 end) pb_rows,
          sum(case when ps_ttm is not null and ps_ttm > 0 then 1 else 0 end) ps_rows,
          sum(case when pcf_ncf_ttm is not null and pcf_ncf_ttm > 0 then 1 else 0 end) pcf_rows,
          sum(case when is_st = 1 then 1 else 0 end) st_rows
        from daily_bars
        group by provider
        order by rows desc
        """,
    )


def a_share_symbols(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        select symbol
        from symbols
        where market = 'A'
          and (symbol like '%.SH' or symbol like '%.SZ' or symbol like '%.BJ')
        order by symbol
        """
    ).fetchall()
    return [row["symbol"] for row in rows]


def latest_daily_backfill_run(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute(
        """
        select id, provider, scope, status, started_at, finished_at, counts_json, errors_json
        from ingestion_runs
        where provider = 'baostock'
          and scope like 'a-share-history-background%'
        order by id desc
        limit 1
        """
    ).fetchone()
    return dict(row) if row else None


def coverage(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    target_end = latest_baostock_daily_trade_date()
    target_start = baostock_history_start_date(target_end, 260)
    rows = query(
        conn,
        """
        with a_universe as (
          select symbol from symbols
          where market = 'A' and (symbol like '%.SH' or symbol like '%.SZ' or symbol like '%.BJ')
        ),
        b as (
          select symbol, count(*) bars, max(trade_date) latest
          from daily_bars
          where provider = ?
          group by symbol
        )
        select 'target_end' metric, ? value, 'BaoStock daily target for a new run now' detail
        union all select 'target_start', ?, '260-day request window start'
        union all select 'a_universe', count(*), 'A-share/ETF/index symbols in symbols table' from a_universe
        union all select 'with_baostock_bars', count(*), 'symbols with any baostock-market daily row' from a_universe u join b on b.symbol = u.symbol
        union all select 'without_baostock_bars', count(*), 'currently all are 920xxx.BJ in this database' from a_universe u left join b on b.symbol = u.symbol where b.symbol is null
        union all select 'with_latest_target', count(*), 'symbols whose latest BaoStock bar reaches target_end' from a_universe u join b on b.symbol = u.symbol where b.latest >= ?
        union all select 'before_latest_target_or_none', count(*), 'symbols missing target_end or with no BaoStock bars' from a_universe u left join b on b.symbol = u.symbol where b.symbol is null or b.latest < ?
        union all select 'with_120plus_bars', count(*), 'symbols with at least 120 BaoStock daily dates' from a_universe u join b on b.symbol = u.symbol where b.bars >= 120
        union all select 'under_120_bars', count(*), 'includes new listings and symbols with no BaoStock bars' from a_universe u left join b on b.symbol = u.symbol where coalesce(b.bars, 0) < 120
        union all select 'no_bars_920_bj', count(*), '920xxx.BJ symbols currently have no BaoStock daily rows' from a_universe u left join b on b.symbol = u.symbol where b.symbol is null and u.symbol like '920%.BJ'
        """,
        (PROVIDER, target_end, target_start, target_end, target_end),
    )
    symbols = a_share_symbols(conn)
    plan = baostock_daily_backfill_plan(conn, symbols, start_date=target_start, end_date=target_end)
    rows.append(
        {
            "metric": "planned_backfill_symbols",
            "value": len(plan),
            "detail": f"symbols still selected by current plan for {target_start}..{target_end}",
        }
    )
    latest_run = latest_daily_backfill_run(conn)
    if latest_run:
        counts = json.loads(latest_run.get("counts_json") or "{}")
        errors = json.loads(latest_run.get("errors_json") or "[]")
        rows.extend(
            [
                {"metric": "latest_run_id", "value": latest_run["id"], "detail": latest_run["scope"]},
                {"metric": "latest_run_status", "value": latest_run["status"], "detail": latest_run.get("finished_at") or "not finished"},
                {"metric": "latest_run_target_end", "value": counts.get("target_end", ""), "detail": counts.get("target_start", "")},
                {"metric": "latest_run_daily_bars", "value": counts.get("daily_bars", 0), "detail": "rows written by that run"},
                {"metric": "latest_run_snapshots", "value": counts.get("market_snapshots", 0), "detail": "snapshots written by that run"},
                {"metric": "latest_run_batches", "value": counts.get("batches", 0), "detail": f"batch_size={counts.get('batch_size', '')}"},
                {"metric": "latest_run_remaining", "value": counts.get("remaining_candidates", ""), "detail": "remaining under that run's plan"},
                {"metric": "latest_run_last_progress", "value": counts.get("last_progress_at", ""), "detail": f"errors={len(errors)}"},
            ]
        )
    return rows


def missing_bars(conn: sqlite3.Connection, min_bars: int, limit: int) -> list[dict[str, Any]]:
    return query(
        conn,
        """
        select
          s.symbol,
          s.name,
          s.exchange,
          s.industry,
          coalesce(d.bars, 0) bars,
          d.latest
        from symbols s
        left join (
          select symbol, count(*) bars, max(trade_date) latest
          from daily_bars
          where provider = ?
          group by symbol
        ) d on d.symbol = s.symbol
        where s.market = 'A'
          and (s.symbol like '%.SH' or s.symbol like '%.SZ' or s.symbol like '%.BJ')
          and coalesce(d.bars, 0) < ?
        order by coalesce(d.bars, 0), s.symbol
        limit ?
        """,
        (PROVIDER, min_bars, limit),
    )


def duplicates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return query(
        conn,
        """
        select symbol, trade_date, provider, adjust, count(*) rows
        from daily_bars
        group by symbol, trade_date, provider, adjust
        having count(*) > 1
        order by rows desc, symbol, trade_date
        limit 100
        """,
    )


def pe_coverage(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = query(
        conn,
        """
        select
          provider,
          count(*) rows,
          count(distinct symbol) symbols,
          sum(case when pe_ttm is not null and pe_ttm > 0 then 1 else 0 end) positive_pe_rows,
          sum(case when pb is not null and pb > 0 then 1 else 0 end) positive_pb_rows
        from daily_bars
        group by provider
        order by rows desc
        """,
    )
    rows.extend(
        query(
            conn,
            """
            select
              'sample' provider,
              symbol || ' ' || trade_date rows,
              adjust symbols,
              pe_ttm positive_pe_rows,
              pb positive_pb_rows
            from daily_bars
            where provider = ? and pe_ttm is not null and pe_ttm > 0
            order by trade_date desc, symbol
            limit 12
            """,
            (PROVIDER,),
        )
    )
    return rows


def financial_coverage(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = query(
        conn,
        """
        select
          provider,
          count(*) rows,
          count(distinct symbol) symbols,
          min(report_period) min_period,
          max(report_period) max_period,
          sum(case when roe is not null then 1 else 0 end) roe_rows,
          sum(case when gross_margin is not null then 1 else 0 end) gross_margin_rows,
          sum(case when liability_to_asset is not null or debt_ratio is not null then 1 else 0 end) debt_rows,
          sum(case when json_valid(raw_json) and json_extract(raw_json, '$.status') = 'no_data' then 1 else 0 end) no_data_rows
        from financial_metrics_history
        group by provider
        order by rows desc
        """,
    )
    rows.extend(
        query(
            conn,
            """
            select
              provider || ':' || report_type provider,
              count(*) rows,
              count(distinct symbol) symbols,
              min(report_period) min_period,
              max(report_period) max_period,
              null roe_rows,
              null gross_margin_rows,
              null debt_rows,
              null no_data_rows
            from company_reports_history
            group by provider, report_type
            order by rows desc
            """,
        )
    )
    return rows


def daily_symbol_rows(conn: sqlite3.Connection, search: str, days: int) -> list[dict[str, Any]]:
    symbols = resolve_symbol_queries(conn, search, limit=20)
    if not symbols:
        return []
    target_end = latest_baostock_daily_trade_date()
    target_start = baostock_history_start_date(target_end, days)
    plan = baostock_daily_backfill_plan(conn, symbols, start_date=target_start, end_date=target_end, days=days)
    placeholders = ",".join("?" for _ in symbols)
    rows = query(
        conn,
        f"""
        select
          s.symbol,
          s.name,
          count(distinct d.trade_date) as bars,
          min(d.trade_date) as first_date,
          max(d.trade_date) as latest_date,
          count(distinct case when d.pe_ttm is not null and d.pe_ttm > 0 then d.trade_date end) pe_dates,
          count(distinct case when d.pb is not null and d.pb > 0 then d.trade_date end) pb_dates
        from symbols s
        left join daily_bars d
          on d.symbol = s.symbol
         and d.provider = ?
        where s.symbol in ({placeholders})
        group by s.symbol, s.name
        order by s.symbol
        """,
        (BAOSTOCK_MARKET_PROVIDER, *symbols),
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        request_ranges = plan.get(row["symbol"]) or []
        result.append(
            {
                **row,
                "target_start": target_start,
                "target_end": target_end,
                "request_ranges": ",".join(f"{start}..{end}" for start, end in request_ranges),
                "needs_backfill": "yes" if request_ranges else "no",
            }
        )
    return result


def financial_symbol_rows(conn: sqlite3.Connection, search: str, quarters: int) -> list[dict[str, Any]]:
    symbols = resolve_symbol_queries(conn, search, limit=20)
    if not symbols:
        return []
    periods = recent_quarter_periods(quarters)
    storage_periods = financial_storage_periods(periods)
    plan = baostock_financial_backfill_plan(conn, symbols, periods)
    placeholders = ",".join("?" for _ in symbols)
    period_placeholders = ",".join("?" for _ in storage_periods)
    metric_rows = query(
        conn,
        f"""
        select
          symbol,
          report_period,
          fetched_at,
          case
            when json_valid(raw_json) and json_extract(raw_json, '$.status') = 'no_data' then 'no_data'
            else 'ok'
          end as status,
          roe,
          gross_margin,
          net_margin,
          liability_to_asset,
          json_extract(raw_json, '$.period_key') as period_key
        from financial_metrics_history
        where provider = ?
          and symbol in ({placeholders})
          and report_period in ({period_placeholders})
        order by symbol, report_period desc
        """,
        (BAOSTOCK_FINANCIAL_PROVIDER, *symbols, *storage_periods),
    )
    by_key = {(row["symbol"], row["report_period"]): row for row in metric_rows}
    latest_ok = latest_ok_financial_periods(metric_rows)
    result: list[dict[str, Any]] = []
    for symbol in symbols:
        name = scalar(conn, "select name from symbols where symbol = ?", (symbol,))
        missing_periods = {quarter_end_date(year, quarter) for year, quarter in plan.get(symbol, [])}
        for year, quarter in periods:
            report_period = quarter_end_date(year, quarter)
            row = by_key.get((symbol, report_period))
            result.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "period_key": quarter_period_key(year, quarter),
                    "report_period": report_period,
                    "warehouse_status": row["status"] if row else "missing",
                    "needs_backfill": "yes" if report_period in missing_periods else "no",
                    "latest_ok_period": latest_ok.get(symbol, ""),
                    "roe": row.get("roe") if row else None,
                    "gross_margin": row.get("gross_margin") if row else None,
                    "debt_ratio": row.get("liability_to_asset") if row else None,
                    "fetched_at": row.get("fetched_at") if row else "",
                }
            )
    return result


def resolve_symbol_queries(conn: sqlite3.Connection, search: str, limit: int = 20) -> list[str]:
    normalized = search.strip().lower().replace(" ", "")
    if not normalized:
        return []
    rows = conn.execute(
        """
        select distinct s.symbol
        from symbols s
        left join symbol_aliases a on a.symbol = s.symbol
        where lower(replace(s.symbol, ' ', '')) = ?
           or lower(replace(s.name, ' ', '')) like ?
           or a.normalized_alias = ?
        order by s.symbol
        limit ?
        """,
        (normalized, f"%{normalized}%", normalized, limit),
    ).fetchall()
    return [row["symbol"] for row in rows]


def latest_ok_financial_periods(rows: list[dict[str, Any]]) -> dict[str, str]:
    latest: dict[str, str] = {}
    for row in rows:
        if row["status"] == "no_data":
            continue
        symbol = row["symbol"]
        period = row["report_period"]
        if period and period > latest.get(symbol, ""):
            latest[symbol] = period
    return latest


def symbol_rows(conn: sqlite3.Connection, search: str, limit: int) -> list[dict[str, Any]]:
    normalized = search.strip().lower().replace(" ", "")
    symbols = [
        row["symbol"]
        for row in conn.execute(
            """
            select distinct s.symbol
            from symbols s
            left join symbol_aliases a on a.symbol = s.symbol
            where lower(replace(s.symbol, ' ', '')) = ?
               or lower(replace(s.name, ' ', '')) like ?
               or a.normalized_alias = ?
            order by s.symbol
            limit 20
            """,
            (normalized, f"%{normalized}%", normalized),
        )
    ]
    if not symbols:
        return []
    placeholders = ",".join("?" for _ in symbols)
    return query(
        conn,
        f"""
        select
          s.symbol,
          s.name,
          d.provider,
          d.adjust,
          d.trade_date,
          d.close,
          d.amount,
          d.turnover_rate,
          d.pe_ttm,
          d.pb,
          d.ps_ttm,
          d.pcf_ncf_ttm,
          d.is_st,
          d.trade_status,
          d.fetched_at
        from symbols s
        left join daily_bars d on d.symbol = s.symbol
        where s.symbol in ({placeholders})
        order by s.symbol, d.trade_date desc, d.provider
        limit ?
        """,
        (*symbols, limit),
    )


def ingestion_runs(conn: sqlite3.Connection, limit: int) -> list[dict[str, Any]]:
    return query(
        conn,
        """
        select id, provider, scope, status, started_at, finished_at, counts_json, errors_json
        from ingestion_runs
        order by id desc
        limit ?
        """,
        (limit,),
    )


def readonly_sql(conn: sqlite3.Connection, statement: str, limit: int) -> list[dict[str, Any]]:
    stripped = statement.strip().rstrip(";")
    if not stripped.lower().startswith(("select", "with", "pragma")):
        raise SystemExit("Only read-only SELECT/WITH/PRAGMA statements are allowed.")
    if stripped.lower().startswith("pragma") and ";" in stripped:
        raise SystemExit("Multiple statements are not allowed.")
    sql = stripped
    if stripped.lower().startswith(("select", "with")) and " limit " not in f" {stripped.lower()} ":
        sql = f"select * from ({stripped}) limit ?"
        return query(conn, sql, (limit,))
    return query(conn, sql)


def query(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def scalar(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def print_rows(rows: list[dict[str, Any]], as_json: bool = False, raw: bool = False) -> None:
    if raw:
        if not rows:
            return
        columns = list(rows[0].keys())
        if len(columns) != 1:
            raise SystemExit("--raw requires the query to return exactly one column.")
        column = columns[0]
        for row in rows:
            value = row.get(column)
            if value is not None:
                print(value)
        return
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    if not rows:
        print("(no rows)")
        return
    columns = list(rows[0].keys())
    widths = {
        column: max(len(str(column)), *(display_width(row.get(column)) for row in rows))
        for column in columns
    }
    print("  ".join(str(column).ljust(widths[column]) for column in columns))
    print("  ".join("-" * widths[column] for column in columns))
    for row in rows:
        print("  ".join(format_cell(row.get(column)).ljust(widths[column]) for column in columns))


def display_width(value: Any) -> int:
    return len(format_cell(value))


def format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    text = str(value)
    if len(text) > 120:
        return text[:117] + "..."
    return text


if __name__ == "__main__":
    main()
