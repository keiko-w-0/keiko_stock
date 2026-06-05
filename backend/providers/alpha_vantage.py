from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ALPHA_VANTAGE_ENDPOINT = "https://www.alphavantage.co/query"
ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"
ENV_KEY_NAMES = ("ALPHA_VANTAGE_API_KEY", "ALPHAVANTAGE_API_KEY", "ALPHA_VANTAGE_KEY")
MAX_RETURN_ROWS = 5000


class AlphaVantageError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502, payload: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass(frozen=True)
class AVParam:
    name: str
    kind: str = "str"
    required: bool = False
    default: Any = None
    choices: tuple[Any, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class AVCapability:
    id: str
    category: str
    label: str
    function: str
    description: str
    params: tuple[AVParam, ...] = ()
    default_return_limit: int = 80
    examples: tuple[dict[str, Any], ...] = ()
    docs_url: str = "https://www.alphavantage.co/documentation/"
    datatype: str = "json"


CAPABILITY_GROUPS = {
    "search": "搜索/列表",
    "market": "行情/K线",
    "fundamental": "基本面",
    "news": "新闻情绪",
    "macro": "市场状态",
}


CAPABILITIES: tuple[AVCapability, ...] = (
    AVCapability(
        id="symbol_search",
        category="search",
        label="股票代码搜索",
        function="SYMBOL_SEARCH",
        description="按关键词搜索 Alpha Vantage 支持的股票、ETF 和其他证券代码。",
        params=(AVParam("keywords", required=True, description="关键词或代码，如 Apple、AAPL、NVIDIA"),),
        default_return_limit=20,
        examples=({"keywords": "AAPL"},),
    ),
    AVCapability(
        id="listing_status",
        category="search",
        label="美股上市/退市列表",
        function="LISTING_STATUS",
        description="返回 Alpha Vantage 覆盖的美国交易所上市或退市证券清单，CSV 接口。",
        params=(
            AVParam("date", default=lambda: date.today().isoformat(), description="YYYY-MM-DD"),
            AVParam("state", default="active", choices=("active", "delisted"), description="active 或 delisted"),
        ),
        default_return_limit=300,
        examples=({"state": "active"},),
        datatype="csv",
    ),
    AVCapability(
        id="global_quote",
        category="market",
        label="实时/最新报价",
        function="GLOBAL_QUOTE",
        description="返回单个代码的最新报价、成交量、上一交易日收盘和涨跌幅。",
        params=(AVParam("symbol", required=True, description="美股代码，如 AAPL 或 NVDA"),),
        default_return_limit=1,
        examples=({"symbol": "AAPL"},),
    ),
    AVCapability(
        id="intraday",
        category="market",
        label="盘中分钟线",
        function="TIME_SERIES_INTRADAY",
        description="分钟级历史行情，适合盘中刷新、短周期波动和成交量确认。",
        params=(
            AVParam("symbol", required=True, description="美股代码，如 AAPL"),
            AVParam("interval", default="5min", choices=("1min", "5min", "15min", "30min", "60min"), description="分钟周期"),
            AVParam("adjusted", kind="bool", default=True, description="是否使用复权分钟线"),
            AVParam("extended_hours", kind="bool", default=True, description="是否包含盘前/盘后"),
            AVParam("outputsize", default="compact", choices=("compact", "full"), description="compact 最近约 100 条，full 返回更多历史"),
        ),
        default_return_limit=120,
        examples=({"symbol": "AAPL", "interval": "5min", "outputsize": "compact"},),
    ),
    AVCapability(
        id="daily",
        category="market",
        label="日线行情",
        function="TIME_SERIES_DAILY",
        description="未复权日线行情，适合简单 K 线和技术指标。",
        params=(
            AVParam("symbol", required=True, description="美股代码，如 AAPL"),
            AVParam("outputsize", default="compact", choices=("compact", "full"), description="compact 最近约 100 天，full 返回完整历史"),
        ),
        default_return_limit=120,
        examples=({"symbol": "AAPL", "outputsize": "compact"},),
    ),
    AVCapability(
        id="daily_adjusted",
        category="market",
        label="复权日线行情",
        function="TIME_SERIES_DAILY_ADJUSTED",
        description="包含 adjusted close、股息和拆股系数的日线行情，适合收益率和回测；部分 key/套餐可能返回 premium 提示。",
        params=(
            AVParam("symbol", required=True, description="美股代码，如 AAPL"),
            AVParam("outputsize", default="compact", choices=("compact", "full"), description="compact 最近约 100 天，full 返回完整历史"),
        ),
        default_return_limit=120,
        examples=({"symbol": "AAPL", "outputsize": "compact"},),
    ),
    AVCapability(
        id="weekly_adjusted",
        category="market",
        label="复权周线行情",
        function="TIME_SERIES_WEEKLY_ADJUSTED",
        description="复权周线行情，适合中期趋势和波动回放。",
        params=(AVParam("symbol", required=True, description="美股代码，如 AAPL"),),
        default_return_limit=120,
        examples=({"symbol": "AAPL"},),
    ),
    AVCapability(
        id="monthly_adjusted",
        category="market",
        label="复权月线行情",
        function="TIME_SERIES_MONTHLY_ADJUSTED",
        description="复权月线行情，适合长期趋势和跨周期比较。",
        params=(AVParam("symbol", required=True, description="美股代码，如 AAPL"),),
        default_return_limit=120,
        examples=({"symbol": "AAPL"},),
    ),
    AVCapability(
        id="top_gainers_losers",
        category="market",
        label="美股涨跌幅榜",
        function="TOP_GAINERS_LOSERS",
        description="返回涨幅榜、跌幅榜和活跃成交榜。",
        default_return_limit=150,
        examples=({},),
    ),
    AVCapability(
        id="company_overview",
        category="fundamental",
        label="公司概览/估值",
        function="OVERVIEW",
        description="公司基础资料、估值、市值、分红、利润率、52 周价格区间等字段。",
        params=(AVParam("symbol", required=True, description="美股代码，如 AAPL"),),
        default_return_limit=1,
        examples=({"symbol": "AAPL"},),
    ),
    AVCapability(
        id="income_statement",
        category="fundamental",
        label="利润表",
        function="INCOME_STATEMENT",
        description="年度和季度利润表，用于收入、毛利、营业利润和净利润分析。",
        params=(AVParam("symbol", required=True, description="美股代码，如 AAPL"),),
        default_return_limit=12,
        examples=({"symbol": "AAPL"},),
    ),
    AVCapability(
        id="balance_sheet",
        category="fundamental",
        label="资产负债表",
        function="BALANCE_SHEET",
        description="年度和季度资产负债表，用于资产质量、现金、债务和权益结构分析。",
        params=(AVParam("symbol", required=True, description="美股代码，如 AAPL"),),
        default_return_limit=12,
        examples=({"symbol": "AAPL"},),
    ),
    AVCapability(
        id="cash_flow",
        category="fundamental",
        label="现金流量表",
        function="CASH_FLOW",
        description="年度和季度现金流量表，用于经营现金流、资本开支和自由现金流分析。",
        params=(AVParam("symbol", required=True, description="美股代码，如 AAPL"),),
        default_return_limit=12,
        examples=({"symbol": "AAPL"},),
    ),
    AVCapability(
        id="earnings",
        category="fundamental",
        label="每股收益",
        function="EARNINGS",
        description="年度和季度 EPS 历史及预期差字段。",
        params=(AVParam("symbol", required=True, description="美股代码，如 AAPL"),),
        default_return_limit=16,
        examples=({"symbol": "AAPL"},),
    ),
    AVCapability(
        id="etf_profile",
        category="fundamental",
        label="ETF Profile",
        function="ETF_PROFILE",
        description="ETF 基础信息、持仓、行业暴露和资产配置。",
        params=(AVParam("symbol", required=True, description="ETF 代码，如 SPY 或 QQQ"),),
        default_return_limit=80,
        examples=({"symbol": "SPY"},),
    ),
    AVCapability(
        id="news_sentiment",
        category="news",
        label="新闻情绪",
        function="NEWS_SENTIMENT",
        description="按 tickers/topics 拉取新闻、摘要、来源、整体情绪和 ticker 级情绪。",
        params=(
            AVParam("tickers", default="AAPL", description="逗号分隔代码，如 AAPL,NVDA"),
            AVParam("topics", default="", description="可选主题，如 technology,earnings"),
            AVParam("time_from", default="", description="可选起点，格式 YYYYMMDDTHHMM"),
            AVParam("time_to", default="", description="可选终点，格式 YYYYMMDDTHHMM"),
            AVParam("sort", default="LATEST", choices=("LATEST", "EARLIEST", "RELEVANCE"), description="排序"),
            AVParam("limit", kind="int", default=50, description="Alpha Vantage 返回新闻条数"),
        ),
        default_return_limit=50,
        examples=({"tickers": "AAPL", "sort": "LATEST", "limit": 20},),
    ),
    AVCapability(
        id="market_status",
        category="macro",
        label="全球市场开闭市",
        function="MARKET_STATUS",
        description="全球主要股票、外汇和加密市场开闭市状态。",
        default_return_limit=80,
        examples=({},),
    ),
    AVCapability(
        id="currency_exchange_rate",
        category="macro",
        label="汇率",
        function="CURRENCY_EXCHANGE_RATE",
        description="获取两个币种之间的实时汇率，适合跨币种持仓估值。",
        params=(
            AVParam("from_currency", default="USD", description="源币种，如 USD"),
            AVParam("to_currency", default="CNY", description="目标币种，如 CNY"),
        ),
        default_return_limit=1,
        examples=({"from_currency": "USD", "to_currency": "CNY"},),
    ),
)

CAPABILITIES_BY_ID = {item.id: item for item in CAPABILITIES}


class AlphaVantageClient:
    def __init__(self, api_key: str | None = None, endpoint: str = ALPHA_VANTAGE_ENDPOINT, timeout: float = 25) -> None:
        self.api_key = (api_key or alpha_vantage_api_key()).strip()
        if not self.api_key:
            raise AlphaVantageError("missing Alpha Vantage API key", status_code=503)
        self.endpoint = endpoint
        self.timeout = timeout

    def query(self, function: str, params: dict[str, Any] | None = None, datatype: str = "json") -> Any:
        query_params = {
            "function": function,
            **{key: normalize_query_value(value) for key, value in (params or {}).items() if value not in (None, "")},
            "apikey": self.api_key,
        }
        if datatype != "json":
            query_params["datatype"] = datatype

        request = Request(
            f"{self.endpoint}?{urlencode(query_params)}",
            headers={"Accept": "application/json,text/csv", "User-Agent": "KeikoStockAI/0.1"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
            raise AlphaVantageError(f"Alpha Vantage HTTP {exc.code}: {detail[:240]}", status_code=502) from exc
        except (OSError, URLError) as exc:
            raise AlphaVantageError(f"Alpha Vantage request failed: {exc}", status_code=502) from exc

        if datatype == "csv":
            return parse_csv(body)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AlphaVantageError(f"Alpha Vantage returned non-JSON response: {body[:240]}", status_code=502) from exc

        validate_alpha_payload(payload)
        return payload


def alpha_vantage_api_key() -> str:
    for name in ENV_KEY_NAMES:
        value = os.environ.get(name, "").strip()
        if value:
            return value

    values = dotenv_values()
    for name in ENV_KEY_NAMES:
        value = values.get(name, "").strip()
        if value:
            os.environ[name] = value
            return value
    return ""


def configure_runtime_alpha_vantage_key(api_key: str) -> None:
    clean_key = api_key.strip()
    if clean_key:
        os.environ["ALPHA_VANTAGE_API_KEY"] = clean_key


def clear_runtime_alpha_vantage_key() -> None:
    for name in ENV_KEY_NAMES:
        os.environ.pop(name, None)


def alpha_vantage_config_status() -> dict[str, Any]:
    key = alpha_vantage_api_key()
    return {
        "configured": bool(key),
        "credential_hint": mask_api_key(key) if key else "",
        "env_names": list(ENV_KEY_NAMES),
        "env_file": str(ENV_FILE),
        "endpoint": ALPHA_VANTAGE_ENDPOINT,
        "note": (
            "Alpha Vantage key 已通过环境变量或 .env 配置。"
            if key
            else "未配置 Alpha Vantage key；设置 ALPHA_VANTAGE_API_KEY 或在 .env 中写入后即可调用。"
        ),
    }


def list_alpha_vantage_capabilities(configured: bool | None = None, credential_hint: str = "") -> dict[str, Any]:
    status = alpha_vantage_config_status()
    if configured is not None:
        status["configured"] = configured
        if credential_hint:
            status["credential_hint"] = credential_hint
        status["note"] = (
            "Alpha Vantage key 已通过环境变量、.env 或账户私有凭据配置。"
            if configured
            else status["note"]
        )
    configured = bool(status["configured"])
    capabilities = [capability_payload(item, configured) for item in CAPABILITIES]
    return {
        "mode": "alpha-vantage-live" if configured else "alpha-vantage-not-configured",
        "status": status,
        "groups": [
            {"id": key, "label": label, "count": sum(1 for item in CAPABILITIES if item.category == key)}
            for key, label in CAPABILITY_GROUPS.items()
        ],
        "capabilities": capabilities,
        "summary": {
            "total": len(capabilities),
            "available": sum(1 for item in capabilities if item["available"]),
            "categories": len(CAPABILITY_GROUPS),
        },
    }


def query_alpha_vantage_capability(
    capability_id: str,
    raw_params: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    capability = CAPABILITIES_BY_ID.get(capability_id)
    if not capability:
        raise AlphaVantageError(f"Unknown Alpha Vantage capability: {capability_id}", status_code=404)

    raw_params = dict(raw_params or {})
    params, warnings = build_params(capability, raw_params)
    return_limit = parse_return_limit(raw_params.get("return_limit"), capability.default_return_limit)
    client = AlphaVantageClient(api_key=api_key)
    payload = client.query(capability.function, params, datatype=capability.datatype)
    result = shape_alpha_result(capability.id, payload, return_limit=return_limit)
    return {
        "mode": "alpha-vantage-live",
        "capability": capability_payload(capability, True),
        "params": params,
        "warnings": warnings,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "result": result,
    }


def search_alpha_vantage_symbols(query: str, limit: int = 20, api_key: str | None = None) -> dict[str, Any]:
    return query_alpha_vantage_capability(
        "symbol_search",
        {"keywords": query, "return_limit": limit},
        api_key=api_key,
    )


def alpha_vantage_quote(symbol: str, api_key: str | None = None) -> dict[str, Any]:
    return query_alpha_vantage_capability("global_quote", {"symbol": normalize_symbol(symbol)}, api_key=api_key)


def alpha_vantage_time_series(
    symbol: str,
    period: str = "daily",
    raw_params: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    capability_id = {
        "intraday": "intraday",
        "daily": "daily",
        "daily_adjusted": "daily_adjusted",
        "weekly": "weekly_adjusted",
        "weekly_adjusted": "weekly_adjusted",
        "monthly": "monthly_adjusted",
        "monthly_adjusted": "monthly_adjusted",
    }.get(period, period)
    if capability_id not in CAPABILITIES_BY_ID:
        raise AlphaVantageError("period must be intraday, daily, daily_adjusted, weekly_adjusted, or monthly_adjusted", status_code=400)
    params = dict(raw_params or {})
    params["symbol"] = normalize_symbol(symbol)
    return query_alpha_vantage_capability(capability_id, params, api_key=api_key)


def alpha_vantage_company_overview(symbol: str, api_key: str | None = None) -> dict[str, Any]:
    return query_alpha_vantage_capability("company_overview", {"symbol": normalize_symbol(symbol)}, api_key=api_key)


def alpha_vantage_financials(
    symbol: str,
    sections: str = "overview,income,balance,cash_flow,earnings",
    api_key: str | None = None,
) -> dict[str, Any]:
    section_map = {
        "overview": "company_overview",
        "income": "income_statement",
        "income_statement": "income_statement",
        "balance": "balance_sheet",
        "balance_sheet": "balance_sheet",
        "cash": "cash_flow",
        "cash_flow": "cash_flow",
        "earnings": "earnings",
    }
    requested = [item.strip().lower() for item in sections.split(",") if item.strip()]
    if not requested:
        requested = ["overview"]

    results: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    for section in requested:
        capability_id = section_map.get(section)
        if not capability_id:
            errors.append({"section": section, "error": "unknown financial section"})
            continue
        try:
            results[section] = query_alpha_vantage_capability(
                capability_id,
                {"symbol": normalize_symbol(symbol)},
                api_key=api_key,
            )
        except AlphaVantageError as exc:
            errors.append({"section": section, "error": str(exc)})

    return {
        "mode": "alpha-vantage-live",
        "symbol": normalize_symbol(symbol),
        "sections": results,
        "errors": errors,
        "note": "每个 section 都会消耗一次 Alpha Vantage API 调用；免费额度有限时建议按需请求。",
    }


def capability_payload(capability: AVCapability, available: bool) -> dict[str, Any]:
    return {
        "id": capability.id,
        "category": capability.category,
        "category_label": CAPABILITY_GROUPS.get(capability.category, capability.category),
        "label": capability.label,
        "function": capability.function,
        "description": capability.description,
        "params": [param_payload(param) for param in capability.params],
        "default_return_limit": capability.default_return_limit,
        "examples": [dict(example) for example in capability.examples],
        "docs_url": capability.docs_url,
        "datatype": capability.datatype,
        "available": available,
    }


def param_payload(param: AVParam) -> dict[str, Any]:
    return {
        "name": param.name,
        "kind": param.kind,
        "required": param.required,
        "default": resolve_default(param.default),
        "choices": list(param.choices),
        "description": param.description,
    }


def build_params(capability: AVCapability, raw_params: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    allowed = {param.name for param in capability.params}
    unknown = sorted(set(raw_params) - allowed - {"return_limit"})
    if unknown:
        warnings.append(f"已忽略未注册参数：{', '.join(unknown)}")

    params: dict[str, Any] = {}
    for param in capability.params:
        raw_value = raw_params.get(param.name)
        default = resolve_default(param.default)
        if raw_value in (None, ""):
            if param.required and default in (None, ""):
                raise AlphaVantageError(f"Missing required Alpha Vantage param: {param.name}", status_code=422)
            value = default
        else:
            value = coerce_value(raw_value, param)

        if value not in (None, "") and param.choices and value not in param.choices:
            raise AlphaVantageError(
                f"Invalid value for {param.name}; allowed: {', '.join(map(str, param.choices))}",
                status_code=422,
            )
        if value not in (None, ""):
            params[param.name] = normalize_param_value(param.name, value)
    return params, warnings


def shape_alpha_result(capability_id: str, payload: Any, return_limit: int) -> dict[str, Any]:
    if isinstance(payload, list):
        return table_result(payload, return_limit, result_type="csv")
    if not isinstance(payload, dict):
        return {"type": type(payload).__name__, "value": payload}

    if capability_id == "symbol_search":
        return table_result(normalize_symbol_matches(payload), return_limit)
    if capability_id == "global_quote":
        return table_result([normalize_quote(payload)], return_limit)
    if capability_id in {"intraday", "daily", "daily_adjusted", "weekly_adjusted", "monthly_adjusted"}:
        rows, metadata = normalize_time_series(payload)
        result = table_result(rows, return_limit, result_type="time_series")
        result["metadata"] = metadata
        return result
    if capability_id == "company_overview":
        return table_result([normalize_mapping(payload)], return_limit, result_type="overview")
    if capability_id in {"income_statement", "balance_sheet", "cash_flow", "earnings"}:
        return statement_result(payload, return_limit)
    if capability_id == "news_sentiment":
        return news_result(payload, return_limit)
    if capability_id == "etf_profile":
        return etf_result(payload, return_limit)
    if capability_id == "market_status":
        rows = [normalize_mapping(row) for row in payload.get("markets", [])]
        return table_result(rows, return_limit, result_type="market_status")
    if capability_id == "top_gainers_losers":
        return movers_result(payload, return_limit)
    if capability_id == "currency_exchange_rate":
        return table_result([normalize_mapping(payload.get("Realtime Currency Exchange Rate", {}))], return_limit)
    return table_result([normalize_mapping(payload)], return_limit)


def table_result(rows: list[dict[str, Any]], return_limit: int, result_type: str = "table") -> dict[str, Any]:
    limited = rows[:return_limit]
    return {
        "type": result_type,
        "columns": columns_for(rows),
        "total_rows": len(rows),
        "returned_rows": len(limited),
        "rows": limited,
    }


def statement_result(payload: dict[str, Any], return_limit: int) -> dict[str, Any]:
    annual = [normalize_mapping(row) for row in payload.get("annualReports", [])]
    quarterly = [normalize_mapping(row) for row in payload.get("quarterlyReports", [])]
    rows = quarterly or annual
    result = table_result(rows, return_limit, result_type="financial_statement")
    result["symbol"] = payload.get("symbol", "")
    result["sections"] = {
        "annualReports": {"total_rows": len(annual), "rows": annual[:return_limit]},
        "quarterlyReports": {"total_rows": len(quarterly), "rows": quarterly[:return_limit]},
    }
    return result


def news_result(payload: dict[str, Any], return_limit: int) -> dict[str, Any]:
    rows = []
    for item in payload.get("feed", []):
        ticker_sentiment = item.get("ticker_sentiment") or []
        rows.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "time_published": item.get("time_published", ""),
                "source": item.get("source", ""),
                "summary": item.get("summary", ""),
                "overall_sentiment_score": safe_float(item.get("overall_sentiment_score")),
                "overall_sentiment_label": item.get("overall_sentiment_label", ""),
                "authors": ", ".join(item.get("authors") or []),
                "tickers": ", ".join(row.get("ticker", "") for row in ticker_sentiment),
                "raw_ticker_sentiment": ticker_sentiment,
            }
        )
    result = table_result(rows, return_limit, result_type="news_sentiment")
    result["items"] = payload.get("items", len(rows))
    result["sentiment_score_definition"] = payload.get("sentiment_score_definition", "")
    result["relevance_score_definition"] = payload.get("relevance_score_definition", "")
    return result


def etf_result(payload: dict[str, Any], return_limit: int) -> dict[str, Any]:
    profile_keys = [
        "net_assets",
        "net_expense_ratio",
        "portfolio_turnover",
        "dividend_yield",
        "inception_date",
        "leveraged",
    ]
    profile = {key: normalize_value(payload.get(key)) for key in profile_keys if key in payload}
    profile["symbol"] = payload.get("symbol", "")
    profile["name"] = payload.get("name", "")
    holdings = [normalize_mapping(row) for row in payload.get("holdings", [])]
    result = table_result(holdings or [profile], return_limit, result_type="etf_profile")
    result["profile"] = profile
    result["sectors"] = [normalize_mapping(row) for row in payload.get("sectors", [])]
    result["asset_allocation"] = [normalize_mapping(row) for row in payload.get("asset_allocation", [])]
    return result


def movers_result(payload: dict[str, Any], return_limit: int) -> dict[str, Any]:
    rows = []
    for section in ("top_gainers", "top_losers", "most_actively_traded"):
        for item in payload.get(section, []) or []:
            rows.append({"section": section, **normalize_mapping(item)})
    result = table_result(rows, return_limit, result_type="top_movers")
    result["last_updated"] = payload.get("last_updated", "")
    return result


def normalize_symbol_matches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in payload.get("bestMatches", []) or []:
        rows.append(
            {
                "symbol": item.get("1. symbol", ""),
                "name": item.get("2. name", ""),
                "type": item.get("3. type", ""),
                "region": item.get("4. region", ""),
                "market_open": item.get("5. marketOpen", ""),
                "market_close": item.get("6. marketClose", ""),
                "timezone": item.get("7. timezone", ""),
                "currency": item.get("8. currency", ""),
                "match_score": safe_float(item.get("9. matchScore")),
            }
        )
    return rows


def normalize_quote(payload: dict[str, Any]) -> dict[str, Any]:
    quote = payload.get("Global Quote", {}) or {}
    return {
        "symbol": quote.get("01. symbol", ""),
        "open": safe_float(quote.get("02. open")),
        "high": safe_float(quote.get("03. high")),
        "low": safe_float(quote.get("04. low")),
        "price": safe_float(quote.get("05. price")),
        "volume": safe_int(quote.get("06. volume")),
        "latest_trading_day": quote.get("07. latest trading day", ""),
        "previous_close": safe_float(quote.get("08. previous close")),
        "change": safe_float(quote.get("09. change")),
        "change_percent": quote.get("10. change percent", ""),
    }


def normalize_time_series(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    metadata = normalize_mapping(payload.get("Meta Data", {}) or {})
    series_key = find_time_series_key(payload)
    if not series_key:
        return [], metadata
    rows = []
    for timestamp, values in (payload.get(series_key) or {}).items():
        row = {"timestamp": timestamp}
        for key, value in values.items():
            row[normalize_alpha_key(key)] = normalize_value(value)
        rows.append(row)
    return sorted(rows, key=lambda item: str(item.get("timestamp", "")), reverse=True), metadata


def find_time_series_key(payload: dict[str, Any]) -> str:
    for key, value in payload.items():
        if key == "Meta Data" or not isinstance(value, dict):
            continue
        if "Time Series" in key or "Weekly" in key or "Monthly" in key:
            return key
    return ""


def normalize_mapping(payload: dict[str, Any]) -> dict[str, Any]:
    return {normalize_alpha_key(key): normalize_value(value) for key, value in payload.items()}


def normalize_alpha_key(key: Any) -> str:
    text = str(key).strip()
    if ". " in text and text.split(". ", 1)[0].replace(" ", "").isdigit():
        text = text.split(". ", 1)[1]
    return (
        text.replace("%", "percent")
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .lower()
    )


def normalize_value(value: Any) -> Any:
    if value in (None, "", "None", "null", "-", "N/A"):
        return None
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, dict):
        return normalize_mapping(value)
    if isinstance(value, str):
        number = safe_float(value)
        if number is not None and value.strip().replace(".", "", 1).replace("-", "", 1).isdigit():
            return int(number) if float(number).is_integer() else number
    return value


def columns_for(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for row in rows[:20]:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def validate_alpha_payload(payload: dict[str, Any]) -> None:
    if "Error Message" in payload:
        raise AlphaVantageError(str(payload["Error Message"]), status_code=422, payload=payload)
    if "Note" in payload:
        raise AlphaVantageError(str(payload["Note"]), status_code=429, payload=payload)
    if "Information" in payload:
        message = str(payload["Information"])
        status_code = 429 if "rate limit" in message.lower() or "standard api rate" in message.lower() else 503
        raise AlphaVantageError(message, status_code=status_code, payload=payload)


def parse_csv(body: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(body.splitlines())
    return [normalize_mapping(dict(row)) for row in reader]


def dotenv_values(path: Path = ENV_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def resolve_default(default: Any) -> Any:
    if callable(default):
        return default()
    return default


def coerce_value(raw_value: Any, param: AVParam) -> Any:
    if param.kind == "int":
        return int(raw_value)
    if param.kind == "float":
        return float(raw_value)
    if param.kind == "bool":
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).strip().lower() in {"1", "true", "yes", "y", "on"}
    return str(raw_value).strip()


def normalize_param_value(name: str, value: Any) -> Any:
    if name == "symbol":
        return normalize_symbol(str(value))
    if name in {"tickers", "from_currency", "to_currency"}:
        return str(value).strip().upper()
    return value


def normalize_query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def parse_return_limit(raw_limit: Any, default: int) -> int:
    if raw_limit in (None, ""):
        return min(default, MAX_RETURN_ROWS)
    try:
        return max(1, min(int(raw_limit), MAX_RETURN_ROWS))
    except (TypeError, ValueError):
        raise AlphaVantageError("return_limit must be an integer", status_code=422) from None


def safe_float(value: Any) -> float | None:
    if value in (None, "", "None", "null", "-", "N/A"):
        return None
    try:
        return float(str(value).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None


def safe_int(value: Any) -> int | None:
    number = safe_float(value)
    if number is None:
        return None
    return int(number)


def mask_api_key(value: str) -> str:
    if len(value) <= 6:
        return "******"
    return f"{value[:3]}...{value[-3:]}"
