from __future__ import annotations
import numpy as np
from typing import Dict, Any

def simulate_paths(
    p0: float,
    v0: float,
    grid: np.ndarray,
    U: np.ndarray,
    F_flow: float,
    sigma_local: float,
    alpha: float,
    beta: float,
    gamma: float,
    steps: int = 250,
    n_paths: int = 2000,
    seed: int = 7,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    gradU = np.gradient(U, grid)

    def g(p):
        return np.interp(p, grid, gradU)

    P = np.zeros((n_paths, steps + 1), dtype=float)
    V = np.zeros((n_paths,), dtype=float)
    P[:, 0] = p0
    V[:] = v0

    for k in range(steps):
        eps = rng.normal(0.0, sigma_local, size=n_paths)
        V = alpha * V - beta * g(P[:, k]) + gamma * F_flow + eps
        P[:, k + 1] = P[:, k] + V

    return P

def cone_summary(paths: np.ndarray, qs=(0.05, 0.25, 0.5, 0.75, 0.95)) -> Dict[str, Any]:
    return {
        "bands": {str(q): np.quantile(paths, q, axis=0).tolist() for q in qs},
        "mean": np.mean(paths, axis=0).tolist(),
    }

def touch_probability(paths: np.ndarray, level: float) -> float:
    touched = np.any(paths >= level, axis=1) if level >= paths[:,0].mean() else np.any(paths <= level, axis=1)
    return float(np.mean(touched))
