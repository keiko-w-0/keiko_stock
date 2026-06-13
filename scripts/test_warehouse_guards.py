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
            dedupe_filing_history_by_title,
            upsert_baostock_financial_metrics,
            upsert_filing_documents,
        )
        from backend.finnhub_service import (
            insert_financial_snapshot as insert_finnhub_financial_snapshot,
            normalize_symbols as normalize_finnhub_symbols,
            upsert_finnhub_symbol,
        )
        from backend.providers.baostock_provider import BaostockError, run_baostock_child_with_timeout
        from backend.tushare_service import insert_financial_snapshot as insert_tushare_financial_snapshot

        init_db()
        test_child_timeout(BaostockError, run_baostock_child_with_timeout)
        with get_db() as conn:
            test_finished_run_guard(conn, start_ingestion, update_ingestion_progress, finish_ingestion)
            test_daily_backfill_plan(conn, BAOSTOCK_MARKET_PROVIDER, baostock_daily_backfill_plan)
            test_quarterly_no_data_retry(conn, upsert_baostock_financial_metrics, baostock_financial_backfill_plan)
            test_tushare_fcf_margin_standardization(conn, insert_tushare_financial_snapshot)
            test_filing_title_dedupe(conn, upsert_filing_documents, dedupe_filing_history_by_title)
            test_finnhub_financial_history_and_hk_symbols(
                conn,
                insert_finnhub_financial_snapshot,
                normalize_finnhub_symbols,
                upsert_finnhub_symbol,
            )
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


def test_tushare_fcf_margin_standardization(conn, insert_tushare_financial_snapshot) -> None:
    insert_symbol(conn, "TEST04.SH", "Tushare FCF")
    insert_tushare_financial_snapshot(
        conn,
        "TEST04.SH",
        {"end_date": "20260331", "ann_date": "20260420", "or_yoy": "11.5", "roe_dt": "18.2", "ocf_to_or": "99"},
        {"end_date": "20260331", "ann_date": "20260420", "total_revenue": "1000", "n_income_attr_p": "120"},
        {"end_date": "20260331", "ann_date": "20260420", "n_cashflow_act": "300", "c_pay_acq_const_fiolta": "125"},
        {"pe_ttm": "20", "pb": "3"},
    )
    row = financial_metric_row(conn, "TEST04.SH", "20260331", "tushare-financial")
    assert round(row["fcf_margin"], 4) == 17.5, row
    assert row["revenue_growth"] == 11.5, row
    assert row["roe"] == 18.2, row
    raw = json.loads(row["raw_json"])
    assert raw["fcf_margin_source"] == "n_cashflow_act_minus_c_pay_acq_const_fiolta", raw
    assert raw["free_cash_flow"] == 175.0, raw

    insert_tushare_financial_snapshot(
        conn,
        "TEST04.SH",
        {"end_date": "20260630", "ann_date": "20260720", "or_yoy": "8", "roe_dt": "15", "ocf_to_or": "88"},
        {"end_date": "20260630", "ann_date": "20260720", "total_revenue": "1000"},
        None,
        {},
    )
    missing_cashflow = financial_metric_row(conn, "TEST04.SH", "20260630", "tushare-financial")
    assert missing_cashflow["fcf_margin"] is None, missing_cashflow
    snapshot = conn.execute(
        """
        select fcf_margin
        from financial_snapshots
        where symbol = 'TEST04.SH' and period = '20260630' and provider = 'tushare-financial'
        """
    ).fetchone()
    assert snapshot["fcf_margin"] == 0, snapshot


def test_filing_title_dedupe(conn, upsert_filing_documents, dedupe_filing_history_by_title) -> None:
    insert_symbol(conn, "TEST05.SH", "公告消重")
    insert_symbol(conn, "TEST06.SH", "公告同名隔离")
    duplicate_title = "关于以集中竞价交易方式回购公司股份方案的公告"
    upsert_filing_documents(
        conn,
        [
            {
                "symbol": "TEST05.SH",
                "source": "sse",
                "published_at": "2026-06-12",
                "title": f" {duplicate_title} ",
                "url": "https://example.test/sse-duplicate.pdf",
                "category": "其它",
                "source_tier": "S",
            },
            {
                "symbol": "TEST05.SH",
                "source": "cninfo",
                "published_at": "2026-06-12T00:00:00+08:00",
                "title": duplicate_title,
                "url": "https://example.test/cninfo-duplicate.pdf",
                "category": "其它",
                "source_tier": "S",
            },
            {
                "symbol": "TEST05.SH",
                "source": "sse",
                "published_at": "2026-06-13",
                "title": "第二届董事会第二十三次会议决议公告",
                "url": "https://example.test/sse-unique.pdf",
                "category": "其它",
                "source_tier": "S",
            },
            {
                "symbol": "TEST06.SH",
                "source": "sse",
                "published_at": "2026-06-12",
                "title": duplicate_title,
                "url": "https://example.test/other-symbol.pdf",
                "category": "其它",
                "source_tier": "S",
            },
        ],
    )
    duplicate_row = conn.execute(
        """
        select id
        from filings_history
        where symbol = 'TEST05.SH' and source = 'sse' and url = 'https://example.test/sse-duplicate.pdf'
        """
    ).fetchone()
    assert duplicate_row is not None
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        insert into sentiment_evidence (
          symbol, sentiment_type, source_table, source_id, source, event_date, title, url, category,
          sentiment_score, sentiment_label, confidence, impact_horizon,
          keywords_json, evidence_json, model_provider, model_name, method_version, analyzed_at
        )
        values (?, 'filing_news', 'filings_history', ?, 'sse', '2026-06-12', ?, '', 'filing',
          10, 'neutral', 0.8, '1w', '[]', '{}', 'local', 'fallback-v1', 'test-method', ?)
        """,
        ("TEST05.SH", str(duplicate_row["id"]), duplicate_title, now),
    )

    cleanup = dedupe_filing_history_by_title(conn)
    assert cleanup["duplicate_groups"] == 1, cleanup
    assert cleanup["filings_deleted"] == 1, cleanup
    assert cleanup["sentiment_evidence_deleted"] == 1, cleanup

    rows = conn.execute(
        """
        select symbol, source, title
        from filings_history
        where symbol in ('TEST05.SH', 'TEST06.SH')
        order by symbol, title
        """
    ).fetchall()
    assert len(rows) == 3, [dict(row) for row in rows]
    kept_duplicate = conn.execute(
        """
        select source
        from filings_history
        where symbol = 'TEST05.SH' and title = ?
        """,
        (duplicate_title,),
    ).fetchone()
    assert kept_duplicate["source"] == "cninfo", kept_duplicate
    evidence_count = conn.execute(
        """
        select count(*) as count
        from sentiment_evidence
        where source_table = 'filings_history'
          and source_id = ?
        """,
        (str(duplicate_row["id"]),),
    ).fetchone()
    assert evidence_count["count"] == 0, evidence_count


def test_finnhub_financial_history_and_hk_symbols(
    conn,
    insert_finnhub_financial_snapshot,
    normalize_finnhub_symbols,
    upsert_finnhub_symbol,
) -> None:
    assert normalize_finnhub_symbols(["00700.HK", "AAPL", "600519.SH"]) == ["0700.HK", "AAPL"]
    profile = {
        "name": "Tencent Holdings",
        "currency": "HKD",
        "exchange": "HKEX",
        "finnhubIndustry": "Interactive Media",
    }
    upsert_finnhub_symbol(conn, "0700.HK", profile)
    insert_finnhub_financial_snapshot(
        conn,
        "0700.HK",
        {
            "metric": {
                "revenueGrowthTTMYoy": "12.4",
                "roeTTM": "21.3",
                "fcfMarginTTM": "18.6",
                "totalDebt/totalAssetsAnnual": "14.2",
                "grossMarginTTM": "49.8",
                "netProfitMarginTTM": "24.1",
            },
            "series": {},
        },
        profile,
    )
    symbol = conn.execute("select market, currency from symbols where symbol = '0700.HK'").fetchone()
    assert symbol["market"] == "HK", symbol
    assert symbol["currency"] == "HKD", symbol
    row = conn.execute(
        """
        select *
        from financial_metrics_history
        where symbol = '0700.HK' and provider = 'finnhub-financial'
        """
    ).fetchone()
    assert row["revenue_growth"] == 12.4, row
    assert row["roe"] == 21.3, row
    assert row["fcf_margin"] == 18.6, row


def financial_metric_row(conn, symbol: str, period: str, provider: str):
    row = conn.execute(
        """
        select *
        from financial_metrics_history
        where symbol = ? and report_period = ? and provider = ?
        """,
        (symbol, period, provider),
    ).fetchone()
    assert row is not None, (symbol, period, provider)
    return row


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
