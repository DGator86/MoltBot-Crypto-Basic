from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, Literal

class NewOrderRequest(BaseModel):
    venue: str
    symbol: str
    side: Literal["buy", "sell"]
    type: Literal["market", "limit"]
    size: float
    price: Optional[float] = None
    client_id: Optional[str] = None

class OrderAck(BaseModel):
    order_id: str
    client_id: Optional[str] = None
    status: str
