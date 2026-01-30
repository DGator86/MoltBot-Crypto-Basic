from __future__ import annotations
import pandas as pd
import numpy as np


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / (loss + 1e-12)
    return 100 - (100 / (1 + rs))


def make_basic_features(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    out = df.copy()
    out['ema_fast'] = ema(out[price_col], 20)
    out['ema_slow'] = ema(out[price_col], 100)
    out['rsi_14'] = rsi(out[price_col], 14)
    return out
