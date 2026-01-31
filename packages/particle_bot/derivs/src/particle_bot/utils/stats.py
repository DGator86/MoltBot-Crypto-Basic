from __future__ import annotations
import math
from typing import Iterable, Optional


def mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    return sum(xs) / max(len(xs), 1)


def stdev(xs: Iterable[float]) -> float:
    xs = list(xs)
    n = len(xs)
    if n < 2:
        return 0.0
    m = sum(xs) / n
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return math.sqrt(max(var, 0.0))


def zscore(x: float, mu: float, sd: float, eps: float = 1e-12) -> float:
    return (x - mu) / max(sd, eps)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
