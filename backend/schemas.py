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
    filter_ids: list[str] = Field(default_factory=list)
    mode: str = "all"
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
