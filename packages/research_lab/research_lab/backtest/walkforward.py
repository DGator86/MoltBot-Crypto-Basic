from __future__ import annotations
import pandas as pd
from .engine import ema_crossover_backtest


def walkforward(df: pd.DataFrame, n_splits: int = 3):
    n = len(df)
    split = n // (n_splits + 1)
    results = []
    for i in range(n_splits):
        train = df.iloc[: (i+1)*split]
        test = df.iloc[(i+1)*split : (i+2)*split]
        res = ema_crossover_backtest(test)
        results.append({
            'split': i,
            'test_start': test.index.min(),
            'test_end': test.index.max(),
            'final_equity': float(res['equity'].iloc[-1]) if len(res) else 1.0,
            'avg_ret': float(res['strat_ret'].mean()) if len(res) else 0.0,
        })
    return results
