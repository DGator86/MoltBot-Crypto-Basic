from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal

class Trade(BaseModel):
    venue: str
    symbol: str
    ts: int  # epoch ms
    price: float
    size: float
    side: Literal["buy", "sell"]

class Kline(BaseModel):
    venue: str
    symbol: str
    start_ts: int
    end_ts: int
    o: float
    h: float
    l: float
    c: float
    v: float

class OrderBookDelta(BaseModel):
    venue: str
    symbol: str
    ts: int
    bids: list[tuple[float, float]] = Field(default_factory=list)
    asks: list[tuple[float, float]] = Field(default_factory=list)
