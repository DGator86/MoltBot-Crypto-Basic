from __future__ import annotations
import requests
from typing import Any, Dict

BASE = "https://api.llama.fi"

def perp_volume_all() -> Dict[str, Any]:
    r = requests.get(f"{BASE}/perp/overview", timeout=30)
    r.raise_for_status()
    return r.json()
