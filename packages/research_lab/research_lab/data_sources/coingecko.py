from __future__ import annotations
import requests
from typing import Any, Dict

BASE = "https://api.coingecko.com/api/v3"

def market_chart(symbol_id: str, vs_currency: str = "usd", days: str = "30") -> Dict[str, Any]:
    url = f"{BASE}/coins/{symbol_id}/market_chart"
    r = requests.get(url, params={"vs_currency": vs_currency, "days": days}, timeout=30)
    r.raise_for_status()
    return r.json()
