from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol

from .. import seed_data


class MarketProvider(Protocol):
    provider_name: str

    def snapshots(self, fetched_at: str) -> list[dict[str, Any]]:
        ...


class FinancialProvider(Protocol):
    provider_name: str

    def snapshots(self) -> list[dict[str, Any]]:
        ...


class NewsProvider(Protocol):
    provider_name: str

    def news_items(self) -> list[dict[str, Any]]:
        ...

    def claims(self) -> list[dict[str, Any]]:
        ...


class MockMarketProvider:
    provider_name = "mock-market"
    provider_version = "phase1e-v1"

    def snapshots(self, fetched_at: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for symbol, profile in seed_data.STOCK_PROFILES.items():
            metrics = profile["metrics"]
            rows.append(
                {
                    "symbol": symbol,
                    "provider": self.provider_name,
                    "as_of": "2026-06-05T15:00:00+08:00",
                    "fetched_at": fetched_at,
                    "price": profile["price"],
                    "volume": round(metrics["avg_amount_cny"] / max(profile["price"], 1)),
                    "amount": metrics["avg_amount_cny"],
                    "turnover_rate": metrics["turnover_rate"],
                    "spread_bps": metrics["spread_bps"],
                    "raw_json": {
                        "change": profile["change"],
                        "lag_minutes": profile["lag_minutes"],
                        "score": profile["score"],
                        "freshness_status": profile["freshness_status"],
                        "spark": profile["spark"],
                        "volume_ratio": metrics["volume_ratio"],
                        "ma20_gap_pct": metrics["ma20_gap_pct"],
                        "atr_pct": metrics["atr_pct"],
                        "volatility_20d": metrics["volatility_20d"],
                        "max_drawdown_60d": metrics["max_drawdown_60d"],
                    },
                    "freshness_status": profile["freshness_status"],
                }
            )
        return rows


class MockFinancialProvider:
    provider_name = "mock-financial"
    provider_version = "phase1e-v1"

    def snapshots(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for symbol, profile in seed_data.STOCK_PROFILES.items():
            metrics = profile["metrics"]
            rows.append(
                {
                    "symbol": symbol,
                    "period": "2026Q1-mock",
                    "provider": self.provider_name,
                    "revenue_growth": metrics["revenue_growth"],
                    "roe": metrics["roe"],
                    "fcf_margin": metrics["fcf_margin"],
                    "debt_ratio": metrics["debt_ratio"],
                    "pe": metrics["pe"],
                    "pb": metrics["pb"],
                    "raw_json": {
                        "pe_percentile": metrics["pe_percentile"],
                        "catalyst_score": metrics["catalyst_score"],
                        "verified_catalyst_ratio": metrics["verified_catalyst_ratio"],
                        "unverified_ratio": metrics["unverified_ratio"],
                        "news_count_72h": metrics["news_count_72h"],
                        "sentiment_score": metrics["sentiment_score"],
                    },
                }
            )
        return rows


class MockNewsProvider:
    provider_name = "mock-news"
    provider_version = "phase1e-v1"

    def news_items(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for symbol, profile in seed_data.STOCK_PROFILES.items():
            metrics = profile["metrics"]
            rows.append(
                {
                    "symbol": symbol,
                    "source": self.provider_name,
                    "source_tier": "B",
                    "title": f"{symbol} mock 72小时新闻与情绪摘要",
                    "url": official_url(symbol),
                    "published_at": "2026-06-05T14:30:00+08:00",
                    "summary": "当前仍为 mock 新闻摘要，只用于验证新闻快照、情绪分和未证实比例的数据边界。",
                    "sentiment_score": metrics["sentiment_score"],
                    "raw_text_hash": stable_hash({"symbol": symbol, "news_count": metrics["news_count_72h"]}),
                }
            )
        return rows

    def claims(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for symbol, profile in seed_data.STOCK_PROFILES.items():
            for index, item in enumerate(profile["evidence"], start=1):
                rows.append(
                    {
                        "symbol": symbol,
                        "claim_text": item["claim"],
                        "claim_type": claim_type_for(item["source"]),
                        "source_tier": item["tier"],
                        "source": item["source"],
                        "source_url": official_url(symbol) if item["tier"] != "C" else "",
                        "confidence": item["confidence"],
                        "truth_status": "mock_verified" if item["tier"] in {"S", "A"} else "needs_review",
                        "raw_json": {"claim_index": index, "provider": self.provider_name},
                    }
                )
        return rows


class MockProviderSet:
    def __init__(self) -> None:
        self.market = MockMarketProvider()
        self.financial = MockFinancialProvider()
        self.news = MockNewsProvider()

    @property
    def provider_set_hash(self) -> str:
        versions = [
            self.market.provider_version,
            self.financial.provider_version,
            self.news.provider_version,
        ]
        return stable_hash({"providers": versions})[:16]

    def factor_runs(self, as_of: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        provider_hash = self.provider_set_hash
        for symbol, profile in seed_data.STOCK_PROFILES.items():
            metrics = profile["metrics"]
            for factor_name, score in profile["factors"].items():
                rows.append(
                    {
                        "symbol": symbol,
                        "as_of": as_of,
                        "factor_name": factor_name,
                        "score": score,
                        "inputs_json": factor_inputs(factor_name, metrics),
                        "method_version": "mock-factor-v1",
                        "provider_set_hash": provider_hash,
                    }
                )
        return rows


def factor_inputs(factor_name: str, metrics: dict[str, Any]) -> dict[str, Any]:
    groups = {
        "基本面": ["roe", "revenue_growth", "fcf_margin", "debt_ratio"],
        "估值": ["pe", "pe_percentile", "pb"],
        "技术": ["ma20_gap_pct", "volume_ratio", "atr_pct", "max_drawdown_60d"],
        "催化": ["catalyst_score", "news_count_72h", "verified_catalyst_ratio", "unverified_ratio"],
        "情绪": ["sentiment_score", "unverified_ratio", "news_count_72h"],
        "风险": ["volatility_20d", "max_drawdown_60d", "atr_pct", "spread_bps"],
    }
    return {key: metrics[key] for key in groups.get(factor_name, [])}


def claim_type_for(source: str) -> str:
    if "公告" in source or "HKEX" in source or "SEC" in source:
        return "filing"
    if "财务" in source or "基本面" in source or "IR" in source:
        return "financial"
    if "社媒" in source:
        return "sentiment"
    return "news"


def official_url(symbol: str) -> str:
    if symbol in {"NVDA", "AAPL"}:
        return "https://www.sec.gov/search-filings/edgar-application-programming-interfaces"
    if symbol.endswith(".HK"):
        return "https://www.hkexnews.hk/index.htm"
    if symbol.endswith(".SH"):
        return "https://www.sse.com.cn/disclosure/listedinfo/announcement/"
    return "https://www.szse.cn/disclosure/listed/notice/index.html"


def stable_hash(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
