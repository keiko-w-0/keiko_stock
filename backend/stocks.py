from __future__ import annotations

import sqlite3
import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Callable

from fastapi import HTTPException

from . import seed_data
from .data_sources import DEFAULT_ACCOUNT_ID, SOURCE_KIND_LABELS, active_source_ids, active_source_kinds_by_market
from .db import row_to_dict
from .schemas import ScreenerInput
from .symbol_resolver import resolve_symbol


FILTERS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "amount-high": lambda stock: stock["metrics"]["avgAmountCny"] >= 5000000000,
    "turnover-high": lambda stock: stock["metrics"]["turnoverRate"] >= 1,
    "spread-low": lambda stock: stock["metrics"]["spreadBps"] <= 5,
    "valuation-not-hot": lambda stock: stock["metrics"]["pePercentile"] <= 70,
    "roe-high": lambda stock: stock["metrics"]["roe"] >= 15,
    "cashflow-good": lambda stock: stock["metrics"]["fcfMargin"] >= 5,
    "trend-strong": lambda stock: stock["metrics"]["ma20GapPct"] > 0,
    "volume-confirm": lambda stock: stock["metrics"]["volumeRatio"] >= 1.2,
    "catalyst-strong": lambda stock: stock["metrics"]["catalystScore"] >= 75,
    "data-fresh": lambda stock: stock["freshnessStatus"] == "fresh",
    "evidence-high": lambda stock: stock["truthScore"] >= 80,
    "rumor-low": lambda stock: stock["metrics"]["unverifiedRatio"] < 0.25,
}


PROVIDER_LABELS = {
    "tushare-market": "Tushare Pro 行情",
    "tushare-financial": "Tushare Pro 财务指标",
    "akshare-market": "AKShare A股行情",
    "baostock-market": "BaoStock 历史日线",
    "finnhub-market": "Finnhub 美股行情",
    "finnhub-financial": "Finnhub 基本面",
    "finnhub-news": "Finnhub 公司新闻",
    "alpha_vantage-news": "Alpha Vantage 新闻情绪",
}


def search_stocks(conn: sqlite3.Connection, query: str = "", market: str = "all", account_id: str = DEFAULT_ACCOUNT_ID) -> dict[str, Any]:
    normalized_query = query.strip().lower()
    resolved = resolve_symbol(conn, query, market) if normalized_query else None
    resolved_symbol = str(resolved["symbol"]).upper() if resolved else ""
    stocks = all_stock_payloads(conn, normalized_query, account_id)
    normalized_market = market.upper()
    if normalized_market != "ALL":
        stocks = [stock for stock in stocks if stock["market"] == normalized_market]
    if resolved_symbol and not any(stock["symbol"].upper() == resolved_symbol for stock in stocks):
        symbol_row = conn.execute("select * from symbols where upper(symbol) = ?", (resolved_symbol,)).fetchone()
        if symbol_row:
            active_sources = active_source_kinds_by_market(conn, account_id)
            stocks.append(build_stock_payload(row_to_dict(symbol_row), active_sources))
    if normalized_query:
        stocks = [
            stock
            for stock in stocks
            if normalized_query in stock["symbol"].lower()
            or normalized_query in stock["name"].lower()
            or (resolved_symbol and stock["symbol"].upper() == resolved_symbol)
        ]
    mode = "provider-cached" if any(stock["sourceStatus"]["mode"] == "provider-cached" for stock in stocks) else "provider-configured"
    return {
        "stocks": stocks,
        "mode": mode,
        "count": len(stocks),
        "query": {"raw": query, "resolved_symbol": resolved_symbol or None},
    }


def run_screener(conn: sqlite3.Connection, payload: ScreenerInput) -> dict[str, Any]:
    result = search_stocks(conn, market=payload.market, account_id=payload.account_id)
    rules = [FILTERS[item] for item in payload.filter_ids if item in FILTERS]
    if not rules:
        return {**result, "applied_filters": [], "filter_mode": payload.mode}

    mode = "any" if payload.mode == "any" else "all"
    stocks = []
    for stock in result["stocks"]:
        outcomes = [rule(stock) for rule in rules]
        matched = all(outcomes) if mode == "all" else any(outcomes)
        if matched:
            stocks.append(stock)
    return {
        "stocks": stocks,
        "mode": result["mode"],
        "count": len(stocks),
        "applied_filters": payload.filter_ids,
        "filter_mode": mode,
    }


def stock_memory(conn: sqlite3.Connection, symbol: str) -> dict[str, Any]:
    normalized = symbol.upper()
    stock = conn.execute("select symbol, name, market from symbols where symbol = ?", (normalized,)).fetchone()
    if not stock:
        raise HTTPException(status_code=404, detail="symbol not found")

    memory = conn.execute(
        """
        select *
        from stock_memories
        where symbol = ?
        order by created_at desc, id desc
        limit 1
        """,
        (normalized,),
    ).fetchone()
    if not memory:
        return {"symbol": row_to_dict(stock), "memory": None, "scope": "shared"}

    item = row_to_dict(memory)
    import json

    item["reusable_json"] = json.loads(item["reusable_json"])
    item["must_refresh_json"] = json.loads(item["must_refresh_json"])
    item["invalidated_by"] = json.loads(item["invalidated_by"])
    return {"symbol": row_to_dict(stock), "memory": item, "scope": "shared"}


def all_stock_payloads(conn: sqlite3.Connection, query: str = "", account_id: str = DEFAULT_ACCOUNT_ID) -> list[dict[str, Any]]:
    active_sources = active_source_kinds_by_market(conn, account_id)
    source_ids = active_source_ids(conn, account_id)
    market_snapshots: dict[str, dict[str, Any]] = {}
    financial_snapshots: dict[str, dict[str, Any]] = {}
    news_snapshots: dict[str, dict[str, Any]] = latest_news_snapshots(conn)
    if "cn-baostock-history" in source_ids:
        merge_snapshots(market_snapshots, latest_snapshots(conn, "market_snapshots", "baostock-market"))
    if "cn-tushare-market" in source_ids:
        merge_snapshots(market_snapshots, latest_snapshots(conn, "market_snapshots", "tushare-market"))
    if "cn-akshare-market" in source_ids:
        merge_snapshots(market_snapshots, latest_snapshots(conn, "market_snapshots", "akshare-market"))
    if "us-finnhub-market" in source_ids:
        merge_snapshots(market_snapshots, latest_snapshots(conn, "market_snapshots", "finnhub-market"))
    if "cn-tushare-financial" in source_ids:
        merge_snapshots(financial_snapshots, latest_snapshots(conn, "financial_snapshots", "tushare-financial"))
    if "us-finnhub-financial" in source_ids:
        merge_snapshots(financial_snapshots, latest_snapshots(conn, "financial_snapshots", "finnhub-financial"))
    symbols = {
        row["symbol"]: row_to_dict(row)
        for row in conn.execute("select * from symbols order by market, symbol")
    }
    payloads = []
    for symbol in seed_data.STOCK_PROFILES:
        if symbol not in symbols:
            continue
        payloads.append(
            build_stock_payload(
                symbols[symbol],
                active_sources,
                market_snapshots.get(symbol),
                financial_snapshots.get(symbol),
                news_snapshots.get(symbol),
            )
        )

    if query:
        existing_symbols = {item["symbol"] for item in payloads}
        for symbol, row in symbols.items():
            if symbol in existing_symbols:
                continue
            if query not in symbol.lower() and query not in row["name"].lower():
                continue
            payloads.append(
                build_stock_payload(
                    row,
                    active_sources,
                    market_snapshots.get(symbol),
                    financial_snapshots.get(symbol),
                    news_snapshots.get(symbol),
                )
            )
    return payloads


def build_stock_payload(
    symbol_row: dict[str, Any],
    active_sources: dict[str, set[str]],
    market_snapshot: dict[str, Any] | None = None,
    financial_snapshot: dict[str, Any] | None = None,
    news_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    symbol = symbol_row["symbol"]
    profile = deepcopy(seed_data.STOCK_PROFILES.get(symbol) or default_profile(symbol_row))
    market = symbol_row["market"]
    active_kinds = active_sources.get(market, set())
    analysis_kinds = set(active_kinds)
    if "market" in analysis_kinds and not market_snapshot:
        analysis_kinds.remove("market")
    if "financial" in analysis_kinds and not financial_snapshot:
        analysis_kinds.remove("financial")
    if "news" in analysis_kinds and not news_snapshot:
        analysis_kinds.remove("news")
    missing_kinds = [kind for kind in ["market", "financial", "filing", "news"] if kind not in analysis_kinds]
    real_sources: list[str] = []

    if market_snapshot:
        apply_market_snapshot(profile, market_snapshot)
        real_sources.append(market_snapshot.get("provider") or "market")
    if financial_snapshot:
        apply_financial_snapshot(profile, financial_snapshot)
        real_sources.append(financial_snapshot.get("provider") or "financial")
    if news_snapshot:
        apply_news_snapshot(profile, news_snapshot)
        real_sources.append(news_snapshot.get("provider") or "news")
    if real_sources:
        profile["factors"] = score_metrics(profile["metrics"], profile["factors"])
        profile["score"] = round(sum(profile["factors"].values()) / len(profile["factors"]))
        profile["truth_score"] = min(96, max(profile["truth_score"], 82 + 5 * len(real_sources)))
        profile["action"] = action_for_score(profile["score"])
        profile["thesis"] = real_data_thesis(profile, market_snapshot, financial_snapshot, news_snapshot)

    factors = profile["factors"]
    if "financial" in missing_kinds:
        factors["基本面"] = min(factors["基本面"], 45)
        factors["估值"] = min(factors["估值"], 45)
    if "market" in missing_kinds:
        factors["技术"] = min(factors["技术"], 40)
        factors["风险"] = min(factors["风险"], 45)
        profile["freshness_status"] = "stale"
        profile["lag_minutes"] = max(profile["lag_minutes"], 240)
    if "news" in missing_kinds:
        factors["催化"] = min(factors["催化"], 50)
        factors["情绪"] = min(factors["情绪"], 45)
    if not financial_snapshot:
        clear_fundamental_metrics(profile["metrics"])
        if not market_snapshot:
            clear_valuation_metrics(profile["metrics"])
    if not news_snapshot:
        clear_news_metrics(profile["metrics"])

    evidence = [
        normalize_evidence_item(item, market)
        for item in profile["evidence"]
        if not template_evidence(item)
        and claim_allowed(item["source"], analysis_kinds)
    ]
    if "filing" in analysis_kinds:
        evidence.append(filing_source_status_evidence(market))
    if not evidence:
        evidence = [
            {
                "tier": "F",
                "source": "数据源设置",
                "claim": "当前市场未启用可用于分析的证据源，系统不会使用未勾选的数据源生成结论。",
                "confidence": 0,
            }
        ]

    missing_penalty = sum(12 for kind in missing_kinds if kind in {"market", "financial", "filing", "news"})
    score = max(0, min(profile["score"], round(sum(factors.values()) / len(factors)) - missing_penalty))
    truth_score = max(0, profile["truth_score"] - missing_penalty - (0 if "filing" not in missing_kinds else 8))

    blocked = "market" in missing_kinds or "filing" in missing_kinds
    action = "等待数据源" if blocked else profile["action"]
    thesis = profile["thesis"]
    if missing_kinds:
        missing_text = "、".join(missing_kind_label(kind, market_snapshot, financial_snapshot) for kind in missing_kinds)
        thesis = f"缺少可用于本次分析的{missing_text}数据；本次分析不会使用这些来源。{thesis}"

    return {
        "symbol": symbol,
        "name": symbol_row["name"],
        "market": market,
        "marketLabel": profile["market_label"],
        "currency": symbol_row["currency"],
        "price": profile["price"],
        "change": profile["change"],
        "action": action,
        "score": score,
        "lagMinutes": profile["lag_minutes"],
        "freshnessStatus": profile["freshness_status"],
        "truthScore": truth_score,
        "factors": factors,
        "spark": profile["spark"],
        "thesis": clean_analysis_text(thesis),
        "reasons": [clean_analysis_text(item) for item in profile["reasons"]],
        "risks": [clean_analysis_text(item) for item in profile["risks"]],
        "evidence": evidence,
        "reflection": [normalize_reflection_item(item) for item in profile["reflection"]],
        "metrics": camel_metrics(profile["metrics"]),
        "sourceStatus": {
            "activeKinds": sorted(active_kinds),
            "analysisKinds": sorted(analysis_kinds),
            "missingKinds": missing_kinds,
            "mode": "provider-cached" if real_sources else "provider-configured",
            "providers": real_sources,
            "marketSnapshot": snapshot_meta(market_snapshot),
            "financialSnapshot": snapshot_meta(financial_snapshot),
            "newsSnapshot": snapshot_meta(news_snapshot),
            "valuationBasis": valuation_basis(market_snapshot, financial_snapshot),
        },
    }


def normalize_evidence_item(item: dict[str, Any], market: str) -> dict[str, Any]:
    source = str(item.get("source") or "")
    return {
        **item,
        "source": normalize_evidence_source(source, market),
    }


def template_evidence(item: dict[str, Any]) -> bool:
    source = str(item.get("source") or "")
    return "Mock" in source or "mock" in source


def filing_source_status_evidence(market: str) -> dict[str, Any]:
    source = {
        "A": "CNINFO / 交易所公告",
        "HK": "HKEXnews 公告",
        "US": "SEC EDGAR 披露",
    }.get(market, "公告/披露数据源")
    return {
        "tier": "G",
        "source": source,
        "claim": "公告/披露数据源已启用；原文标题与链接需要在数据健康的公告/披露测试结果中核验。",
        "confidence": 0.55,
    }


def missing_kind_label(
    kind: str,
    market_snapshot: dict[str, Any] | None,
    financial_snapshot: dict[str, Any] | None,
) -> str:
    if kind == "financial" and market_snapshot and not financial_snapshot:
        return "财报财务快照（ROE/收入/现金流）"
    return SOURCE_KIND_LABELS.get(kind, kind)


def normalize_evidence_source(source: str, market: str) -> str:
    if "Mock" not in source and "mock" not in source:
        return source
    if "公告" in source or "HKEX" in source or "SEC" in source:
        if market == "HK":
            return "HKEXnews 公告"
        if market == "US":
            return "SEC EDGAR 披露"
        return "CNINFO / 交易所公告"
    if "财务" in source or "基本面" in source or "IR" in source:
        return "财务/估值数据源"
    if "新闻" in source or "情绪" in source or "社媒" in source:
        return "新闻情绪数据源"
    return source.replace(" Mock", "").replace(" mock", "").strip() or "数据源"


def normalize_reflection_item(item: dict[str, Any]) -> dict[str, Any]:
    return {**item, "text": clean_analysis_text(str(item.get("text") or ""))}


def clean_analysis_text(text: str) -> str:
    return (
        text.replace(" Mock", "")
        .replace(" mock ", " 数据源")
        .replace("mock ", "数据源")
        .replace("本原型", "当前环境")
        .replace("原型演示", "数据闸门")
        .replace("真实版本", "当前版本")
        .strip()
    )


def claim_allowed(source: str, active_kinds: set[str]) -> bool:
    if "公告" in source or "HKEX" in source or "SEC" in source:
        return "filing" in active_kinds
    if "财务" in source or "基本面" in source or "IR" in source:
        return "financial" in active_kinds
    if "新闻" in source or "社媒" in source or "情绪" in source:
        return "news" in active_kinds
    return True


def camel_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "avgAmountCny": metrics["avg_amount_cny"],
        "turnoverRate": metrics["turnover_rate"],
        "spreadBps": metrics["spread_bps"],
        "pe": metrics["pe"],
        "pePercentile": metrics["pe_percentile"],
        "pb": metrics["pb"],
        "roe": metrics["roe"],
        "revenueGrowth": metrics["revenue_growth"],
        "fcfMargin": metrics["fcf_margin"],
        "debtRatio": metrics["debt_ratio"],
        "volumeRatio": metrics["volume_ratio"],
        "ma20GapPct": metrics["ma20_gap_pct"],
        "atrPct": metrics["atr_pct"],
        "catalystScore": metrics["catalyst_score"],
        "newsCount72h": metrics["news_count_72h"],
        "verifiedCatalystRatio": metrics["verified_catalyst_ratio"],
        "sentimentScore": metrics["sentiment_score"],
        "unverifiedRatio": metrics["unverified_ratio"],
        "volatility20d": metrics["volatility_20d"],
        "maxDrawdown60d": metrics["max_drawdown_60d"],
    }


def latest_snapshots(conn: sqlite3.Connection, table: str, provider: str) -> dict[str, dict[str, Any]]:
    if table == "financial_snapshots":
        rows = conn.execute(
            """
            with ranked as (
              select *,
                row_number() over (
                  partition by symbol
                  order by period desc, id desc
                ) as rn
              from financial_snapshots
              where provider = ?
            )
            select * from ranked where rn = 1
            """,
            (provider,),
        )
    else:
        rows = conn.execute(
            """
            with ranked as (
              select *,
                row_number() over (
                  partition by symbol
                  order by as_of desc, fetched_at desc, id desc
                ) as rn
              from market_snapshots
              where provider = ?
            )
            select * from ranked where rn = 1
            """,
            (provider,),
        )
    snapshots: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = row_to_dict(row)
        if "raw_json" in item:
            item["raw"] = parse_json(item["raw_json"])
        snapshots[item["symbol"]] = item
    return snapshots


def merge_snapshots(target: dict[str, dict[str, Any]], incoming: dict[str, dict[str, Any]]) -> None:
    for symbol, snapshot in incoming.items():
        current = target.get(symbol)
        if current is None or snapshot_sort_key(snapshot) > snapshot_sort_key(current):
            target[symbol] = snapshot


def snapshot_sort_key(snapshot: dict[str, Any]) -> tuple[str, int, str, int]:
    provider = str(snapshot.get("provider") or "")
    freshness = str(snapshot.get("as_of") or snapshot.get("period") or "")
    fetched_at = str(snapshot.get("fetched_at") or "")
    row_id = int(snapshot.get("id") or 0)
    return (freshness, provider_priority(provider), fetched_at, row_id)


def provider_priority(provider: str) -> int:
    return {
        "tushare-market": 50,
        "akshare-market": 40,
        "baostock-market": 30,
        "finnhub-market": 30,
        "tushare-financial": 50,
        "finnhub-financial": 40,
        "alpha_vantage-news": 40,
    }.get(provider, 10)


def latest_news_snapshots(conn: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """
        select
          symbol,
          count(*) as count,
          max(published_at) as as_of,
          avg(sentiment_score) as sentiment_score,
          group_concat(distinct source) as sources
        from news_items
        where lower(source) not like '%mock%'
        group by symbol
        """
    )
    snapshots: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = row_to_dict(row)
        sources = [source for source in str(item.get("sources") or "").split(",") if source]
        item["provider"] = sources[0] if sources else "news"
        item["sources"] = sources
        snapshots[item["symbol"]] = item
    return snapshots


def default_profile(symbol_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "market_label": {"A": "A 股", "HK": "港股", "US": "美股"}.get(symbol_row["market"], symbol_row["market"]),
        "price": 0,
        "change": 0,
        "action": "等待数据",
        "score": 50,
        "lag_minutes": 9999,
        "freshness_status": "stale",
        "truth_score": 55,
        "factors": {"基本面": 50, "估值": 50, "技术": 50, "催化": 45, "情绪": 45, "风险": 55},
        "spark": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "thesis": "该股票来自真实数据源或搜索结果，当前只生成结构化快照，不生成买卖建议。",
        "reasons": ["等待更多行情、财务、公告和新闻证据后再进入完整分析。"],
        "risks": ["数据源不足时不能直接用于交易决策。"],
        "metrics": {
            "avg_amount_cny": 0,
            "turnover_rate": 0,
            "spread_bps": 10,
            "pe": 0,
            "pe_percentile": 50,
            "pb": 0,
            "roe": 0,
            "revenue_growth": 0,
            "fcf_margin": 0,
            "debt_ratio": 0,
            "volume_ratio": 1,
            "ma20_gap_pct": 0,
            "atr_pct": 3,
            "catalyst_score": 45,
            "news_count_72h": 0,
            "verified_catalyst_ratio": 0,
            "sentiment_score": 0,
            "unverified_ratio": 0,
            "volatility_20d": 25,
            "max_drawdown_60d": 10,
        },
        "evidence": [],
        "reflection": [
            {"round": "第 1 轮", "label": "数据闸门", "status": "warn", "text": "已拿到部分结构化数据，但公告和新闻证据仍不足。"},
            {"round": "第 2 轮", "label": "证据闸门", "status": "warn", "text": "真实版本需要补充可追溯公告、新闻和财务原文。"},
            {"round": "第 3 轮", "label": "投资逻辑", "status": "warn", "text": "当前只展示数据快照，不升级为交易动作。"},
        ],
    }


def apply_market_snapshot(profile: dict[str, Any], snapshot: dict[str, Any]) -> None:
    raw = snapshot.get("raw") or {}
    daily_basic = raw.get("daily_basic") or {}
    metrics = profile["metrics"]
    price = float(snapshot["price"])
    profile["price"] = price
    profile["change"] = float(raw.get("change") or 0)
    profile["lag_minutes"] = lag_minutes(snapshot.get("as_of"))
    profile["freshness_status"] = snapshot["freshness_status"]
    spark = profile.get("spark") or []
    profile["spark"] = ([price] * 10 if not any(spark) else [*spark[-9:], price])
    metrics["avg_amount_cny"] = float(snapshot["amount"])
    metrics["turnover_rate"] = float(snapshot["turnover_rate"])
    metrics["spread_bps"] = float(snapshot["spread_bps"])
    metrics["volume_ratio"] = float(daily_basic.get("volume_ratio") or raw.get("volume_ratio") or metrics["volume_ratio"])
    metrics["pe"] = float(raw.get("pe") or metrics["pe"])
    metrics["pb"] = float(raw.get("pb") or metrics["pb"])
    profile["evidence"].append(
        {
            "tier": "A",
            "source": provider_label(snapshot["provider"]),
            "claim": f"最新行情快照截至 {snapshot.get('as_of')}，收盘价 {price}，涨跌幅 {profile['change']}%。",
            "confidence": 0.86,
            "rawFields": {
                "provider": snapshot["provider"],
                "fetched_at": snapshot["fetched_at"],
                "amount": snapshot["amount"],
                "turnover_rate": snapshot["turnover_rate"],
            },
        }
    )


def apply_financial_snapshot(profile: dict[str, Any], snapshot: dict[str, Any]) -> None:
    metrics = profile["metrics"]
    metrics["revenue_growth"] = float(snapshot["revenue_growth"])
    metrics["roe"] = float(snapshot["roe"])
    metrics["fcf_margin"] = float(snapshot["fcf_margin"])
    metrics["debt_ratio"] = float(snapshot["debt_ratio"])
    if snapshot["pe"]:
        metrics["pe"] = float(snapshot["pe"])
    if snapshot["pb"]:
        metrics["pb"] = float(snapshot["pb"])
    profile["evidence"].append(
        {
            "tier": "A",
            "source": provider_label(snapshot["provider"]),
            "claim": f"财务快照期末 {snapshot.get('period')}，ROE {metrics['roe']}%，营收增速 {metrics['revenue_growth']}%。",
            "confidence": 0.84,
            "rawFields": {
                "provider": snapshot["provider"],
                "period": snapshot["period"],
                "pe": snapshot["pe"],
                "pb": snapshot["pb"],
            },
        }
    )


def apply_news_snapshot(profile: dict[str, Any], snapshot: dict[str, Any]) -> None:
    metrics = profile["metrics"]
    count = int(snapshot.get("count") or 0)
    sentiment_score = float(snapshot.get("sentiment_score") or 0)
    metrics["news_count_72h"] = count
    metrics["sentiment_score"] = sentiment_score
    profile["evidence"].append(
        {
            "tier": "B",
            "source": provider_label(snapshot.get("provider")),
            "claim": f"新闻缓存包含 {count} 条，最新发布时间 {snapshot.get('as_of')}，平均情绪分 {round(sentiment_score, 2)}。",
            "confidence": 0.72,
            "rawFields": {
                "provider": snapshot.get("provider"),
                "sources": snapshot.get("sources"),
                "latest_published_at": snapshot.get("as_of"),
            },
        }
    )


def clear_fundamental_metrics(metrics: dict[str, Any]) -> None:
    for key in ["roe", "revenue_growth", "fcf_margin", "debt_ratio"]:
        metrics[key] = None


def clear_valuation_metrics(metrics: dict[str, Any]) -> None:
    for key in ["pe", "pe_percentile", "pb"]:
        metrics[key] = None


def clear_news_metrics(metrics: dict[str, Any]) -> None:
    metrics["news_count_72h"] = 0
    metrics["verified_catalyst_ratio"] = None
    metrics["sentiment_score"] = None
    metrics["unverified_ratio"] = None


def score_metrics(metrics: dict[str, Any], previous: dict[str, int]) -> dict[str, int]:
    return {
        "基本面": round(
            average(
                [
                    high_score(metrics["roe"], 5, 25),
                    high_score(metrics["revenue_growth"], -10, 30),
                    high_score(metrics["fcf_margin"], -5, 20),
                    low_score(metrics["debt_ratio"], 85, 20),
                ]
            )
        ),
        "估值": round(average([low_score(metrics["pe"], 80, 10), low_score(metrics["pb"], 12, 1)])),
        "技术": round(
            average(
                [
                    high_score(metrics["volume_ratio"], 0.6, 2),
                    high_score(metrics["ma20_gap_pct"], -5, 8),
                    low_score(metrics["atr_pct"], 8, 1),
                ]
            )
        ),
        "催化": previous.get("催化", 45),
        "情绪": previous.get("情绪", 45),
        "风险": round(
            average(
                [
                    low_score(metrics["volatility_20d"], 60, 10),
                    low_score(metrics["max_drawdown_60d"], 30, 5),
                    low_score(metrics["spread_bps"], 20, 2),
                ]
            )
        ),
    }


def high_score(value: float, low: float, high: float) -> float:
    if high == low:
        return 50
    return max(0, min(100, (value - low) / (high - low) * 100))


def low_score(value: float, high_bad: float, low_good: float) -> float:
    if high_bad == low_good:
        return 50
    return max(0, min(100, (high_bad - value) / (high_bad - low_good) * 100))


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0


def action_for_score(score: int) -> str:
    if score >= 80:
        return "重点观察"
    if score >= 65:
        return "等待确认"
    if score >= 50:
        return "谨慎观察"
    return "等待数据"


def real_data_thesis(
    profile: dict[str, Any],
    market_snapshot: dict[str, Any] | None,
    financial_snapshot: dict[str, Any] | None,
    news_snapshot: dict[str, Any] | None,
) -> str:
    providers = sorted(
        {
            provider_label(snapshot.get("provider"))
            for snapshot in [market_snapshot, financial_snapshot, news_snapshot]
            if snapshot and snapshot.get("provider")
        }
    )
    parts = [f"已接入{'、'.join(providers) if providers else '真实数据源'}缓存"]
    if market_snapshot:
        parts.append(f"行情截至 {market_snapshot.get('as_of')}")
    if financial_snapshot:
        parts.append(f"财务期末 {financial_snapshot.get('period')}")
    if news_snapshot:
        parts.append(f"新闻最新 {news_snapshot.get('as_of')}")
    return "，".join(parts) + "。结论仍需结合公告、财务和新闻证据复核。"


def snapshot_meta(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not snapshot:
        return None
    return {
        "provider": snapshot.get("provider"),
        "asOf": snapshot.get("as_of") or snapshot.get("period"),
        "fetchedAt": snapshot.get("fetched_at"),
    }


def valuation_basis(
    market_snapshot: dict[str, Any] | None,
    financial_snapshot: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if financial_snapshot:
        return {
            "mode": "financial-snapshot",
            "label": provider_label(financial_snapshot.get("provider")),
            "asOf": financial_snapshot.get("period"),
        }
    if market_snapshot:
        return {
            "mode": "latest-market-with-prior-valuation",
            "label": "上一估值基线 + 最新行情",
            "asOf": market_snapshot.get("as_of"),
            "marketProvider": provider_label(market_snapshot.get("provider")),
        }
    return None


def lag_minutes(as_of: str | None) -> int:
    if not as_of:
        return 9999
    try:
        parsed = datetime.fromisoformat(as_of)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return max(0, round((datetime.now() - parsed).total_seconds() / 60))
    except (TypeError, ValueError):
        return 9999


def parse_json(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def provider_label(provider: str | None) -> str:
    if not provider:
        return "真实数据源"
    return PROVIDER_LABELS.get(provider, provider)
