from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List


@dataclass(frozen=True)
class Scale:
    name: str
    trade_count: Optional[int] = None
    sigma_window_trades: Optional[int] = None
    sigma_k: Optional[float] = None


DEFAULT_SCALES: List[Scale] = [
    Scale("micro", trade_count=500, sigma_window_trades=2000, sigma_k=1.0),
    Scale("minor", trade_count=2000, sigma_window_trades=5000, sigma_k=1.5),
    Scale("major", trade_count=8000, sigma_window_trades=15000, sigma_k=2.0),
    Scale("macro", trade_count=30000, sigma_window_trades=60000, sigma_k=3.0),
]
