from __future__ import annotations

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
