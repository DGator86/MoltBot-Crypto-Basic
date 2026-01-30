from __future__ import annotations
from typing import Any, Dict

# Placeholder normalizers (fill with real mappings later)

def normalize_binance_trade(msg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "venue": "binance",
        "symbol": msg.get("s"),
        "ts": int(msg.get("T", 0)),
        "price": float(msg.get("p", 0.0)),
        "size": float(msg.get("q", 0.0)),
        "side": "buy" if msg.get("m") is False else "sell",
    }
