from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException


RESERVED_QUERY_PARAMS = {"limit", "q"}
MAX_RETURN_ROWS = 5000


@dataclass(frozen=True)
class AkParam:
    name: str
    kind: str = "str"
    required: bool = False
    default: Any = None
    choices: tuple[Any, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class AkCapability:
    id: str
    category: str
    label: str
    function: str
    description: str
    params: tuple[AkParam, ...] = ()
    default_limit: int = 200
    examples: tuple[dict[str, Any], ...] = ()
    notes: tuple[str, ...] = ()
    docs_url: str = "https://akshare.akfamily.xyz/"


def yyyymmdd(days_ago: int = 0) -> str:
    return (date.today() - timedelta(days=days_ago)).strftime("%Y%m%d")


def minute_start_default() -> str:
    return f"{yyyymmdd()} 09:30:00"


def minute_end_default() -> str:
    return f"{yyyymmdd()} 15:00:00"


CAPABILITY_GROUPS = {
    "stock": "股票",
    "index": "指数",
    "board": "行业/概念板块",
    "fund": "基金/ETF",
    "bond": "债券/可转债",
    "macro": "宏观",
    "fx": "外汇",
    "futures": "期货",
    "news": "资讯",
}


CAPABILITIES: tuple[AkCapability, ...] = (
    AkCapability(
        id="stock_a_spot",
        category="stock",
        label="A 股实时行情快照",
        function="stock_zh_a_spot_em",
        description="东方财富 A 股全市场快照，常用于搜索股票、获取最新价、涨跌幅、成交额、换手率等字段。",
        default_limit=300,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_a_hist",
        category="stock",
        label="A 股日/周/月 K 线",
        function="stock_zh_a_hist",
        description="A 股复权或不复权历史行情，适合生成 K 线、均线、波动率和技术因子。",
        params=(
            AkParam("symbol", required=True, description="6 位股票代码，如 600519 或 002594"),
            AkParam("period", default="daily", choices=("daily", "weekly", "monthly"), description="周期"),
            AkParam("start_date", default=lambda: yyyymmdd(365), description="YYYYMMDD"),
            AkParam("end_date", default=yyyymmdd, description="YYYYMMDD"),
            AkParam("adjust", default="", choices=("", "qfq", "hfq"), description="复权方式"),
        ),
        default_limit=260,
        examples=({"symbol": "600519", "period": "daily", "adjust": "qfq"},),
        notes=("A 股代码会自动去掉 .SH/.SZ 后缀。",),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_a_minute",
        category="stock",
        label="A 股分钟线",
        function="stock_zh_a_hist_min_em",
        description="A 股分钟级行情，适合盘中刷新、成交量确认和 intraday 风控。",
        params=(
            AkParam("symbol", required=True, description="6 位股票代码，如 600519"),
            AkParam("period", default="5", choices=("1", "5", "15", "30", "60"), description="分钟周期"),
            AkParam("start_date", default=minute_start_default, description="YYYY-MM-DD HH:MM:SS"),
            AkParam("end_date", default=minute_end_default, description="YYYY-MM-DD HH:MM:SS"),
            AkParam("adjust", default="", choices=("", "qfq", "hfq"), description="复权方式"),
        ),
        default_limit=300,
        examples=({"symbol": "600519", "period": "5"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_a_info",
        category="stock",
        label="A 股个股资料",
        function="stock_individual_info_em",
        description="个股基础信息，常用于补全名称、总市值、流通市值、行业等字段。",
        params=(AkParam("symbol", required=True, description="6 位股票代码，如 600519"),),
        default_limit=80,
        examples=({"symbol": "600519"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_a_financial_abstract",
        category="stock",
        label="A 股财务摘要",
        function="stock_financial_abstract",
        description="A 股主要财务指标摘要，适合 ROE、利润率、成长性等基本面因子。",
        params=(AkParam("symbol", required=True, description="6 位股票代码，如 600519"),),
        default_limit=120,
        examples=({"symbol": "600519"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_a_financial_indicator",
        category="stock",
        label="A 股财务分析指标",
        function="stock_financial_analysis_indicator",
        description="新浪财务分析指标，适合拉较长时间序列的财务比率。",
        params=(
            AkParam("symbol", required=True, description="6 位股票代码，如 600519"),
            AkParam("start_year", default=lambda: str(date.today().year - 5), description="起始年份"),
        ),
        default_limit=160,
        examples=({"symbol": "600519", "start_year": "2020"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_a_balance_sheet",
        category="stock",
        label="A 股资产负债表",
        function="stock_balance_sheet_by_report_em",
        description="按报告期获取资产负债表，用于偿债能力、资产质量和资本结构分析。",
        params=(AkParam("symbol", required=True, description="交易所前缀代码，如 SH600519 或 SZ002594"),),
        default_limit=120,
        examples=({"symbol": "SH600519"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_a_profit_sheet",
        category="stock",
        label="A 股利润表",
        function="stock_profit_sheet_by_report_em",
        description="按报告期获取利润表，用于收入、利润、费用率和盈利质量分析。",
        params=(AkParam("symbol", required=True, description="交易所前缀代码，如 SH600519 或 SZ002594"),),
        default_limit=120,
        examples=({"symbol": "SH600519"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_a_cash_flow",
        category="stock",
        label="A 股现金流量表",
        function="stock_cash_flow_sheet_by_report_em",
        description="按报告期获取现金流量表，用于自由现金流、经营现金流和利润含金量分析。",
        params=(AkParam("symbol", required=True, description="交易所前缀代码，如 SH600519 或 SZ002594"),),
        default_limit=120,
        examples=({"symbol": "SH600519"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_a_news",
        category="news",
        label="A 股个股新闻",
        function="stock_news_em",
        description="东方财富个股新闻列表，可作为新闻情绪和事件抽取的输入。",
        params=(AkParam("symbol", required=True, description="6 位股票代码，如 600519"),),
        default_limit=50,
        examples=({"symbol": "600519"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_hk_spot",
        category="stock",
        label="港股实时行情快照",
        function="stock_hk_spot_em",
        description="东方财富港股全市场快照，适合港股搜索和最新行情展示。",
        default_limit=300,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_hk_hist",
        category="stock",
        label="港股历史 K 线",
        function="stock_hk_hist",
        description="港股历史行情，适合技术面和持仓收益回放。",
        params=(
            AkParam("symbol", required=True, description="港股 5 位代码，如 00700"),
            AkParam("period", default="daily", choices=("daily", "weekly", "monthly"), description="周期"),
            AkParam("start_date", default=lambda: yyyymmdd(365), description="YYYYMMDD"),
            AkParam("end_date", default=yyyymmdd, description="YYYYMMDD"),
            AkParam("adjust", default="", choices=("", "qfq", "hfq"), description="复权方式"),
        ),
        default_limit=260,
        examples=({"symbol": "00700", "period": "daily"},),
        notes=("港股代码会自动去掉 .HK 后缀并补齐到 5 位。",),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_us_spot",
        category="stock",
        label="美股实时行情快照",
        function="stock_us_spot_em",
        description="东方财富美股市场快照，适合搜索和获取最新价等字段。",
        default_limit=300,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="stock_us_hist",
        category="stock",
        label="美股历史 K 线",
        function="stock_us_hist",
        description="美股历史行情。部分 AKShare 版本要求使用 spot 返回的代码，如 105.AAPL。",
        params=(
            AkParam("symbol", required=True, description="美股代码，如 105.AAPL；快捷接口可传 AAPL"),
            AkParam("period", default="daily", choices=("daily", "weekly", "monthly"), description="周期"),
            AkParam("start_date", default=lambda: yyyymmdd(365), description="YYYYMMDD"),
            AkParam("end_date", default=yyyymmdd, description="YYYYMMDD"),
            AkParam("adjust", default="", choices=("", "qfq", "hfq"), description="复权方式"),
        ),
        default_limit=260,
        examples=({"symbol": "105.AAPL", "period": "daily"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="index_a_spot",
        category="index",
        label="A 股指数实时行情",
        function="stock_zh_index_spot_em",
        description="沪深京指数实时快照，适合大盘、宽基和行业指数观察。",
        default_limit=300,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/index/index.html",
    ),
    AkCapability(
        id="index_a_hist",
        category="index",
        label="A 股指数历史行情",
        function="stock_zh_index_daily_em",
        description="A 股指数历史日线，适合大盘趋势和指数基准回测。",
        params=(AkParam("symbol", required=True, description="指数代码，如 sh000001 或 sz399006"),),
        default_limit=260,
        examples=({"symbol": "sh000001"},),
        docs_url="https://akshare.akfamily.xyz/data/index/index.html",
    ),
    AkCapability(
        id="board_industry_list",
        category="board",
        label="东方财富行业板块列表",
        function="stock_board_industry_name_em",
        description="行业板块名称、涨跌幅和热度，适合板块轮动入口。",
        default_limit=120,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="board_industry_cons",
        category="board",
        label="行业板块成份股",
        function="stock_board_industry_cons_em",
        description="按行业板块获取成份股，用于板块筛选和批量分析。",
        params=(AkParam("symbol", required=True, description="行业名称，如 小金属"),),
        default_limit=200,
        examples=({"symbol": "小金属"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="board_concept_list",
        category="board",
        label="东方财富概念板块列表",
        function="stock_board_concept_name_em",
        description="概念板块名称、涨跌幅和热度，适合主题投资和催化扫描。",
        default_limit=160,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="board_concept_cons",
        category="board",
        label="概念板块成份股",
        function="stock_board_concept_cons_em",
        description="按概念板块获取成份股，用于主题池和事件驱动筛选。",
        params=(AkParam("symbol", required=True, description="概念名称，如 车联网"),),
        default_limit=200,
        examples=({"symbol": "车联网"},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
    AkCapability(
        id="fund_etf_spot",
        category="fund",
        label="ETF 实时行情",
        function="fund_etf_spot_em",
        description="场内 ETF 快照，适合宽基、行业、跨境 ETF 搜索和比较。",
        default_limit=300,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/fund/fund.html",
    ),
    AkCapability(
        id="fund_etf_hist",
        category="fund",
        label="ETF 历史行情",
        function="fund_etf_hist_em",
        description="场内 ETF 历史行情，适合 ETF 趋势、波动和回撤分析。",
        params=(
            AkParam("symbol", required=True, description="ETF 代码，如 510300"),
            AkParam("period", default="daily", choices=("daily", "weekly", "monthly"), description="周期"),
            AkParam("start_date", default=lambda: yyyymmdd(365), description="YYYYMMDD"),
            AkParam("end_date", default=yyyymmdd, description="YYYYMMDD"),
            AkParam("adjust", default="", choices=("", "qfq", "hfq"), description="复权方式"),
        ),
        default_limit=260,
        examples=({"symbol": "510300", "period": "daily"},),
        docs_url="https://akshare.akfamily.xyz/data/fund/fund.html",
    ),
    AkCapability(
        id="fund_open_daily",
        category="fund",
        label="开放式基金净值",
        function="fund_open_fund_daily_em",
        description="开放式基金最新净值列表，适合基金池、净值日期和收益字段展示。",
        default_limit=300,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/fund/fund.html",
    ),
    AkCapability(
        id="bond_spot",
        category="bond",
        label="沪深债券实时行情",
        function="bond_zh_hs_spot",
        description="沪深债券实时行情，适合债券价格和收益率入口。",
        default_limit=300,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/bond/bond.html",
    ),
    AkCapability(
        id="bond_convertible_spot",
        category="bond",
        label="可转债实时行情",
        function="bond_zh_hs_cov_spot",
        description="沪深可转债行情，适合转债价格、溢价率和正股联动观察。",
        default_limit=300,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/bond/bond.html",
    ),
    AkCapability(
        id="macro_china_cpi",
        category="macro",
        label="中国 CPI",
        function="macro_china_cpi",
        description="中国 CPI 数据，适合宏观通胀背景和利率环境判断。",
        default_limit=120,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/macro/macro.html",
    ),
    AkCapability(
        id="macro_china_ppi",
        category="macro",
        label="中国 PPI",
        function="macro_china_ppi",
        description="中国 PPI 数据，适合上游价格、利润压力和周期判断。",
        default_limit=120,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/macro/macro.html",
    ),
    AkCapability(
        id="macro_china_pmi",
        category="macro",
        label="中国 PMI",
        function="macro_china_pmi",
        description="中国 PMI 数据，适合经济景气度、制造业趋势和市场风格判断。",
        default_limit=120,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/macro/macro.html",
    ),
    AkCapability(
        id="macro_china_gdp",
        category="macro",
        label="中国 GDP",
        function="macro_china_gdp",
        description="中国 GDP 数据，适合宏观增长背景和资产配置解释。",
        default_limit=80,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/macro/macro.html",
    ),
    AkCapability(
        id="fx_spot",
        category="fx",
        label="外汇实时行情",
        function="forex_spot_em",
        description="外汇市场快照，适合汇率换算、跨市场持仓展示和美元/港币/人民币风险暴露。",
        default_limit=200,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/fx/fx.html",
    ),
    AkCapability(
        id="fx_boc",
        category="fx",
        label="中国银行外汇牌价",
        function="currency_boc_sina",
        description="中国银行外汇牌价，适合本地估算换汇成本和展示参考汇率。",
        default_limit=200,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/fx/fx.html",
    ),
    AkCapability(
        id="futures_main",
        category="futures",
        label="国内期货主力连续",
        function="futures_main_sina",
        description="新浪期货主力连续行情，适合商品价格背景和周期板块解释。",
        params=(AkParam("symbol", required=True, description="主力连续代码，如 V0、RB0、AU0"),),
        default_limit=260,
        examples=({"symbol": "RB0"},),
        docs_url="https://akshare.akfamily.xyz/data/futures/futures.html",
    ),
    AkCapability(
        id="global_news",
        category="news",
        label="全球财经资讯",
        function="stock_info_global_sina",
        description="新浪全球财经资讯，适合作为宏观/市场新闻入口。",
        default_limit=80,
        examples=({},),
        docs_url="https://akshare.akfamily.xyz/data/stock/stock.html",
    ),
)

CAPABILITIES_BY_ID = {item.id: item for item in CAPABILITIES}
SPOT_BY_MARKET = {"A": "stock_a_spot", "HK": "stock_hk_spot", "US": "stock_us_spot"}
HIST_BY_MARKET = {"A": "stock_a_hist", "HK": "stock_hk_hist", "US": "stock_us_hist"}


def akshare_status() -> dict[str, Any]:
    try:
        ak = importlib.import_module("akshare")
    except ModuleNotFoundError:
        return {
            "installed": False,
            "version": None,
            "install": "python3 -m pip install -r requirements.txt",
            "note": "当前 Python 环境未安装 akshare；能力清单仍可查看，真实拉数接口会返回安装提示。",
        }
    except Exception as exc:
        return {
            "installed": False,
            "version": None,
            "install": "python3 -m pip install -r requirements.txt",
            "note": f"akshare 导入失败：{exc}",
        }

    return {
        "installed": True,
        "version": getattr(ak, "__version__", "unknown"),
        "install": "python3 -m pip install -r requirements.txt",
        "note": "AKShare 已安装；具体接口仍取决于当前 AKShare 版本和上游数据源可用性。",
    }


def list_akshare_capabilities() -> dict[str, Any]:
    status = akshare_status()
    available_functions: set[str] = set()
    if status["installed"]:
        ak = importlib.import_module("akshare")
        available_functions = set(dir(ak))

    capabilities = [capability_payload(item, available_functions) for item in CAPABILITIES]
    return {
        "mode": "akshare-live" if status["installed"] else "akshare-not-installed",
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


def capability_payload(capability: AkCapability, available_functions: set[str] | None = None) -> dict[str, Any]:
    available = capability.function in available_functions if available_functions is not None else None
    return {
        "id": capability.id,
        "category": capability.category,
        "category_label": CAPABILITY_GROUPS.get(capability.category, capability.category),
        "label": capability.label,
        "function": capability.function,
        "description": capability.description,
        "params": [param_payload(param) for param in capability.params],
        "default_limit": capability.default_limit,
        "examples": [dict(example) for example in capability.examples],
        "notes": list(capability.notes),
        "docs_url": capability.docs_url,
        "available": bool(available) if available is not None else False,
    }


def param_payload(param: AkParam) -> dict[str, Any]:
    default = resolve_default(param.default)
    return {
        "name": param.name,
        "kind": param.kind,
        "required": param.required,
        "default": default,
        "choices": list(param.choices),
        "description": param.description,
    }


def query_akshare_capability(capability_id: str, raw_params: dict[str, Any] | None = None) -> dict[str, Any]:
    capability = CAPABILITIES_BY_ID.get(capability_id)
    if not capability:
        raise HTTPException(status_code=404, detail=f"Unknown AKShare capability: {capability_id}")

    status = akshare_status()
    if not status["installed"]:
        raise HTTPException(status_code=503, detail=status)

    raw_params = dict(raw_params or {})
    ak = importlib.import_module("akshare")
    func = getattr(ak, capability.function, None)
    if not callable(func):
        raise HTTPException(
            status_code=501,
            detail={
                "message": f"当前 AKShare 版本不包含 {capability.function}",
                "capability": capability.id,
                "status": status,
            },
        )

    params, warnings = build_params(capability, raw_params)
    limit = parse_limit(raw_params.get("limit"), capability.default_limit)
    query = str(raw_params.get("q", "")).strip()

    try:
        result = func(**params)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "AKShare 调用失败，可能是参数不匹配、源站变更、网络不可用或上游限流。",
                "capability": capability.id,
                "function": capability.function,
                "params": params,
                "error": str(exc),
            },
        ) from exc

    payload = shape_result(result, limit=limit, query=query)
    return {
        "mode": "akshare-live",
        "capability": capability_payload(capability, set(dir(ak))),
        "params": params,
        "warnings": warnings,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "result": payload,
    }


def search_akshare_symbols(query: str = "", market: str = "all", limit: int = 50) -> dict[str, Any]:
    normalized_market = market.upper()
    if normalized_market == "ALL":
        markets = ["A", "HK", "US"]
    elif normalized_market in SPOT_BY_MARKET:
        markets = [normalized_market]
    else:
        raise HTTPException(status_code=400, detail="market must be one of all, A, HK, US")

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for item_market in markets:
        try:
            response = query_akshare_capability(SPOT_BY_MARKET[item_market], {"q": query, "limit": limit})
            for row in response["result"].get("rows", []):
                rows.append(normalize_symbol_row(row, item_market))
        except HTTPException as exc:
            errors.append({"market": item_market, "error": str(exc.detail)})

    return {
        "mode": "akshare-live",
        "market": normalized_market,
        "query": query,
        "count": min(len(rows), limit),
        "rows": rows[:limit],
        "errors": errors,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }


def stock_spot(market: str, raw_params: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized_market = market.upper()
    capability_id = SPOT_BY_MARKET.get(normalized_market)
    if not capability_id:
        raise HTTPException(status_code=400, detail="market must be A, HK, or US")
    return query_akshare_capability(capability_id, raw_params)


def stock_history(market: str, symbol: str, raw_params: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized_market = market.upper()
    capability_id = HIST_BY_MARKET.get(normalized_market)
    if not capability_id:
        raise HTTPException(status_code=400, detail="market must be A, HK, or US")
    params = dict(raw_params or {})
    params["symbol"] = normalize_symbol(symbol, normalized_market, capability_id)
    return query_akshare_capability(capability_id, params)


def index_spot(raw_params: dict[str, Any] | None = None) -> dict[str, Any]:
    return query_akshare_capability("index_a_spot", raw_params)


def build_params(capability: AkCapability, raw_params: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    allowed = {param.name for param in capability.params}
    unknown = sorted(set(raw_params) - allowed - RESERVED_QUERY_PARAMS)
    if unknown:
        warnings.append(f"已忽略未注册参数：{', '.join(unknown)}")

    params: dict[str, Any] = {}
    for param in capability.params:
        raw_value = raw_params.get(param.name)
        default = resolve_default(param.default)
        if raw_value in (None, ""):
            if param.required and default in (None, ""):
                raise HTTPException(status_code=422, detail=f"Missing required AKShare param: {param.name}")
            value = default
        else:
            value = coerce_value(raw_value, param)

        if value not in (None, "") and param.choices and value not in param.choices:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid value for {param.name}; allowed: {', '.join(map(str, param.choices))}",
            )
        if value is not None:
            params[param.name] = normalize_param_value(capability.id, param.name, value)
    return params, warnings


def resolve_default(default: Any) -> Any:
    if callable(default):
        return default()
    return default


def coerce_value(raw_value: Any, param: AkParam) -> Any:
    if param.kind == "int":
        return int(raw_value)
    if param.kind == "float":
        return float(raw_value)
    if param.kind == "bool":
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).strip().lower() in {"1", "true", "yes", "y", "on"}
    return str(raw_value).strip()


def normalize_param_value(capability_id: str, name: str, value: Any) -> Any:
    if name != "symbol":
        return value
    if capability_id.startswith("stock_a_") and capability_id not in {
        "stock_a_balance_sheet",
        "stock_a_profit_sheet",
        "stock_a_cash_flow",
    }:
        return normalize_cn_symbol(str(value))
    if capability_id in {"stock_hk_hist"}:
        return normalize_hk_symbol(str(value))
    if capability_id == "stock_us_hist":
        return normalize_us_symbol(str(value), for_hist=True)
    if capability_id in {"stock_a_balance_sheet", "stock_a_profit_sheet", "stock_a_cash_flow"}:
        return normalize_cn_exchange_symbol(str(value))
    return value


def normalize_symbol(symbol: str, market: str, capability_id: str = "") -> str:
    if market == "A":
        return normalize_cn_symbol(symbol)
    if market == "HK":
        return normalize_hk_symbol(symbol)
    if market == "US":
        return normalize_us_symbol(symbol, for_hist=capability_id == "stock_us_hist")
    return symbol.strip().upper()


def normalize_cn_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    normalized = normalized.removeprefix("SH").removeprefix("SZ").removeprefix("BJ")
    return normalized.split(".")[0]


def normalize_cn_exchange_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper().replace(".", "")
    if normalized.startswith(("SH", "SZ", "BJ")):
        return normalized
    code = normalize_cn_symbol(normalized)
    if code.startswith("6"):
        return f"SH{code}"
    if code.startswith(("0", "2", "3")):
        return f"SZ{code}"
    if code.startswith(("4", "8", "9")):
        return f"BJ{code}"
    return code


def normalize_hk_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper().removesuffix(".HK")
    return normalized.zfill(5)


def normalize_us_symbol(symbol: str, for_hist: bool = False) -> str:
    normalized = symbol.strip().upper()
    if for_hist and "." not in normalized:
        return f"105.{normalized}"
    return normalized


def normalize_symbol_row(row: dict[str, Any], market: str) -> dict[str, Any]:
    code = pick_first(row, ["代码", "symbol", "证券代码", "代码"])
    name = pick_first(row, ["名称", "name", "证券简称", "中文名称", "英文名称"])
    latest = pick_first(row, ["最新价", "价格", "收盘", "现价"])
    change_pct = pick_first(row, ["涨跌幅", "涨幅", "涨跌幅%"])
    return {
        "market": market,
        "symbol": code,
        "name": name,
        "latest": latest,
        "change_pct": change_pct,
        "raw": row,
    }


def pick_first(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return ""


def parse_limit(raw_limit: Any, default: int) -> int:
    if raw_limit in (None, ""):
        return min(default, MAX_RETURN_ROWS)
    try:
        return max(1, min(int(raw_limit), MAX_RETURN_ROWS))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="limit must be an integer") from None


def shape_result(result: Any, limit: int, query: str = "") -> dict[str, Any]:
    if hasattr(result, "columns") and hasattr(result, "to_dict"):
        total_rows = safe_len(result)
        columns = [str(column) for column in getattr(result, "columns", [])]
        rows = frame_to_records(result, limit=limit, query=query)
        return {
            "type": "table",
            "columns": columns,
            "total_rows": total_rows,
            "returned_rows": len(rows),
            "filtered": bool(query),
            "rows": rows,
        }

    if hasattr(result, "to_dict"):
        return {"type": type(result).__name__, "value": sanitize_value(result.to_dict())}

    value = sanitize_value(result)
    if isinstance(value, list):
        filtered = filter_rows(value, query) if query else value
        return {
            "type": "list",
            "total_rows": len(value),
            "returned_rows": min(len(filtered), limit),
            "filtered": bool(query),
            "rows": filtered[:limit],
        }
    return {"type": type(result).__name__, "value": value}


def frame_to_records(frame: Any, limit: int, query: str = "") -> list[dict[str, Any]]:
    if query:
        records = sanitize_value(frame.to_dict(orient="records"))
        records = filter_rows(records, query)
        return records[:limit]
    head = frame.head(limit) if hasattr(frame, "head") else frame
    return sanitize_value(head.to_dict(orient="records"))


def filter_rows(rows: list[Any], query: str) -> list[Any]:
    normalized = query.strip().lower()
    if not normalized:
        return rows
    return [row for row in rows if normalized in stringify_for_search(row)]


def stringify_for_search(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(stringify_for_search(item) for item in value.values()).lower()
    if isinstance(value, (list, tuple)):
        return " ".join(stringify_for_search(item) for item in value).lower()
    return str(value).lower()


def safe_len(value: Any) -> int:
    try:
        return len(value)
    except TypeError:
        return 0


def sanitize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): sanitize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_value(item) for item in value]
    if hasattr(value, "item"):
        try:
            return sanitize_value(value.item())
        except Exception:
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)
