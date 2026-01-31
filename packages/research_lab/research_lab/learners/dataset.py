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


def build_dataset(ohlcv: List[Dict[str, Any]], level: str, windows: Dict[str, int] | None = None, aux: Dict[str, Any] | None = None) -> Tuple[pd.DataFrame, pd.Series]:
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
    elif level in ('clazz','order','family'):
        pass
    else:
        raise ValueError('level not supported yet (kingdom|phylum|clazz|order|family)')

    if level == 'clazz':
        feats = add_class_features(feats, aux)
        X = feats[['ret','ema_fast','ema_slow','rv','rsi_14','dir_strength','funding','oi','basis']].dropna()
        y = label_clazz(feats.loc[X.index])
    elif level == 'order':
        feats = add_order_features(feats)
        X = feats[['ret','rv','dir_strength','profile_var','dist_avwap']].dropna()
        y = label_order(feats.loc[X.index])
    elif level == 'family':
        feats = add_family_features(feats)
        X = feats[['ret','rv','dir_strength','impulse','exhaustion','progress_sigma','vol_mult']].dropna()
        y = label_family(feats.loc[X.index])

    if level in ('clazz','order','family'):
        # y already set above
        ...

    # Align sizes
    y = y.loc[X.index]
    return X, y


# ----- Extended features and labels for Class / Order / Family -----
# NOTE: These use proxies when derivatives/orderbook inputs are not provided.
# You can pass auxiliary series later to replace proxies.

def add_class_features(feats: pd.DataFrame, aux: Dict[str, Any] | None = None) -> pd.DataFrame:
    out = feats.copy()
    if aux and 'funding' in aux:
        out['funding'] = pd.Series(aux['funding'], index=out.index).fillna(0)
    else:
        # proxy: funding ~ normalized momentum sign
        out['funding'] = np.sign(out['ema_fast'] - out['ema_slow']).fillna(0)
    if aux and 'oi' in aux:
        out['oi'] = pd.Series(aux['oi'], index=out.index).fillna(method='ffill').fillna(0)
    else:
        # proxy: oi ~ cumulative abs returns
        out['oi'] = out['ret'].abs().rolling(100).sum().fillna(0)
    if aux and 'basis' in aux:
        out['basis'] = pd.Series(aux['basis'], index=out.index).fillna(0)
    else:
        # proxy: basis ~ price deviation from ema_slow
        out['basis'] = (out['close'] - out['ema_slow']) / (out['ema_slow'] + 1e-9)
    return out


def label_clazz(feats: pd.DataFrame) -> pd.Series:
    fz = (feats['funding'] - feats['funding'].rolling(500).mean()).fillna(0) / (feats['funding'].rolling(500).std() + 1e-9)
    oiz = (feats['oi'] - feats['oi'].rolling(500).mean()).fillna(0) / (feats['oi'].rolling(500).std() + 1e-9)
    basis_pct = feats['basis'].rank(pct=True)
    squeeze = (oiz > 0.8).astype(int) * (basis_pct.between(0.4, 0.6)).astype(int)
    lab = pd.Series(index=feats.index, dtype=object)
    lab[squeeze == 1] = 'squeeze_setup'
    lab[(fz > 1.25) & (oiz > 1.0) & (basis_pct > 0.7)] = 'crowded_long'
    lab[(fz < -1.25) & (oiz > 1.0) & (basis_pct < 0.3)] = 'crowded_short'
    lab = lab.fillna('balanced')
    return lab


def add_order_features(feats: pd.DataFrame) -> pd.DataFrame:
    out = feats.copy()
    # liquidity topology proxies: profile via rolling var of returns and distance from ema anchors
    out['profile_var'] = feats['ret'].rolling(200).var().fillna(method='bfill').fillna(0)
    out['dist_avwap'] = (feats['close'] - feats['ema_slow']) / (feats['rv'] + 1e-9)
    return out


def label_order(feats: pd.DataFrame) -> pd.Series:
    # Identify potential wells/barriers via low/high profile_var
    pv = feats['profile_var']
    p = pv.rank(pct=True)
    lab = pd.Series(index=feats.index, dtype=object)
    lab[p < 0.2] = 'well'
    lab[p > 0.8] = 'barrier'
    lab = lab.fillna('neutral')
    return lab


def add_family_features(feats: pd.DataFrame) -> pd.DataFrame:
    out = feats.copy()
    # microstructure proxies
    out['impulse'] = feats['ret'].rolling(5).sum().abs() / (feats['rv'] + 1e-9)
    out['exhaustion'] = (feats['ret'].rolling(20).sum().abs() / (feats['rv'] + 1e-9)) * (feats['ret'].rolling(20).std())
    out['progress_sigma'] = (feats['close'].diff().abs()) / (feats['rv'] + 1e-9)
    out['vol_mult'] = feats['ret'].abs() / (feats['ret'].abs().rolling(50).mean() + 1e-9)
    return out


def label_family(feats: pd.DataFrame) -> pd.Series:
    lab = pd.Series(index=feats.index, dtype=object)
    if 'impulse' in feats:
        lab[feats['impulse'] > feats['impulse'].quantile(0.8)] = 'impulse'
    if 'exhaustion' in feats:
        lab[feats['exhaustion'] > feats['exhaustion'].quantile(0.85)] = 'exhaustion'
    # absorption: high vol_mult but low progress
    if 'vol_mult' in feats and 'progress_sigma' in feats:
        mask = (feats['vol_mult'] > feats['vol_mult'].quantile(0.8)) & (feats['progress_sigma'] < feats['progress_sigma'].quantile(0.4))
        lab[mask] = 'absorption'
    lab = lab.fillna('neutral')
    return lab
