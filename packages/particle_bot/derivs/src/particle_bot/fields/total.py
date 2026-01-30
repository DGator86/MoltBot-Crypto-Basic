from __future__ import annotations
from typing import Dict
import numpy as np

def total_potential(components: Dict[str, np.ndarray], weights: Dict[str, float]) -> np.ndarray:
    keys = list(components.keys())
    if not keys:
        raise ValueError("No potential components provided")
    U = np.zeros_like(components[keys[0]])
    for k, arr in components.items():
        U += weights.get(k, 1.0) * arr
    return U

def grad(U: np.ndarray, grid: np.ndarray) -> np.ndarray:
    return np.gradient(U, grid)
