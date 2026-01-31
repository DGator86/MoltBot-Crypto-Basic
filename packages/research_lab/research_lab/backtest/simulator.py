from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import math

@dataclass
class SimOrder:
    client_id: str
    side: str           # 'buy' or 'sell'
    type: str           # 'market' or 'limit'
    size: float
    price: Optional[float] = None
    reduce_only: bool = False

@dataclass
class Fill:
    ts: int
    price: float
    size: float

@dataclass
class OrderState:
    order: SimOrder
    status: str = 'new'     # new -> open/partially_filled/filled/rejected/canceled
    filled: float = 0.0
    avg_fill_price: float = 0.0
    fills: List[Fill] = field(default_factory=list)
    reason: Optional[str] = None

@dataclass
class SimConfig:
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    post_only: bool = False
    latency_ms: int = 0
    partial_fill_prob: float = 0.3

@dataclass
class Account:
    base_pos: float = 0.0     # base units
    quote: float = 0.0        # quote currency
    equity: float = 0.0


def simulate_paper(ohlc: List[Dict[str, Any]], orders: List[SimOrder], cfg: SimConfig) -> Dict[str, Any]:
    """
    Very simple per-tick simulator using close prices as mid, applying:
    - optional latency
    - partial fills with probability
    - fees & slippage
    - reduceOnly enforcement
    """
    ts_list = [int(x.get('ts', i)) for i, x in enumerate(ohlc)]
    px_list = [float(x['close']) for x in ohlc]

    # index orders by client_id, enforce idempotency
    book: Dict[str, OrderState] = {}
    acct = Account(base_pos=0.0, quote=0.0, equity=0.0)

    fees = 0.0

    for idx, (ts, mid) in enumerate(zip(ts_list, px_list)):
        # process any new orders that arrive at this ts (no latency queue for brevity)
        for o in list(orders):
            if o.client_id in book:
                continue  # idempotent
            # simulate immediate acceptance
            st = OrderState(order=o, status='open')
            book[o.client_id] = st

        # walk open orders
        for st in book.values():
            if st.status not in ('open', 'partially_filled'):
                continue
            o = st.order
            # limit crossing check
            px_exec = mid
            if o.type == 'limit':
                if o.side == 'buy' and (o.price is None or o.price < mid):
                    continue
                if o.side == 'sell' and (o.price is None or o.price > mid):
                    continue
            # post-only reject if crossing
            if cfg.post_only and o.type == 'limit':
                st.status = 'rejected'
                st.reason = 'post_only_cross'
                continue
            # compute slippage
            px = px_exec * (1 + (cfg.slippage_bps/10000.0) * (1 if o.side == 'buy' else -1))
            # partial fill amount
            remaining = o.size - st.filled
            fill_size = remaining
            # probabilistic partials
            if remaining > 0 and cfg.partial_fill_prob > 0.0:
                import random
                if random.random() < cfg.partial_fill_prob:
                    fill_size = remaining * 0.25
            if fill_size <= 0:
                continue
            # apply fill
            st.fills.append(Fill(ts=ts, price=px, size=fill_size))
            st.filled += fill_size
            st.avg_fill_price = ((st.avg_fill_price * (st.filled - fill_size)) + px * fill_size) / max(st.filled, 1e-12)
            if abs(st.filled - o.size) < 1e-12:
                st.status = 'filled'
            else:
                st.status = 'partially_filled'
            # reduceOnly enforcement: only decrease position
            delta = fill_size if o.side == 'buy' else -fill_size
            if o.reduce_only and ((acct.base_pos > 0 and delta > 0) or (acct.base_pos < 0 and delta < 0)):
                st.status = 'rejected'
                st.reason = 'reduce_only_violation'
                continue
            # update positions and cash
            if o.side == 'buy':
                acct.base_pos += fill_size
                acct.quote -= px * fill_size
            else:
                acct.base_pos -= fill_size
                acct.quote += px * fill_size
            # fees
            fees += abs(px * fill_size) * (cfg.fee_bps/10000.0)

        # recompute equity as mark-to-market
        acct.equity = acct.quote + acct.base_pos * mid

    return {
        'orders': [st.__dict__ | {'fills': [f.__dict__ for f in st.fills]} for st in book.values()],
        'account': acct.__dict__,
        'fees': fees
    }
