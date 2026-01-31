from __future__ import annotations

def slippage_bps(price: float, mid: float) -> float:
    if not price or not mid:
        return 0.0
    return abs((price - mid) / mid) * 10000.0
