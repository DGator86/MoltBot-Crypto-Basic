from __future__ import annotations
import pandas as pd
import numpy as np


def sharpe(returns: pd.Series, ann_factor: int = 365) -> float:
    mu = returns.mean()
    sd = returns.std()
    if sd == 0 or np.isnan(sd):
        return 0.0
    return float((mu / sd) * (ann_factor**0.5))


def win_rate(returns: pd.Series) -> float:
    pos = (returns > 0).sum()
    neg = (returns <= 0).sum()
    tot = pos + neg
    return float(pos / tot) if tot else 0.0


def pass_fail(df: pd.DataFrame, min_sharpe: float = 1.0, min_equity: float = 1.05) -> dict:
    s = sharpe(df['strat_ret'])
    eq = float(df['equity'].iloc[-1]) if len(df) else 1.0
    return {
        'sharpe': s,
        'final_equity': eq,
        'pass': bool(s >= min_sharpe and eq >= min_equity)
    }
