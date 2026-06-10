#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="keiko-warehouse-test-") as temp_dir:
        os.environ["KEIKO_DATA_DIR"] = temp_dir

        from backend.db import get_db, init_db
        from backend.history import (
            BAOSTOCK_MARKET_PROVIDER,
            baostock_daily_backfill_plan,
            baostock_financial_backfill_plan,
            finish_ingestion,
            start_ingestion,
            update_ingestion_progress,
            upsert_baostock_financial_metrics,
        )
        from backend.providers.baostock_provider import BaostockError, run_baostock_child_with_timeout

        init_db()
        test_child_timeout(BaostockError, run_baostock_child_with_timeout)
        with get_db() as conn:
            test_finished_run_guard(conn, start_ingestion, update_ingestion_progress, finish_ingestion)
            test_daily_backfill_plan(conn, BAOSTOCK_MARKET_PROVIDER, baostock_daily_backfill_plan)
            test_quarterly_no_data_retry(conn, upsert_baostock_financial_metrics, baostock_financial_backfill_plan)
    print("warehouse guard tests ok")
    return 0


def test_child_timeout(BaostockError, run_baostock_child_with_timeout) -> None:
    started = time.monotonic()
    try:
        run_baostock_child_with_timeout(time.sleep, (2,), {}, 0.2, "timeout-test")
    except BaostockError as exc:
        assert "timed out" in str(exc), exc
    else:
        raise AssertionError("timeout-test unexpectedly completed")
    assert time.monotonic() - started < 1.5


def test_finished_run_guard(conn, start_ingestion, update_ingestion_progress, finish_ingestion) -> None:
    run_id = start_ingestion(conn, "baostock", "guard-test", [], False)
    update_ingestion_progress(conn, run_id, ["before"], {"batches": 1}, [])
    finish_ingestion(conn, run_id, "partial", ["before"], {"batches": 1}, [])
    before = run_row(conn, run_id)

    update_ingestion_progress(conn, run_id, ["after"], {"batches": 99}, [{"scope": "bad", "error": "should not write"}])
    after_progress = run_row(conn, run_id)
    assert after_progress["status"] == "partial", after_progress
    assert after_progress["finished_at"] == before["finished_at"], after_progress
    assert json.loads(after_progress["updated_symbols"]) == ["before"], after_progress
    assert json.loads(after_progress["counts_json"])["batches"] == 1, after_progress

    finish_ingestion(conn, run_id, "ok", ["after"], {"batches": 100}, [])
    after_finish = run_row(conn, run_id)
    assert after_finish["status"] == "partial", after_finish
    assert json.loads(after_finish["counts_json"])["batches"] == 1, after_finish


def test_daily_backfill_plan(conn, provider: str, baostock_daily_backfill_plan) -> None:
    insert_symbol(conn, "TEST01.SH", "前后缺口")
    insert_daily_bar(conn, "TEST01.SH", "2026-02-03", provider)
    insert_daily_bar(conn, "TEST01.SH", "2026-06-05", provider)
    plan = baostock_daily_backfill_plan(
        conn,
        ["TEST01.SH"],
        start_date="2025-09-21",
        end_date="2026-06-08",
    )
    assert plan == {
        "TEST01.SH": [
            ("2026-06-06", "2026-06-08"),
            ("2025-09-21", "2026-02-02"),
        ]
    }, plan

    insert_symbol(conn, "TEST02.SH", "完整覆盖")
    for index in range(119):
        day = datetime.fromisoformat("2025-09-21").date() + timedelta(days=index)
        insert_daily_bar(conn, "TEST02.SH", day.isoformat(), provider)
    insert_daily_bar(conn, "TEST02.SH", "2026-06-08", provider)
    complete = baostock_daily_backfill_plan(
        conn,
        ["TEST02.SH"],
        start_date="2025-09-21",
        end_date="2026-06-08",
    )
    assert complete == {}, complete


def test_quarterly_no_data_retry(conn, upsert_baostock_financial_metrics, baostock_financial_backfill_plan) -> None:
    insert_symbol(conn, "TEST03.SH", "季报占位")
    periods = [(2026, 1), (2025, 4), (2025, 3)]
    upsert_baostock_financial_metrics(
        conn,
        {},
        ["TEST03.SH"],
        [periods[0]],
        set(),
        requested_periods_by_symbol={"TEST03.SH": [periods[0]]},
    )
    fresh = baostock_financial_backfill_plan(conn, ["TEST03.SH"], periods)
    assert fresh == {"TEST03.SH": [(2025, 4), (2025, 3)]}, fresh

    old_time = (datetime.now() - timedelta(days=10)).isoformat(timespec="seconds")
    conn.execute(
        """
        update financial_metrics_history
        set fetched_at = ?
        where symbol = 'TEST03.SH'
          and provider = 'baostock-financial'
          and report_period = '2026-03-31'
        """,
        (old_time,),
    )
    stale = baostock_financial_backfill_plan(conn, ["TEST03.SH"], periods)
    assert stale == {"TEST03.SH": [(2026, 1), (2025, 4), (2025, 3)]}, stale


def insert_symbol(conn, symbol: str, name: str) -> None:
    conn.execute(
        """
        insert into symbols (symbol, market, name, currency, exchange, sector, industry)
        values (?, 'A', ?, 'CNY', 'SSE', 'A股', '')
        on conflict(symbol) do update set name = excluded.name
        """,
        (symbol, name),
    )


def insert_daily_bar(conn, symbol: str, trade_date: str, provider: str) -> None:
    conn.execute(
        """
        insert or replace into daily_bars (
          symbol, trade_date, provider, adjust, close, raw_json, fetched_at
        )
        values (?, ?, ?, 'qfq', 1, '{}', ?)
        """,
        (symbol, trade_date, provider, datetime.now().isoformat(timespec="seconds")),
    )


def run_row(conn, run_id: int):
    row = conn.execute("select * from ingestion_runs where id = ?", (run_id,)).fetchone()
    assert row is not None, run_id
    return row


if __name__ == "__main__":
    raise SystemExit(main())
