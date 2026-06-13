from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FavoriteToggle(BaseModel):
    favorite: bool
    note: str = ""


class TradeInput(BaseModel):
    symbol: str
    side: str
    date: str
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    fee: float = Field(default=0, ge=0)


class AnomalyInput(BaseModel):
    scope_type: str = "question"
    scope_key: str = "manual"
    question: str


class DataSourceUpdate(BaseModel):
    enabled: bool | None = None
    credential: str = ""
    clear_credential: bool = False


class ScreenerInput(BaseModel):
    market: str = "all"
    industry: str = ""
    filter_ids: list[str] = Field(default_factory=list)
    mode: str = "all"
    natural_query: str = ""
    account_id: str = "acct-admin"


class BacktestInput(BaseModel):
    market: str = "all"
    strategy: str = "quality_momentum"
    start_date: str = "2026-03-02"
    end_date: str = "2026-06-05"
    max_positions: int = Field(default=3, ge=1, le=10)
    initial_cash: float = Field(default=1000000, gt=0)
    fee_bps: float = Field(default=8, ge=0, le=100)
    slippage_bps: float = Field(default=5, ge=0, le=100)
    rebalance: str = "monthly"


class DataRefreshInput(BaseModel):
    scope: str = "all"
    account_id: str | None = None
    provider: str = "auto"
    symbols: list[str] = Field(default_factory=list)
    refresh_universe: bool = False


class DataSourceTestInput(BaseModel):
    test_id: str
    symbol: str = ""
    account_id: str = "acct-admin"
    params: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class SearchHistoryInput(BaseModel):
    account_id: str = "acct-admin"
    surface: str
    query: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SentimentRefreshInput(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    days: int = Field(default=30, ge=1, le=365)
    use_llm: bool = True
    crawl_community: bool = False
    community_limit: int = Field(default=120, ge=1, le=200)
    evidence_limit: int = Field(default=120, ge=1, le=200)


class CommunityCrawlInput(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    source: str = "eastmoney_guba"
    limit: int = Field(default=120, ge=1, le=200)
    timeout: int = Field(default=15, ge=3, le=60)
    sleep_seconds: float = Field(default=0.8, ge=0, le=10)


class CommunitySentimentCycleInput(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    use_llm: bool = True
    community_limit: int = Field(default=120, ge=1, le=200)
    evidence_limit: int = Field(default=120, ge=1, le=200)
    analysis_days: int = Field(default=30, ge=1, le=365)
    retention_days: int = Field(default=3, ge=1, le=30)
    refresh_market: bool = True
    refresh_filings: bool = True
    market_days: int = Field(default=20, ge=3, le=80)
