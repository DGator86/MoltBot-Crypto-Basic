from __future__ import annotations
import pandas as pd
from ..features.build_features import make_basic_features
from .cost_model import apply_costs


def ema_crossover_backtest(df: pd.DataFrame, fee_bps: float = 5.0, slippage_bps: float = 5.0) -> pd.DataFrame:
    data = make_basic_features(df)
    data['signal'] = (data['ema_fast'] > data['ema_slow']).astype(int)
    data['ret'] = data['close'].pct_change().fillna(0)
    data['strat_ret_raw'] = data['signal'].shift(1).fillna(0) * data['ret']
    data['strat_ret'] = apply_costs(data['strat_ret_raw'], fee_bps=fee_bps, slippage_bps=slippage_bps)
    data['equity'] = (1 + data['strat_ret']).cumprod()
    return data
