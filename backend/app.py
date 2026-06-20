from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import BackgroundTasks, Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .accounts import add_account_trade, fetch_account, favorites_for_account, list_accounts, set_account_favorite, trades_for_account
from .analysis import create_anomaly_run, latest_stock_analysis, shared_cache_summary
from .backtesting import run_backtest
from .data_quality import health_payload, refresh_payload
from .data_source_tests import data_source_test_catalog, run_data_source_test
from .data_sources import DEFAULT_ACCOUNT_ID, alpha_vantage_token, list_data_sources, update_data_source
from .db import ROOT_DIR, get_db, init_db
from .finnhub_service import finnhub_status, refresh_finnhub_data
from .filings import filing_sources_payload, search_filing_documents
from .history import (
    create_a_share_filings_backfill_job,
    create_baostock_backfill_job,
    create_baostock_financial_backfill_job,
    ensure_query_data,
    ingestion_run_payload,
    refresh_baostock_data,
    refresh_market_data_baostock_first_batch,
    refresh_stock_detail_data,
    run_a_share_filings_backfill_job,
    run_baostock_backfill_job,
    run_baostock_financial_backfill_job,
    screen_from_database,
    warehouse_summary,
)
from .iwencai_recall import iwencai_recall_status, search_iwencai_recall, sync_iwencai_recall_index
from .portfolio import account_portfolio, refresh_mock_prices, symbols_for_account
from .providers.iwencai_profile import refresh_iwencai_profile_for_symbol
from .providers.akshare_provider import (
    akshare_status,
    index_spot,
    list_akshare_capabilities,
    query_akshare_capability,
    search_akshare_symbols,
    stock_history,
    stock_spot,
)
from .providers.alpha_vantage import (
    AlphaVantageError,
    alpha_vantage_company_overview,
    alpha_vantage_config_status,
    alpha_vantage_financials,
    alpha_vantage_quote,
    alpha_vantage_time_series,
    list_alpha_vantage_capabilities,
    mask_api_key,
    query_alpha_vantage_capability,
    search_alpha_vantage_symbols,
)
from .schemas import (
    AnomalyInput,
    BacktestInput,
    CommunityCrawlInput,
    CommunitySentimentCycleInput,
    DataRefreshInput,
    DataSourceTestInput,
    DataSourceUpdate,
    FavoriteToggle,
    SearchHistoryInput,
    ScreenerInput,
    SentimentRefreshInput,
    TradeInput,
)
from .search_history import list_search_history, record_search
from .sentiment import (
    community_daily_payload,
    crawl_community_for_symbols,
    refresh_sentiment,
    run_community_sentiment_cycle,
    sentiment_payload,
    sentiment_status,
)
from .stock_detail import stock_detail_payload
from .stocks import all_stock_payloads, run_screener, search_stocks, stock_memory
from .symbol_resolver import normalize_symbol_query, resolve_symbol
from .tushare_service import refresh_tushare_data, tushare_status


app = FastAPI(title="聚宝盆 Data Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def static_file_response(path: str) -> FileResponse:
    return FileResponse(
        ROOT_DIR / path,
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def api_health(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    with get_db() as conn:
        payload = health_payload()
        payload["tushare"] = tushare_status(conn, account_id)
        payload["finnhub"] = finnhub_status(conn, account_id)
        return payload


@app.get("/api/bootstrap")
def bootstrap(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    with get_db() as conn:
        account = fetch_account(conn, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="account not found")

        portfolio = account_portfolio(conn, account_id)
        return {
            "account": account,
            "accounts": list_accounts(conn),
            "favorites": favorites_for_account(conn, account_id),
            "trades": trades_for_account(conn, account_id),
            "portfolio": portfolio,
            "shared_cache": shared_cache_summary(conn),
            "data_sources": list_data_sources(conn, account_id),
            "data_boundary": {
                "shared": [
                    "symbols",
                    "market_snapshots",
                    "financial_snapshots",
                    "news_items",
                    "claims",
                    "factor_runs",
                    "stock_analysis_runs",
                    "anomaly_runs",
                    "stock_memories",
                ],
                "private": [
                    "account_favorites",
                    "account_trades",
                    "account_positions_cache",
                    "data_source_account_settings",
                    "data_source_credentials",
                    "search_history",
                ],
            },
        }


@app.get("/api/analysis/stocks/{symbol}")
def stock_analysis(symbol: str) -> dict[str, Any]:
    with get_db() as conn:
        return latest_stock_analysis(conn, symbol)


@app.post("/api/analysis/anomalies")
def create_anomaly(payload: AnomalyInput) -> dict[str, Any]:
    with get_db() as conn:
        return create_anomaly_run(conn, payload)


@app.get("/api/sentiment/status")
def api_sentiment_status() -> dict[str, Any]:
    with get_db() as conn:
        return sentiment_status(conn)


@app.get("/api/sentiment/stocks/{symbol}")
def api_stock_sentiment(
    symbol: str,
    days: int = Query(30, ge=1, le=365),
    evidence_limit: int = Query(30, ge=1, le=200),
) -> dict[str, Any]:
    with get_db() as conn:
        return sentiment_payload(conn, symbol, days=days, evidence_limit=evidence_limit)


@app.get("/api/sentiment/community/daily/{symbol}")
def api_community_daily_sentiment(
    symbol: str,
    days: int = Query(30, ge=1, le=365),
) -> dict[str, Any]:
    with get_db() as conn:
        return community_daily_payload(conn, symbol, days=days)


@app.post("/api/sentiment/refresh")
def api_refresh_sentiment(payload: SentimentRefreshInput | None = Body(default=None)) -> dict[str, Any]:
    payload = payload or SentimentRefreshInput()
    with get_db() as conn:
        return refresh_sentiment(
            conn,
            payload.symbols,
            days=payload.days,
            use_llm=payload.use_llm,
            crawl_community=payload.crawl_community,
            analyze_filing_news=payload.analyze_filing_news,
            community_limit=payload.community_limit,
            evidence_limit=payload.evidence_limit,
            account_id=payload.account_id or None,
        )


@app.post("/api/sentiment/community/cycle")
def api_community_sentiment_cycle(payload: CommunitySentimentCycleInput | None = Body(default=None)) -> dict[str, Any]:
    payload = payload or CommunitySentimentCycleInput()
    with get_db() as conn:
        return run_community_sentiment_cycle(
            conn,
            symbols=payload.symbols,
            use_llm=payload.use_llm,
            community_limit=payload.community_limit,
            evidence_limit=payload.evidence_limit,
            analysis_days=payload.analysis_days,
            retention_days=payload.retention_days,
            refresh_market=payload.refresh_market,
            refresh_filings=payload.refresh_filings,
            market_days=payload.market_days,
            account_id=payload.account_id or None,
            favorites_only=payload.favorites_only,
            cycle_timeout_seconds=payload.cycle_timeout_seconds,
        )


@app.post("/api/community/crawl")
def api_crawl_community(payload: CommunityCrawlInput) -> dict[str, Any]:
    with get_db() as conn:
        return crawl_community_for_symbols(
            conn,
            payload.symbols,
            source=payload.source,
            limit=payload.limit,
            timeout=payload.timeout,
            sleep_seconds=payload.sleep_seconds,
        )


@app.get("/api/stocks/search")
def api_stock_search(
    q: str = "",
    market: str = "all",
    account_id: str = DEFAULT_ACCOUNT_ID,
    record: bool = Query(True),
    limit: int = Query(0, ge=0, le=300),
) -> dict[str, Any]:
    with get_db() as conn:
        if record and q.strip():
            try:
                record_search(conn, account_id=account_id, surface="stock_analysis", query=q, metadata={"market": market})
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise
        result = search_stocks(conn, q, market, account_id, limit=limit)
        if record and q.strip() and not result["stocks"]:
            ingest_result = ensure_query_data(conn, q, market)
            result = search_stocks(conn, q, market, account_id, limit=limit)
            result["ingestion"] = ingest_result
        return result


@app.get("/api/stocks/{symbol}/detail")
def api_stock_detail(
    symbol: str,
    market: str = "all",
    limit: int = Query(520, ge=20, le=1200),
) -> dict[str, Any]:
    with get_db() as conn:
        return stock_detail_payload(conn, symbol, market=market, limit=limit)


@app.post("/api/stocks/{symbol}/refresh")
def api_refresh_stock_detail(
    symbol: str,
    market: str = "all",
    days: int = Query(260, ge=20, le=1200),
    quarters: int = Query(8, ge=1, le=20),
) -> dict[str, Any]:
    with get_db() as conn:
        return refresh_stock_detail_data(conn, symbol, market=market, days=days, quarters=quarters)


@app.post("/api/stocks/{symbol}/fundamental/iwencai/refresh")
def api_refresh_iwencai_fundamental(
    symbol: str,
    market: str = "all",
) -> dict[str, Any]:
    with get_db() as conn:
        symbol_row = resolve_symbol(conn, symbol, market)
        if not symbol_row:
            raise HTTPException(status_code=404, detail=f"symbol not found: {symbol}")
        try:
            return refresh_iwencai_profile_for_symbol(symbol_row)
        except Exception as exc:  # noqa: BLE001 - surface upstream/WAF errors to the UI.
            raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/iwencai-recall/status")
def api_iwencai_recall_status(include_qdrant: bool = True) -> dict[str, Any]:
    return iwencai_recall_status(include_qdrant=include_qdrant)


@app.get("/api/iwencai-recall/search")
def api_iwencai_recall_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    use_embedding: bool = True,
    include_stocks: bool = False,
    account_id: str = DEFAULT_ACCOUNT_ID,
    min_score: float | None = Query(None, ge=0.0, le=1.0),
) -> dict[str, Any]:
    result = search_iwencai_recall(q, limit=limit, use_embedding=use_embedding, min_score=min_score)
    if not include_stocks:
        return result
    symbols = [str(item["symbol"]).upper() for item in result.get("results", [])]
    if not symbols:
        result["stocks"] = []
        return result
    with get_db() as conn:
        payloads = all_stock_payloads(
            conn,
            account_id=account_id,
            include_universe=True,
            symbol_filter=symbols,
        )
        payloads_by_symbol = {item["symbol"]: item for item in payloads}
        for symbol in symbols:
            if symbol in payloads_by_symbol:
                continue
            search_result = search_stocks(conn, query=symbol, market="all", account_id=account_id, limit=1)
            if search_result["stocks"]:
                payloads_by_symbol[symbol] = search_result["stocks"][0]
    result["stocks"] = [payloads_by_symbol[symbol] for symbol in symbols if symbol in payloads_by_symbol]
    for item in result["results"]:
        symbol = str(item["symbol"]).upper()
        item["stock"] = payloads_by_symbol.get(symbol)
    return result


@app.post("/api/iwencai-recall/update")
def api_update_iwencai_recall(
    force: bool = False,
    dry_run: bool = False,
    batch_size: int = Query(64, ge=1, le=512),
) -> dict[str, Any]:
    try:
        return sync_iwencai_recall_index(force=force, dry_run=dry_run, batch_size=batch_size)
    except Exception as exc:  # noqa: BLE001 - expose missing Qdrant/BGE setup clearly.
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/stocks/search")
def stock_search(q: str = "", market: str = "all", account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    return api_stock_search(q, market, account_id)


@app.post("/api/screeners/run")
def api_run_screener(payload: ScreenerInput) -> dict[str, Any]:
    with get_db() as conn:
        rows = screen_from_database(
            conn,
            payload.market,
            payload.filter_ids,
            payload.mode,
            payload.natural_query,
            payload.industry,
        )
        row_symbols = [row["symbol"] for row in rows]
        payloads = all_stock_payloads(
            conn,
            account_id=payload.account_id,
            include_universe=True,
            symbol_filter=row_symbols,
        )
        payloads_by_symbol = {item["symbol"]: item for item in payloads}
        stocks = [payloads_by_symbol[row["symbol"]] for row in rows if row["symbol"] in payloads_by_symbol]
        return {
            "stocks": stocks,
            "rows": rows,
            "mode": "database-screener",
            "count": len(stocks),
            "applied_filters": payload.filter_ids,
            "filter_mode": payload.mode,
            "natural_query": payload.natural_query,
            "industry": payload.industry,
            "warehouse": warehouse_summary(conn),
        }


@app.get("/api/screeners/industries")
def api_screener_industries(market: str = "all") -> dict[str, Any]:
    normalized_market = market.strip().upper()
    params: list[Any] = []
    market_clause = ""
    if normalized_market != "ALL":
        market_clause = " and upper(market) = ?"
        params.extend([normalized_market, normalized_market])
    with get_db() as conn:
        rows = conn.execute(
            f"""
            with labels as (
              select symbol, trim(industry) as industry
              from symbols
              where trim(coalesce(industry, '')) != ''{market_clause}
              union
              select symbol, trim(sector) as industry
              from symbols
              where trim(coalesce(sector, '')) != ''{market_clause}
            )
            select industry, count(*) as count
            from labels
            group by industry
            order by count(*) desc, industry
            """,
            params,
        ).fetchall()
        return {"market": market, "industries": [dict(row) for row in rows]}


@app.post("/screeners/run")
def public_run_screener(payload: ScreenerInput) -> dict[str, Any]:
    return api_run_screener(payload)


@app.post("/api/backtests/run")
def api_run_backtest(payload: BacktestInput) -> dict[str, Any]:
    with get_db() as conn:
        return run_backtest(payload, conn)


@app.get("/api/memory/stocks/{symbol}")
def api_stock_memory(symbol: str) -> dict[str, Any]:
    with get_db() as conn:
        return stock_memory(conn, symbol)


@app.get("/memory/stocks/{symbol}")
def public_stock_memory(symbol: str) -> dict[str, Any]:
    return api_stock_memory(symbol)


@app.get("/api/data-sources")
def api_data_sources(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    with get_db() as conn:
        return list_data_sources(conn, account_id)


@app.get("/api/filings/sources")
def api_filing_sources() -> dict[str, Any]:
    return filing_sources_payload()


@app.get("/api/filings/search")
def api_filing_search(
    symbol: str = Query(..., min_length=1),
    source: str = "auto",
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str = "",
    category: str = "",
    account_id: str = DEFAULT_ACCOUNT_ID,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    timeout: int = Query(15, ge=3, le=60),
) -> dict[str, Any]:
    with get_db() as conn:
        resolved_symbol = normalize_symbol_query(conn, symbol)
        record_search(
            conn,
            account_id=account_id,
            surface="filings",
            query=symbol,
            metadata={"source": source, "resolved_symbol": resolved_symbol},
        )
        if keyword.strip():
            record_search(
                conn,
                account_id=account_id,
                surface="filing_keyword",
                query=keyword,
                metadata={"source": source, "symbol": resolved_symbol},
            )
    return search_filing_documents(
        symbol=resolved_symbol,
        source=source,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        category=category,
        page=page,
        page_size=page_size,
        timeout=timeout,
    )


@app.get("/api/data-source-tests/catalog")
def api_data_source_test_catalog(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    with get_db() as conn:
        return data_source_test_catalog(conn, account_id)


@app.get("/api/data-source-tests")
def api_data_source_test_catalog_alias(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    return api_data_source_test_catalog(account_id)


@app.post("/api/data-source-tests/run")
def api_run_data_source_test(payload: DataSourceTestInput) -> dict[str, Any]:
    with get_db() as conn:
        result = run_data_source_test(
            conn,
            test_id=payload.test_id,
            symbol=payload.symbol,
            account_id=payload.account_id,
            params=payload.params,
        )
        if payload.symbol.strip():
            record_search(
                conn,
                account_id=payload.account_id,
                surface="data_source_test_symbol",
                query=payload.symbol,
                metadata={
                    "test_id": payload.test_id,
                    "resolved_symbol": result.get("request", {}).get("resolved_symbol"),
                },
            )
        keyword = str(payload.params.get("keyword") or "")
        if keyword.strip():
            record_search(
                conn,
                account_id=payload.account_id,
                surface="data_source_test_keyword",
                query=keyword,
                metadata={"test_id": payload.test_id, "symbol": result.get("request", {}).get("symbol")},
            )
        return result


@app.put("/api/data-sources/{source_id}")
def api_update_data_source(source_id: str, payload: DataSourceUpdate, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    with get_db() as conn:
        return update_data_source(conn, source_id, payload, account_id)


@app.get("/api/search-history")
def api_search_history(account_id: str = DEFAULT_ACCOUNT_ID, surface: str = "", limit: int = Query(50, ge=1, le=120)) -> dict[str, Any]:
    with get_db() as conn:
        return list_search_history(conn, account_id=account_id, surface=surface, limit=limit)


@app.post("/api/search-history")
def api_record_search_history(payload: SearchHistoryInput) -> dict[str, Any]:
    with get_db() as conn:
        item = record_search(
            conn,
            account_id=payload.account_id,
            surface=payload.surface,
            query=payload.query,
            metadata=payload.metadata,
        )
        return {"mode": "account-search-history-recorded", "account_id": payload.account_id, "item": item}


@app.get("/api/data/tushare/status")
def api_tushare_status(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    with get_db() as conn:
        return tushare_status(conn, account_id)


@app.post("/api/data/tushare/refresh")
def api_refresh_tushare(payload: DataRefreshInput | None = Body(default=None)) -> dict[str, Any]:
    payload = payload or DataRefreshInput(provider="tushare")
    with get_db() as conn:
        return refresh_tushare_data(conn, payload.symbols, payload.refresh_universe, payload.account_id or DEFAULT_ACCOUNT_ID)


@app.post("/api/data/baostock/refresh")
def api_refresh_baostock(
    background_tasks: BackgroundTasks,
    payload: DataRefreshInput | None = Body(default=None),
) -> dict[str, Any]:
    payload = payload or DataRefreshInput(provider="baostock")
    with get_db() as conn:
        result = create_baostock_backfill_job(conn, payload.symbols, payload.refresh_universe)
    if not result.get("already_running"):
        background_tasks.add_task(run_baostock_backfill_job, result["run_id"], payload.symbols, payload.refresh_universe)
    return result


@app.post("/api/data/baostock/financials/refresh")
def api_refresh_baostock_financials(
    background_tasks: BackgroundTasks,
    payload: DataRefreshInput | None = Body(default=None),
) -> dict[str, Any]:
    payload = payload or DataRefreshInput(provider="baostock", scope="quarterly-financials")
    with get_db() as conn:
        result = create_baostock_financial_backfill_job(conn, payload.symbols, payload.refresh_universe)
    if not result.get("already_running"):
        background_tasks.add_task(run_baostock_financial_backfill_job, result["run_id"], payload.symbols, payload.refresh_universe)
    return result


@app.get("/api/data/jobs/{run_id}")
def api_data_job(run_id: int, include_symbols: bool = False, symbol_limit: int = Query(50, ge=0, le=500)) -> dict[str, Any]:
    with get_db() as conn:
        return ingestion_run_payload(conn, run_id, include_symbols=include_symbols, symbol_limit=symbol_limit)


@app.get("/api/data/warehouse/summary")
def api_warehouse_summary() -> dict[str, Any]:
    with get_db() as conn:
        return {"mode": "history-warehouse", "warehouse": warehouse_summary(conn)}


@app.get("/api/data/finnhub/status")
def api_finnhub_status(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    with get_db() as conn:
        return finnhub_status(conn, account_id)


@app.post("/api/data/finnhub/refresh")
def api_refresh_finnhub(payload: DataRefreshInput | None = Body(default=None)) -> dict[str, Any]:
    payload = payload or DataRefreshInput(provider="finnhub")
    with get_db() as conn:
        return refresh_finnhub_data(conn, payload.symbols, payload.account_id or DEFAULT_ACCOUNT_ID)


@app.get("/api/akshare/capabilities")
def api_akshare_capabilities() -> dict[str, Any]:
    return list_akshare_capabilities()


@app.get("/api/akshare/status")
def api_akshare_status() -> dict[str, Any]:
    return akshare_status()


@app.get("/api/akshare/query/{capability_id}")
def api_akshare_query(capability_id: str, request: Request) -> dict[str, Any]:
    params = dict(request.query_params)
    account_id = str(params.get("account_id", DEFAULT_ACCOUNT_ID))
    payload = query_akshare_capability(capability_id, params)
    with get_db() as conn:
        record_query_from_params(conn, account_id, "akshare", params, {"capability_id": capability_id})
    return payload


@app.get("/api/akshare/search")
def api_akshare_search(q: str = "", market: str = "all", limit: int = 50, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    with get_db() as conn:
        if q.strip():
            record_search(conn, account_id=account_id, surface="akshare", query=q, metadata={"market": market})
    return search_akshare_symbols(q, market, limit)


@app.get("/api/akshare/stocks/{market}/spot")
def api_akshare_stock_spot(market: str, request: Request) -> dict[str, Any]:
    return stock_spot(market, dict(request.query_params))


@app.get("/api/akshare/stocks/{market}/{symbol}/hist")
def api_akshare_stock_history(market: str, symbol: str, request: Request) -> dict[str, Any]:
    return stock_history(market, symbol, dict(request.query_params))


@app.get("/api/akshare/indices/spot")
def api_akshare_index_spot(request: Request) -> dict[str, Any]:
    return index_spot(dict(request.query_params))


@app.get("/api/alpha-vantage/status")
def api_alpha_vantage_status(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    status = alpha_vantage_config_status()
    api_key = alpha_vantage_key_for_account(account_id)
    if api_key:
        status["configured"] = True
        status["credential_hint"] = mask_api_key(api_key)
        status["note"] = "Alpha Vantage key 已通过环境变量、.env 或账户私有凭据配置。"
    return status


@app.get("/api/alpha-vantage/capabilities")
def api_alpha_vantage_capabilities(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    api_key = alpha_vantage_key_for_account(account_id)
    return list_alpha_vantage_capabilities(configured=bool(api_key), credential_hint=mask_api_key(api_key) if api_key else "")


@app.get("/api/alpha-vantage/query/{capability_id}")
def api_alpha_vantage_query(capability_id: str, request: Request) -> dict[str, Any]:
    params, api_key = alpha_vantage_params_for_request(request)
    payload = handle_alpha_vantage_error(lambda: query_alpha_vantage_capability(capability_id, params, api_key=api_key))
    account_id = str(request.query_params.get("account_id", DEFAULT_ACCOUNT_ID))
    with get_db() as conn:
        record_query_from_params(conn, account_id, "alpha_vantage", params, {"capability_id": capability_id})
    return payload


@app.get("/api/alpha-vantage/search")
def api_alpha_vantage_search(q: str = "", limit: int = 20, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    api_key = alpha_vantage_key_for_account(account_id)
    with get_db() as conn:
        if q.strip():
            record_search(conn, account_id=account_id, surface="alpha_vantage", query=q, metadata={"limit": limit})
    return handle_alpha_vantage_error(lambda: search_alpha_vantage_symbols(q, limit, api_key=api_key))


@app.get("/api/alpha-vantage/quote/{symbol}")
def api_alpha_vantage_quote(symbol: str, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    api_key = alpha_vantage_key_for_account(account_id)
    return handle_alpha_vantage_error(lambda: alpha_vantage_quote(symbol, api_key=api_key))


@app.get("/api/alpha-vantage/stocks/{symbol}/intraday")
def api_alpha_vantage_intraday(symbol: str, request: Request) -> dict[str, Any]:
    params, api_key = alpha_vantage_params_for_request(request)
    return handle_alpha_vantage_error(lambda: alpha_vantage_time_series(symbol, "intraday", params, api_key=api_key))


@app.get("/api/alpha-vantage/stocks/{symbol}/daily")
def api_alpha_vantage_daily(symbol: str, request: Request, adjusted: bool = False) -> dict[str, Any]:
    period = "daily_adjusted" if adjusted else "daily"
    params, api_key = alpha_vantage_params_for_request(request)
    params.pop("adjusted", None)
    return handle_alpha_vantage_error(lambda: alpha_vantage_time_series(symbol, period, params, api_key=api_key))


@app.get("/api/alpha-vantage/stocks/{symbol}/weekly")
def api_alpha_vantage_weekly(symbol: str, request: Request) -> dict[str, Any]:
    params, api_key = alpha_vantage_params_for_request(request)
    return handle_alpha_vantage_error(lambda: alpha_vantage_time_series(symbol, "weekly_adjusted", params, api_key=api_key))


@app.get("/api/alpha-vantage/stocks/{symbol}/monthly")
def api_alpha_vantage_monthly(symbol: str, request: Request) -> dict[str, Any]:
    params, api_key = alpha_vantage_params_for_request(request)
    return handle_alpha_vantage_error(lambda: alpha_vantage_time_series(symbol, "monthly_adjusted", params, api_key=api_key))


@app.get("/api/alpha-vantage/stocks/{symbol}/overview")
def api_alpha_vantage_overview(symbol: str, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    api_key = alpha_vantage_key_for_account(account_id)
    return handle_alpha_vantage_error(lambda: alpha_vantage_company_overview(symbol, api_key=api_key))


@app.get("/api/alpha-vantage/stocks/{symbol}/financials")
def api_alpha_vantage_financials(
    symbol: str,
    sections: str = "overview,income,balance,cash_flow,earnings",
    account_id: str = DEFAULT_ACCOUNT_ID,
) -> dict[str, Any]:
    api_key = alpha_vantage_key_for_account(account_id)
    return handle_alpha_vantage_error(lambda: alpha_vantage_financials(symbol, sections, api_key=api_key))


@app.get("/api/alpha-vantage/news-sentiment")
def api_alpha_vantage_news_sentiment(request: Request) -> dict[str, Any]:
    params, api_key = alpha_vantage_params_for_request(request)
    return handle_alpha_vantage_error(lambda: query_alpha_vantage_capability("news_sentiment", params, api_key=api_key))


@app.get("/api/alpha-vantage/etf/{symbol}/profile")
def api_alpha_vantage_etf_profile(symbol: str, request: Request) -> dict[str, Any]:
    params, api_key = alpha_vantage_params_for_request(request)
    params["symbol"] = symbol
    return handle_alpha_vantage_error(lambda: query_alpha_vantage_capability("etf_profile", params, api_key=api_key))


@app.get("/api/alpha-vantage/market-status")
def api_alpha_vantage_market_status(account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    api_key = alpha_vantage_key_for_account(account_id)
    return handle_alpha_vantage_error(lambda: query_alpha_vantage_capability("market_status", {}, api_key=api_key))


@app.get("/api/alpha-vantage/top-movers")
def api_alpha_vantage_top_movers(request: Request) -> dict[str, Any]:
    params, api_key = alpha_vantage_params_for_request(request)
    return handle_alpha_vantage_error(lambda: query_alpha_vantage_capability("top_gainers_losers", params, api_key=api_key))


@app.get("/api/alpha-vantage/listing-status")
def api_alpha_vantage_listing_status(request: Request) -> dict[str, Any]:
    params, api_key = alpha_vantage_params_for_request(request)
    return handle_alpha_vantage_error(lambda: query_alpha_vantage_capability("listing_status", params, api_key=api_key))


@app.get("/api/alpha-vantage/currency-exchange-rate")
def api_alpha_vantage_currency_exchange_rate(request: Request) -> dict[str, Any]:
    params, api_key = alpha_vantage_params_for_request(request)
    return handle_alpha_vantage_error(lambda: query_alpha_vantage_capability("currency_exchange_rate", params, api_key=api_key))


def record_query_from_params(
    conn: Any,
    account_id: str,
    surface: str,
    params: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    for key in ("q", "symbol", "keywords", "tickers", "topics"):
        value = str(params.get(key) or "").strip()
        if value:
            record_search(
                conn,
                account_id=account_id,
                surface=surface,
                query=value,
                metadata={**(metadata or {}), "param": key},
            )
            return


def alpha_vantage_params_for_request(request: Request) -> tuple[dict[str, Any], str]:
    params = dict(request.query_params)
    account_id = str(params.pop("account_id", DEFAULT_ACCOUNT_ID))
    return params, alpha_vantage_key_for_account(account_id)


def alpha_vantage_key_for_account(account_id: str = DEFAULT_ACCOUNT_ID) -> str:
    with get_db() as conn:
        return alpha_vantage_token(conn, account_id)


def handle_alpha_vantage_error(callback: Any) -> dict[str, Any]:
    try:
        return callback()
    except AlphaVantageError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "message": str(exc),
                "provider": "alpha_vantage",
                "payload": exc.payload,
            },
        ) from exc


@app.get("/api/accounts/{account_id}/portfolio")
def portfolio(account_id: str) -> dict[str, Any]:
    with get_db() as conn:
        return account_portfolio(conn, account_id)


@app.put("/api/accounts/{account_id}/favorites/{symbol}")
def set_favorite(account_id: str, symbol: str, payload: FavoriteToggle) -> dict[str, Any]:
    with get_db() as conn:
        favorites = set_account_favorite(conn, account_id, symbol.upper(), payload.favorite, payload.note)
        conn.commit()
    return {"account_id": account_id, "favorites": favorites}


@app.post("/api/accounts/{account_id}/trades")
def add_trade(account_id: str, payload: TradeInput) -> dict[str, Any]:
    with get_db() as conn:
        trade = add_account_trade(conn, account_id, payload)
        portfolio = account_portfolio(conn, account_id)
    return {"account_id": account_id, "trade": trade, "portfolio": portfolio}


@app.post("/api/data/refresh")
def refresh_data(
    background_tasks: BackgroundTasks,
    payload: DataRefreshInput | None = Body(default=None),
) -> dict[str, Any]:
    response = refresh_payload()
    payload = payload or DataRefreshInput()
    account_id = payload.account_id
    scope = payload.scope
    if payload.provider == "finnhub" or scope in {"finnhub", "us-real-data"}:
        with get_db() as conn:
            return refresh_finnhub_data(conn, payload.symbols, account_id or DEFAULT_ACCOUNT_ID)
    if payload.provider == "tushare" or scope in {"tushare", "real-data", "cn-real-data"}:
        with get_db() as conn:
            return refresh_tushare_data(conn, payload.symbols, payload.refresh_universe, account_id or DEFAULT_ACCOUNT_ID)
    if payload.provider == "akshare" or scope in {"akshare", "history", "a-share-history"}:
        with get_db() as conn:
            return refresh_market_data_baostock_first_batch(conn, payload.symbols, payload.refresh_universe)
    if payload.provider == "baostock" or scope in {"baostock", "history-backfill", "a-share-backfill"}:
        with get_db() as conn:
            result = create_baostock_backfill_job(conn, payload.symbols, payload.refresh_universe)
        if not result.get("already_running"):
            background_tasks.add_task(run_baostock_backfill_job, result["run_id"], payload.symbols, payload.refresh_universe)
        return result
    if payload.provider == "baostock-financial" or scope in {"baostock-financial", "quarterly-financials", "a-share-quarterly-financials"}:
        with get_db() as conn:
            result = create_baostock_financial_backfill_job(conn, payload.symbols, payload.refresh_universe)
        if not result.get("already_running"):
            background_tasks.add_task(run_baostock_financial_backfill_job, result["run_id"], payload.symbols, payload.refresh_universe)
        return result
    if payload.provider in {"cninfo_sse_szse", "cninfo", "sse", "szse"} or scope in {"filing", "filings", "a-share-filings", "cn-exchange-filings"}:
        source = payload.provider if payload.provider in {"cninfo", "sse", "szse"} else "all"
        with get_db() as conn:
            result = create_a_share_filings_backfill_job(conn, payload.symbols, payload.refresh_universe, source=source)
        if not result.get("already_running"):
            background_tasks.add_task(run_a_share_filings_backfill_job, result["run_id"], payload.symbols, payload.refresh_universe, source)
        return result
    if scope == "portfolio" and account_id:
        with get_db() as conn:
            updated_prices = refresh_mock_prices(symbols_for_account(conn, account_id))
            response["updated_prices"] = updated_prices
            response["portfolio"] = account_portfolio(conn, account_id)
    return response


@app.get("/")
def index() -> FileResponse:
    return static_file_response("index.html")


@app.get("/index.html")
def index_html() -> FileResponse:
    return static_file_response("index.html")


@app.get("/styles.css")
def styles() -> FileResponse:
    return static_file_response("styles.css")


@app.get("/app.js")
def app_js() -> FileResponse:
    return static_file_response("app.js")


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    return static_file_response("manifest.webmanifest")


@app.get("/service-worker.js")
def service_worker() -> FileResponse:
    return static_file_response("service-worker.js")


@app.get("/assets/app-icon.svg")
def app_icon() -> FileResponse:
    return static_file_response("assets/app-icon.svg")
