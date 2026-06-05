from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any, Callable

from fastapi import HTTPException

from .data_sources import (
    DEFAULT_ACCOUNT_ID,
    SOURCE_KIND_LABELS,
    alpha_vantage_token,
    finnhub_token,
    list_data_sources,
    tushare_token,
)
from .filings import published_at_sort_value, search_filing_documents
from .providers import FinnhubClient, FinnhubError, TushareClient, TushareError
from .providers.akshare_provider import query_akshare_capability
from .providers.alpha_vantage import AlphaVantageError, query_alpha_vantage_capability
from .providers.tushare import financial_date_window, recent_tushare_date_window
from .symbol_resolver import resolve_symbol


MAX_TEST_ROWS = 100


def filing_params(default_days: int = 90, default_limit: int = 20) -> list[dict[str, Any]]:
    return [
        {"name": "start_date", "label": "开始日期", "kind": "date", "default": iso_days_ago(default_days)},
        {"name": "end_date", "label": "结束日期", "kind": "date", "default": date.today().isoformat()},
        {"name": "keyword", "label": "关键词", "kind": "str", "default": ""},
        {"name": "limit", "label": "返回条数", "kind": "int", "default": default_limit},
    ]


def market_params() -> list[dict[str, Any]]:
    return [
        {"name": "start_date", "label": "开始日期", "kind": "date", "default": iso_days_ago(120)},
        {"name": "end_date", "label": "结束日期", "kind": "date", "default": date.today().isoformat()},
        {"name": "limit", "label": "返回条数", "kind": "int", "default": 20},
    ]


def financial_params() -> list[dict[str, Any]]:
    return [
        {"name": "start_date", "label": "开始日期", "kind": "date", "default": iso_days_ago(760)},
        {"name": "end_date", "label": "结束日期", "kind": "date", "default": date.today().isoformat()},
        {"name": "limit", "label": "返回条数", "kind": "int", "default": 20},
    ]


def news_params() -> list[dict[str, Any]]:
    return [
        {"name": "start_date", "label": "开始日期", "kind": "date", "default": iso_days_ago(7)},
        {"name": "end_date", "label": "结束日期", "kind": "date", "default": date.today().isoformat()},
        {"name": "keyword", "label": "关键词", "kind": "str", "default": ""},
        {"name": "limit", "label": "返回条数", "kind": "int", "default": 20},
    ]


def iso_days_ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


OFFICIAL_FILING_TESTS = [
    {
        "id": "filing-cninfo",
        "label": "CNINFO 公告",
        "provider": "cninfo",
        "market": "A",
        "source_kind": "filing",
        "description": "巨潮资讯公告查询，适合 A 股公告镜像核验。",
        "default_symbol": "002594.SZ",
        "requires_key": False,
        "implemented": True,
        "params": filing_params(),
    },
    {
        "id": "filing-sse",
        "label": "SSE 上交所公告",
        "provider": "sse",
        "market": "A",
        "source_kind": "filing",
        "description": "上海证券交易所上市公司公告查询。",
        "default_symbol": "600519.SH",
        "requires_key": False,
        "implemented": True,
        "params": filing_params(),
    },
    {
        "id": "filing-szse",
        "label": "SZSE 深交所公告",
        "provider": "szse",
        "market": "A",
        "source_kind": "filing",
        "description": "深圳证券交易所上市公司公告查询。",
        "default_symbol": "002594.SZ",
        "requires_key": False,
        "implemented": True,
        "params": filing_params(),
    },
    {
        "id": "filing-hkexnews",
        "label": "HKEXnews 公告",
        "provider": "hkexnews",
        "market": "HK",
        "source_kind": "filing",
        "description": "港交所披露易公告查询。",
        "default_symbol": "0700.HK",
        "requires_key": False,
        "implemented": True,
        "params": filing_params(default_days=30, default_limit=20),
    },
]


SOURCE_TEST_OVERRIDES: dict[str, dict[str, Any]] = {
    "cn-akshare-market": {
        "id": "source-cn-akshare-market",
        "label": "AKShare A股行情",
        "provider": "akshare",
        "market": "A",
        "source_kind": "market",
        "description": "AKShare A 股历史行情小样本测试。",
        "default_symbol": "600519.SH",
        "requires_key": False,
        "implemented": True,
        "params": market_params(),
    },
    "cn-tushare-market": {
        "id": "source-cn-tushare-market",
        "label": "Tushare A股行情",
        "provider": "tushare",
        "market": "A",
        "source_kind": "market",
        "description": "Tushare daily + daily_basic 小样本测试。",
        "default_symbol": "600519.SH",
        "requires_key": True,
        "implemented": True,
        "params": market_params(),
    },
    "cn-tushare-financial": {
        "id": "source-cn-tushare-financial",
        "label": "Tushare 财务指标",
        "provider": "tushare",
        "market": "A",
        "source_kind": "financial",
        "description": "Tushare fina_indicator + income 小样本测试。",
        "default_symbol": "600519.SH",
        "requires_key": True,
        "implemented": True,
        "params": financial_params(),
    },
    "cn-exchange-filings": {
        "id": "source-cn-exchange-filings",
        "label": "A股公告自动源",
        "provider": "cninfo_sse_szse",
        "market": "A",
        "source_kind": "filing",
        "description": "按代码后缀自动选择上交所、深交所或 CNINFO。",
        "default_symbol": "600519.SH",
        "requires_key": False,
        "implemented": True,
        "params": filing_params(),
    },
    "hk-hkexnews-filings": {
        "id": "source-hk-hkexnews-filings",
        "label": "HKEXnews 公告",
        "provider": "hkexnews",
        "market": "HK",
        "source_kind": "filing",
        "description": "港交所披露易公告查询。",
        "default_symbol": "0700.HK",
        "requires_key": False,
        "implemented": True,
        "params": filing_params(default_days=30, default_limit=20),
    },
    "us-alpha-vantage-market": {
        "id": "source-us-alpha-vantage-market",
        "label": "Alpha Vantage 美股报价",
        "provider": "alpha_vantage",
        "market": "US",
        "source_kind": "market",
        "description": "Alpha Vantage GLOBAL_QUOTE 测试。",
        "default_symbol": "AAPL",
        "requires_key": True,
        "implemented": True,
        "params": [{"name": "limit", "label": "返回行数", "kind": "int", "default": 10}],
    },
    "us-alpha-vantage-financial": {
        "id": "source-us-alpha-vantage-financial",
        "label": "Alpha Vantage 公司概览",
        "provider": "alpha_vantage",
        "market": "US",
        "source_kind": "financial",
        "description": "Alpha Vantage OVERVIEW 基本面字段测试。",
        "default_symbol": "AAPL",
        "requires_key": True,
        "implemented": True,
        "params": [{"name": "limit", "label": "返回行数", "kind": "int", "default": 10}],
    },
    "us-alpha-vantage-news": {
        "id": "source-us-alpha-vantage-news",
        "label": "Alpha Vantage 新闻情绪",
        "provider": "alpha_vantage",
        "market": "US",
        "source_kind": "news",
        "description": "Alpha Vantage NEWS_SENTIMENT 测试。",
        "default_symbol": "AAPL",
        "requires_key": True,
        "implemented": True,
        "params": news_params(),
    },
    "us-finnhub-market": {
        "id": "source-us-finnhub-market",
        "label": "Finnhub 美股报价",
        "provider": "finnhub",
        "market": "US",
        "source_kind": "market",
        "description": "Finnhub quote 测试。",
        "default_symbol": "AAPL",
        "requires_key": True,
        "implemented": True,
        "params": [{"name": "limit", "label": "返回行数", "kind": "int", "default": 10}],
    },
    "us-finnhub-financial": {
        "id": "source-us-finnhub-financial",
        "label": "Finnhub 基本面",
        "provider": "finnhub",
        "market": "US",
        "source_kind": "financial",
        "description": "Finnhub profile + stock/metric 测试。",
        "default_symbol": "AAPL",
        "requires_key": True,
        "implemented": True,
        "params": [{"name": "limit", "label": "返回行数", "kind": "int", "default": 20}],
    },
    "us-finnhub-news": {
        "id": "source-us-finnhub-news",
        "label": "Finnhub 公司新闻",
        "provider": "finnhub",
        "market": "US",
        "source_kind": "news",
        "description": "Finnhub company-news 最近窗口测试。",
        "default_symbol": "AAPL",
        "requires_key": True,
        "implemented": True,
        "params": news_params(),
    },
}


def data_source_test_catalog(conn: sqlite3.Connection, account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    source_payload = list_data_sources(conn, account_id)
    source_by_id = {item["id"]: item for item in source_payload["sources"]}
    tests: list[dict[str, Any]] = []

    for item in OFFICIAL_FILING_TESTS:
        tests.append(normalize_test_item(dict(item), source=None, account_id=account_id))

    for source in source_payload["sources"]:
        spec = SOURCE_TEST_OVERRIDES.get(source["id"])
        if not spec:
            spec = fallback_source_test(source)
        tests.append(normalize_test_item(dict(spec), source=source, account_id=account_id))

    return {
        "mode": "data-source-test-catalog",
        "account_id": account_id,
        "count": len(tests),
        "sources": source_payload["sources"],
        "tests": tests,
        "defaults": {
            "symbol": "600519.SH",
            "start_date": iso_days_ago(90),
            "end_date": date.today().isoformat(),
            "limit": 20,
        },
        "source_summary": source_payload.get("summary"),
        "source_by_id": source_by_id,
    }


def normalize_test_item(
    spec: dict[str, Any],
    *,
    source: dict[str, Any] | None,
    account_id: str,
) -> dict[str, Any]:
    requires_key = bool(source["requires_key"]) if source else bool(spec.get("requires_key"))
    configured = bool(source["configured"]) if source else not requires_key
    enabled = bool(source["enabled"]) if source else True
    implemented = bool(spec.get("implemented", True))
    active = enabled and configured and implemented
    source_kind = spec.get("source_kind") or (source.get("source_kind") if source else "")
    return {
        **spec,
        "source_id": source["id"] if source else spec.get("source_id", ""),
        "source_kind": source_kind,
        "source_kind_label": SOURCE_KIND_LABELS.get(source_kind, source_kind),
        "requires_key": requires_key,
        "configured": configured,
        "enabled": enabled,
        "active": active,
        "implemented": implemented,
        "credential_hint": source.get("credential_hint", "") if source else "",
        "status": test_status(enabled, configured, implemented),
        "account_id": account_id,
    }


def test_status(enabled: bool, configured: bool, implemented: bool) -> str:
    if not implemented:
        return "待接入"
    if not enabled:
        return "未启用"
    if not configured:
        return "需配置 key"
    return "可测试"


def fallback_source_test(source: dict[str, Any]) -> dict[str, Any]:
    implemented = str(source["provider"]).startswith("mock_")
    default_symbol = "0700.HK" if source["market"] == "HK" else "AAPL" if source["market"] == "US" else "600519.SH"
    return {
        "id": f"source-{source['id']}",
        "label": source["label"],
        "provider": source["provider"],
        "market": source["market"],
        "source_kind": source["source_kind"],
        "description": "本地 mock provider 快照测试。" if implemented else "该数据源暂未接入独立测试调用。",
        "default_symbol": default_symbol,
        "requires_key": bool(source["requires_key"]),
        "implemented": implemented,
        "params": [{"name": "limit", "label": "返回条数", "kind": "int", "default": 10}],
    }


def run_data_source_test(
    conn: sqlite3.Connection,
    *,
    test_id: str,
    symbol: str = "",
    account_id: str = DEFAULT_ACCOUNT_ID,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tests = {item["id"]: item for item in data_source_test_catalog(conn, account_id)["tests"]}
    test = tests.get(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="data source test not found")
    if not test["implemented"]:
        raise HTTPException(status_code=400, detail=f"{test['label']} 暂未接入独立测试调用")
    if test["requires_key"] and not test["configured"]:
        raise HTTPException(status_code=400, detail=f"{test['label']} 需要先在设置页配置 key")

    clean_params = dict(params or {})
    symbol_input = (symbol or test.get("default_symbol") or "").strip()
    resolved = resolve_symbol(conn, symbol_input, test.get("market") or "all")
    clean_symbol = str(resolved["symbol"]) if resolved else symbol_input
    runner = runner_for_test(test_id, test)
    try:
        result = runner(conn, test, clean_symbol, account_id, clean_params)
    except HTTPException:
        raise
    except (AlphaVantageError, FinnhubError, TushareError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "mode": "data-source-test",
        "account_id": account_id,
        "test": test,
        "request": {
            "test_id": test_id,
            "symbol": clean_symbol,
            "symbol_input": symbol_input,
            "resolved_symbol": clean_symbol if resolved else None,
            "params": clean_params,
        },
        "result": result,
    }


def runner_for_test(test_id: str, test: dict[str, Any]) -> Callable[[sqlite3.Connection, dict[str, Any], str, str, dict[str, Any]], dict[str, Any]]:
    if test_id in {"filing-cninfo", "filing-sse", "filing-szse", "filing-hkexnews", "source-cn-exchange-filings", "source-hk-hkexnews-filings"}:
        return run_filing_test
    if test_id == "source-cn-akshare-market":
        return run_akshare_market_test
    if test_id == "source-cn-tushare-market":
        return run_tushare_market_test
    if test_id == "source-cn-tushare-financial":
        return run_tushare_financial_test
    if test_id.startswith("source-us-alpha-vantage-"):
        return run_alpha_vantage_test
    if test_id.startswith("source-us-finnhub-"):
        return run_finnhub_test
    if test_id.startswith("source-") and str(test.get("provider", "")).startswith("mock_"):
        return run_mock_source_test
    raise HTTPException(status_code=400, detail=f"{test['label']} 暂未接入独立测试调用")


def run_filing_test(
    conn: sqlite3.Connection,
    test: dict[str, Any],
    symbol: str,
    account_id: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    source = {
        "filing-cninfo": "cninfo",
        "filing-sse": "sse",
        "filing-szse": "szse",
        "filing-hkexnews": "hkexnews",
        "source-cn-exchange-filings": "auto",
        "source-hk-hkexnews-filings": "hkexnews",
    }[test["id"]]
    limit = int_param(params, "limit", 20)
    payload = search_filing_documents(
        symbol=symbol,
        source=source,
        start_date=str_param(params, "start_date", iso_days_ago(90)),
        end_date=str_param(params, "end_date", date.today().isoformat()),
        keyword=str_param(params, "keyword", ""),
        page_size=limit,
    )
    rows = [
        {
            "source": item.get("source", ""),
            "published_at": item.get("published_at", ""),
            "stock_code": item.get("stock_code", ""),
            "company": item.get("company", ""),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
        }
        for item in payload.get("documents", [])
    ]
    rows.sort(key=lambda item: published_at_sort_value(item.get("published_at")), reverse=True)
    result = table_result(rows, total=payload.get("count"), raw=payload)
    result["errors"] = payload.get("errors", [])
    return result


def run_akshare_market_test(
    conn: sqlite3.Connection,
    test: dict[str, Any],
    symbol: str,
    account_id: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    query = {
        "symbol": symbol,
        "period": "daily",
        "start_date": compact_date(str_param(params, "start_date", iso_days_ago(120))),
        "end_date": compact_date(str_param(params, "end_date", date.today().isoformat())),
        "adjust": "qfq",
        "limit": int_param(params, "limit", 20),
    }
    payload = query_akshare_capability("stock_a_hist", query)
    return normalize_provider_payload(payload)


def run_tushare_market_test(
    conn: sqlite3.Connection,
    test: dict[str, Any],
    symbol: str,
    account_id: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    token = require_token(tushare_token(conn, account_id), "Tushare token 未配置")
    client = TushareClient(token)
    ts_code = normalize_tushare_symbol(symbol)
    start, end = tushare_window(params, default_days=30)
    daily = client.daily(ts_code, start, end)
    daily_basic = client.daily_basic(ts_code, start, end)
    rows = prefix_rows(daily[: int_param(params, "limit", 20)], "daily")
    rows.extend(prefix_rows(daily_basic[: int_param(params, "limit", 20)], "daily_basic"))
    return table_result(rows, total=len(rows), raw={"daily": daily, "daily_basic": daily_basic})


def run_tushare_financial_test(
    conn: sqlite3.Connection,
    test: dict[str, Any],
    symbol: str,
    account_id: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    token = require_token(tushare_token(conn, account_id), "Tushare token 未配置")
    client = TushareClient(token)
    ts_code = normalize_tushare_symbol(symbol)
    start, end = tushare_window(params, default_days=760, fallback=financial_date_window())
    indicator = client.fina_indicator(ts_code, start, end)
    income = client.income(ts_code, start, end)
    limit = int_param(params, "limit", 20)
    rows = prefix_rows(indicator[:limit], "fina_indicator")
    rows.extend(prefix_rows(income[:limit], "income"))
    return table_result(rows, total=len(rows), raw={"fina_indicator": indicator, "income": income})


def run_alpha_vantage_test(
    conn: sqlite3.Connection,
    test: dict[str, Any],
    symbol: str,
    account_id: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    api_key = require_token(alpha_vantage_token(conn, account_id), "Alpha Vantage key 未配置")
    limit = int_param(params, "limit", 20)
    if test["id"].endswith("-market"):
        payload = query_alpha_vantage_capability("global_quote", {"symbol": symbol, "return_limit": limit}, api_key=api_key)
    elif test["id"].endswith("-financial"):
        payload = query_alpha_vantage_capability("company_overview", {"symbol": symbol, "return_limit": limit}, api_key=api_key)
    else:
        payload = query_alpha_vantage_capability(
            "news_sentiment",
            {
                "tickers": symbol,
                "sort": "LATEST",
                "limit": limit,
                "return_limit": limit,
            },
            api_key=api_key,
        )
    return normalize_provider_payload(payload)


def run_finnhub_test(
    conn: sqlite3.Connection,
    test: dict[str, Any],
    symbol: str,
    account_id: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    token = require_token(finnhub_token(conn, account_id), "Finnhub key 未配置")
    client = FinnhubClient(token)
    if test["id"].endswith("-market"):
        payload = client.quote(symbol)
        rows = [payload]
    elif test["id"].endswith("-financial"):
        profile = client.company_profile(symbol)
        metrics = client.basic_financials(symbol)
        rows = [{"section": "profile", **profile}, {"section": "metric", **(metrics.get("metric") or {})}]
        payload = {"profile": profile, "metrics": metrics}
    else:
        start, end = news_window(params)
        payload = client.company_news(symbol, start, end)
        rows = payload[: int_param(params, "limit", 20)]
    return table_result(rows, raw=payload)


def run_mock_source_test(
    conn: sqlite3.Connection,
    test: dict[str, Any],
    symbol: str,
    account_id: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    from .stocks import all_stock_payloads

    rows = all_stock_payloads(conn)
    normalized = symbol.strip().upper()
    query = symbol.strip().lower()
    if normalized:
        rows = [
            row
            for row in rows
            if row["symbol"].upper() == normalized
            or row["symbol"].upper().startswith(normalized)
            or query in row["name"].lower()
        ]
    if test.get("market"):
        rows = [row for row in rows if row["market"] == test["market"]]
    limit = int_param(params, "limit", 10)
    compact_rows = [
        {
            "symbol": row["symbol"],
            "name": row["name"],
            "market": row["market"],
            "price": row["price"],
            "change": row["change"],
            "score": row["score"],
            "truthScore": row["truthScore"],
            "sourceStatus": row.get("sourceStatus"),
        }
        for row in rows[:limit]
    ]
    return table_result(compact_rows, total=len(rows), raw={"provider": test.get("provider"), "rows": rows[:limit]})


def normalize_provider_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, dict) and ArrayLikeRows(result.get("rows")):
        return {
            "type": "table",
            "columns": result.get("columns") or columns_for_rows(result.get("rows", [])),
            "rows": result.get("rows", []),
            "returned_rows": result.get("returned_rows", len(result.get("rows", []))),
            "total_rows": result.get("total_rows", len(result.get("rows", []))),
            "raw": payload,
        }
    if isinstance(result, dict) and "value" in result:
        value = result["value"]
        rows = [value] if isinstance(value, dict) else [{"value": value}]
        return table_result(rows, raw=payload)
    return table_result([payload], raw=payload)


def ArrayLikeRows(value: Any) -> bool:
    return isinstance(value, list)


def table_result(rows: list[dict[str, Any]], total: int | None = None, raw: Any | None = None) -> dict[str, Any]:
    clean_rows = [sanitize_row(row) for row in rows]
    return {
        "type": "table",
        "columns": columns_for_rows(clean_rows),
        "rows": clean_rows,
        "returned_rows": len(clean_rows),
        "total_rows": total if total is not None else len(clean_rows),
        "raw": raw if raw is not None else clean_rows,
    }


def columns_for_rows(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            clean[str(key)] = value
        else:
            clean[str(key)] = str(value)
    return clean


def str_param(params: dict[str, Any], key: str, default: str) -> str:
    value = params.get(key, default)
    return str(value).strip() if value not in (None, "") else default


def int_param(params: dict[str, Any], key: str, default: int) -> int:
    value = params.get(key, default)
    try:
        return max(1, min(int(value), MAX_TEST_ROWS))
    except (TypeError, ValueError):
        return default


def compact_date(value: str) -> str:
    return value.replace("-", "")


def tushare_window(
    params: dict[str, Any],
    *,
    default_days: int,
    fallback: tuple[str, str] | None = None,
) -> tuple[str, str]:
    if params.get("start_date") or params.get("end_date"):
        return compact_date(str_param(params, "start_date", iso_days_ago(default_days))), compact_date(
            str_param(params, "end_date", date.today().isoformat())
        )
    return fallback or recent_tushare_date_window(default_days)


def news_window(params: dict[str, Any]) -> tuple[date, date]:
    start = date.fromisoformat(str_param(params, "start_date", iso_days_ago(7)))
    end = date.fromisoformat(str_param(params, "end_date", date.today().isoformat()))
    return start, end


def normalize_tushare_symbol(symbol: str) -> str:
    clean = symbol.strip().upper()
    if clean.endswith((".SH", ".SZ", ".BJ")):
        return clean
    code = clean.split(".")[0]
    if code.startswith("6"):
        return f"{code}.SH"
    if code.startswith(("0", "2", "3")):
        return f"{code}.SZ"
    if code.startswith(("4", "8", "9")):
        return f"{code}.BJ"
    return clean


def prefix_rows(rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    return [{"source": source, **row} for row in rows]


def require_token(token: str, message: str) -> str:
    if not token:
        raise HTTPException(status_code=400, detail=message)
    return token
