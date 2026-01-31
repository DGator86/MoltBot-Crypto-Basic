from __future__ import annotations
from typing import Dict, Any, Tuple
import numpy as np

def build_price_grid(p0: float, sigma: float, n: int = 401) -> np.ndarray:
    span = 6.0 * max(sigma, 1e-9)
    return np.linspace(p0 - span, p0 + span, n)

def liquidity_potential(grid: np.ndarray, book: Dict[str, Any] | None, p0: float) -> np.ndarray:
    """Construct a simple potential where high depth == low potential (attractor).
    We invert depth so wells are negative values.
    """
    U = np.zeros_like(grid)

    if not book:
        return U

    bids = book.get("bids", [])
    asks = book.get("asks", [])
    # Turn discrete depths into gaussian bumps around each level
    def add_levels(levels, sign):
        for px, sz in levels[:20]:
            width = max(1.0, abs(px - p0) * 0.02 + 5.0)
            bump = np.exp(-0.5 * ((grid - px) / width) ** 2) * sz
            # more depth -> more attractive -> lower U
            U[:] -= bump * 0.002

    add_levels(bids, -1)
    add_levels(asks, +1)

    # gentle restoring term to keep numeric sane
    U += 1e-6 * (grid - p0) ** 2
    return U
