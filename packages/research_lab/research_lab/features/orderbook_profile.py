from __future__ import annotations
from typing import List, Dict, Any, Tuple
import numpy as np


def volume_profile_from_trades(ohlcv_or_ticks: List[Dict[str, Any]], price_key: str = 'close', size_key: str | None = None, bins: int = 100) -> Dict[str, Any]:
    prices = []
    sizes = []
    for x in ohlcv_or_ticks:
        p = x.get(price_key)
        if p is None:
            continue
        prices.append(float(p))
        if size_key and x.get(size_key) is not None:
            sizes.append(float(x.get(size_key)))
        else:
            sizes.append(1.0)  # count proxy if no size
    if not prices:
        return {"bins": [], "hist": []}
    pmin, pmax = min(prices), max(prices)
    if pmin == pmax:
        pmax = pmin + 1e-6
    hist, edges = np.histogram(prices, bins=bins, range=(pmin, pmax), weights=np.array(sizes))
    centers = ((edges[:-1] + edges[1:]) / 2.0).tolist()
    return {"bins": centers, "hist": hist.tolist()}


def hvn_lvn(profile: Dict[str, Any], top_k: int = 3) -> Dict[str, Any]:
    bins = profile.get('bins', [])
    hist = profile.get('hist', [])
    if not bins or not hist:
        return {"hvn": [], "lvn": []}
    arr = np.array(hist)
    idx_sorted = np.argsort(arr)
    lvn_idx = idx_sorted[:top_k]
    hvn_idx = idx_sorted[-top_k:][::-1]
    return {
        "hvn": [bins[int(i)] for i in hvn_idx],
        "lvn": [bins[int(i)] for i in lvn_idx]
    }
