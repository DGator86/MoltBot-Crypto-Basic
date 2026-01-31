from __future__ import annotations
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

# Basic feature set aligned with earlier build_features

def make_features(df: pd.DataFrame, price_col: str = 'close', windows: Dict[str, int] | None = None) -> pd.DataFrame:
    w = windows or {"ema_fast": 20, "ema_slow": 100, "rv": 50}
    out = df.copy()
    out['ret'] = out[price_col].pct_change().fillna(0)
    out['ema_fast'] = out[price_col].ewm(span=w['ema_fast'], adjust=False).mean()
    out['ema_slow'] = out[price_col].ewm(span=w['ema_slow'], adjust=False).mean()
    out['rv'] = out['ret'].rolling(w['rv']).std().fillna(method='bfill').fillna(0)
    # RSI(14)
    delta = out[price_col].diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(gain, index=out.index).rolling(14).mean()
    roll_down = pd.Series(loss, index=out.index).rolling(14).mean()
    rs = roll_up / (roll_down + 1e-12)
    out['rsi_14'] = 100 - (100 / (1 + rs))
    # Directional strength proxy
    out['dir_strength'] = (out['ema_fast'] - out['ema_slow']).abs() / (out['rv'] + 1e-9)
    out.replace([np.inf, -np.inf], 0.0, inplace=True)
    return out


def label_kingdom(feats: pd.DataFrame) -> pd.Series:
    ds = feats['dir_strength'].clip(0, 5)
    # mean reversion proxy: small ds and high oscillation (use RSI near 50 as neutral)
    mr = (feats['rsi_14'].between(45, 55)).astype(int)
    labels = pd.Series(index=feats.index, dtype=object)
    labels[ds > 1.2] = 'trend'
    labels[(ds <= 1.2) & (mr == 1)] = 'mean_revert'
    labels = labels.fillna('range')
    return labels


def label_phylum(feats: pd.DataFrame) -> pd.Series:
    # vol regime by realized vol percentiles
    rv = feats['rv']
    p = rv.rank(pct=True)
    lab = pd.Series(index=feats.index, dtype=object)
    lab[p < 0.15] = 'compression'
    lab[p > 0.75] = 'expansion'
    lab[(p >= 0.15) & (p <= 0.6)] = 'decay'
    lab[(p > 0.6) & (p <= 0.75)] = 'elevated'
    return lab


def build_dataset(ohlcv: List[Dict[str, Any]], level: str, windows: Dict[str, int] | None = None) -> Tuple[pd.DataFrame, pd.Series]:
    df = pd.DataFrame(ohlcv)
    # Accept either list with 'ts' or simple index; ensure monotonic index
    if 'ts' in df.columns:
        df = df.sort_values('ts').rename(columns={'ts':'index'}).set_index('index')
    feats = make_features(df, windows=windows)
    X = feats[['ret','ema_fast','ema_slow','rv','rsi_14','dir_strength']].dropna()
    if level == 'kingdom':
        y = label_kingdom(feats.loc[X.index])
    elif level == 'phylum':
        y = label_phylum(feats.loc[X.index])
    else:
        raise ValueError('level not supported yet (kingdom|phylum)')
    # Align sizes
    y = y.loc[X.index]
    return X, y
