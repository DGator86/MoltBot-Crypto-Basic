from __future__ import annotations
import os
import requests
from typing import Any, Dict

BASE = "https://cryptopanic.com/api/v1/posts/"

def latest(kind: str = "news", public: bool = True) -> Dict[str, Any]:
    params = {"kind": kind}
    key = os.getenv("CRYPTOPANIC_API_KEY")
    if key and not public:
        params["auth_token"] = key
    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    return r.json()
