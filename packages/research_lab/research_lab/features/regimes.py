from __future__ import annotations
import pandas as pd
import numpy as np


def realized_vol(prices: pd.Series, window: int = 30) -> pd.Series:
    r = np.log(prices).diff()
    return r.rolling(window).std() * (365**0.5)


def trend_slope(prices: pd.Series, window: int = 50) -> pd.Series:
    return prices.pct_change(window)


def label_regimes(df: pd.DataFrame, price_col: str = 'close') -> pd.Series:
    vol = realized_vol(df[price_col])
    slope = trend_slope(df[price_col])
    regime = pd.Series(index=df.index, dtype='object')
    regime[(vol <= vol.quantile(0.5)) & (slope.abs() < 0.02)] = 'low_vol_chop'
    regime[(vol > vol.quantile(0.5)) & (slope.abs() >= 0.02)] = 'trend_high_vol'
    regime = regime.fillna('other')
    return regime
