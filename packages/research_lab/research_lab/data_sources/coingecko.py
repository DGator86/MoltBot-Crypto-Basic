from __future__ import annotations
import os
import requests
from typing import Any, Dict

# Use Pro API if key available, otherwise public API
API_KEY = os.getenv("COINGECKO_API_KEY", "")
BASE = "https://pro-api.coingecko.com/api/v3" if API_KEY else "https://api.coingecko.com/api/v3"

def market_chart(symbol_id: str, vs_currency: str = "usd", days: str = "30") -> Dict[str, Any]:
    url = f"{BASE}/coins/{symbol_id}/market_chart"
    headers = {"x-cg-pro-api-key": API_KEY} if API_KEY else {}
    params = {"vs_currency": vs_currency, "days": days}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()
