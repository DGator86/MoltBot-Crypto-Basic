from __future__ import annotations
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Literal, Dict, Any
from datetime import datetime


class Symbol(str, Enum):
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"


class Venue(str, Enum):
    MOCK = "mock"
    BINANCE = "binance"
    COINBASE = "coinbase"
    BYBIT = "bybit"
    OKX = "okx"
    DERIBIT = "deribit"
    OTHER = "other"


class EventType(str, Enum):
    TRADE_PRINT = "trade_print"
    BOOK_DELTA = "book_delta"
    FUNDING_TICK = "funding_tick"
    OI_TICK = "oi_tick"
    BASIS_TICK = "basis_tick"
    LIQUIDATION_SNAPSHOT = "liquidation_snapshot"
    ONCHAIN_SNAPSHOT = "onchain_snapshot"
    MACRO_SNAPSHOT = "macro_snapshot"


class BaseEvent(BaseModel):
    ts: datetime
    recv_ts: datetime
    symbol: Symbol
    venue: Venue
    etype: EventType
    meta: Dict[str, Any] = Field(default_factory=dict)


class TradeSide(str, Enum):
    BUY = "buy"          # aggressor buy
    SELL = "sell"        # aggressor sell
    UNKNOWN = "unknown"


class TradePrint(BaseEvent):
    etype: Literal[EventType.TRADE_PRINT] = EventType.TRADE_PRINT
    price: float
    size: float          # base units
    side: TradeSide = TradeSide.UNKNOWN


class BookLevel(BaseModel):
    price: float
    size: float


class BookDelta(BaseEvent):
    etype: Literal[EventType.BOOK_DELTA] = EventType.BOOK_DELTA
    bids: list[BookLevel]   # descending
    asks: list[BookLevel]   # ascending
    depth_n: int = 20


class FundingTick(BaseEvent):
    etype: Literal[EventType.FUNDING_TICK] = EventType.FUNDING_TICK
    funding_rate: float
    next_funding_ts: Optional[datetime] = None


class OITick(BaseEvent):
    etype: Literal[EventType.OI_TICK] = EventType.OI_TICK
    open_interest: float


class BasisTick(BaseEvent):
    etype: Literal[EventType.BASIS_TICK] = EventType.BASIS_TICK
    basis: float
    basis_type: str = "perp_minus_spot"


class LiquidationSnapshot(BaseEvent):
    etype: Literal[EventType.LIQUIDATION_SNAPSHOT] = EventType.LIQUIDATION_SNAPSHOT
    bands: list[tuple[float, float]]


class OnchainSnapshot(BaseEvent):
    etype: Literal[EventType.ONCHAIN_SNAPSHOT] = EventType.ONCHAIN_SNAPSHOT
    metrics: Dict[str, float]


class MacroSnapshot(BaseEvent):
    etype: Literal[EventType.MACRO_SNAPSHOT] = EventType.MACRO_SNAPSHOT
    metrics: Dict[str, float]
