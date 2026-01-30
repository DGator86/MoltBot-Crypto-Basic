from __future__ import annotations
import pandas as pd


def apply_costs(returns: pd.Series, fee_bps: float = 5.0, slippage_bps: float = 5.0) -> pd.Series:
    cost = (fee_bps + slippage_bps) / 10000.0
    return returns - cost.abs()
