from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Order:
    client_id: str
    venue: str
    symbol: str
    side: str
    type: str
    size: float
    price: float | None = None

@dataclass
class OrderEvent:
    ts: int
    type: str   # new, accepted, partially_filled, filled, rejected, canceled
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OrderRecord:
    order: Order
    status: str = 'new'
    filled: float = 0.0
    avg_price: float = 0.0
    events: List[OrderEvent] = field(default_factory=list)

class OrderManager:
    def __init__(self):
        self._orders: Dict[str, OrderRecord] = {}

    def submit(self, o: Order) -> OrderRecord:
        if o.client_id in self._orders:
            return self._orders[o.client_id]
        rec = OrderRecord(order=o, status='accepted')
        rec.events.append(OrderEvent(ts=0, type='accepted'))
        self._orders[o.client_id] = rec
        return rec

    def update_fill(self, client_id: str, fill_size: float, price: float) -> OrderRecord:
        rec = self._orders[client_id]
        prev = rec.filled
        rec.filled += fill_size
        rec.avg_price = ((rec.avg_price * prev) + price * fill_size) / max(rec.filled, 1e-12)
        rec.status = 'filled' if abs(rec.filled - rec.order.size) < 1e-12 else 'partially_filled'
        rec.events.append(OrderEvent(ts=0, type=rec.status, data={'fill': fill_size, 'price': price}))
        return rec

    def cancel(self, client_id: str) -> OrderRecord:
        rec = self._orders[client_id]
        rec.status = 'canceled'
        rec.events.append(OrderEvent(ts=0, type='canceled'))
        return rec

    def get(self, client_id: str) -> OrderRecord:
        return self._orders[client_id]
