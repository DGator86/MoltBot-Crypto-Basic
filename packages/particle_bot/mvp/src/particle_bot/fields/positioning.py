from __future__ import annotations
from typing import Dict, Any
import numpy as np

def positioning_potential(grid: np.ndarray, features: Dict[str, Any], p0: float, sigma: float) -> np.ndarray:
    """Crowding pressure: create a hump against the direction of crowded positioning.
    This is a crude MVP. Replace with liquidation bands later.
    """
    U = np.zeros_like(grid)
    fz = features.get("funding_z", 0.0)
    oiz = features.get("oi_z", 0.0)

    crowd = max(0.0, abs(fz) + max(0.0, oiz)) / 3.0
    crowd = min(1.0, crowd)

    if crowd <= 0.05 or sigma <= 0:
        return U

    # If funding_z positive => longs crowded => upward moves face resistance (hump above p0)
    direction = 1.0 if fz > 0 else -1.0
    center = p0 + direction * 2.0 * max(sigma, 1e-9) * 10.0  # sigma in price/print; scale up
    width = 2.5 * max(sigma, 1e-9) * 10.0

    hump = np.exp(-0.5 * ((grid - center) / width) ** 2)
    U += hump * crowd * 0.75  # higher U => repulsive barrier

    return U
