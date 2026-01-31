from __future__ import annotations
import json
from typing import Iterable, Dict, Any, Tuple

# Reads particle bot JSONL events and extracts a simple OHLCV-like series
# focusing on trade prints as the primary truth.

TRADE_KEYS = {"TRADE_PRINT", "trade_print"}


def iter_events_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def extract_trades(path: str) -> Tuple[list[int], list[float]]:
    """
    Return (timestamps_ms, prices) lists using trade events only.
    Attempts to accommodate both MVP and derivs formats.
    """
    ts_list: list[int] = []
    px_list: list[float] = []
    for ev in iter_events_jsonl(path):
        etype = (ev.get('etype') or ev.get('event_type') or '').lower()
        if etype in {e.lower() for e in TRADE_KEYS}:
            # timestamp field tolerance
            ts = ev.get('ts') or ev.get('timestamp') or ev.get('t')
            if isinstance(ts, (int, float)):
                ts_ms = int(ts)
            else:
                # if ISO string or absent, skip
                continue
            price = ev.get('price')
            if price is None:
                continue
            try:
                px = float(price)
            except Exception:
                continue
            ts_list.append(ts_ms)
            px_list.append(px)
    return ts_list, px_list


def trades_to_close_series(timestamps_ms: list[int], prices: list[float]) -> list[dict]:
    """
    Convert tick prices into a minimal OHLCV-like series with only 'close'.
    We downsample by taking every Nth trade to keep payload small.
    """
    if not prices:
        return []
    N = max(1, len(prices) // 2000)  # limit to ~2000 points
    out: list[dict] = []
    for i in range(0, len(prices), N):
        ts = timestamps_ms[i]
        out.append({"ts": ts, "close": float(prices[i])})
    return out
