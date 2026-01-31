from __future__ import annotations

def deflated_metric(metric: float, trials: int = 10) -> float:
    penalty = 0.1 * max(0, trials - 1)
    return max(0.0, metric - penalty)
