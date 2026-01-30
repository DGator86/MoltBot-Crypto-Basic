from __future__ import annotations
import ccxt
from typing import Dict, Any

class CCXTExecution:
    def __init__(self, venue: str, api_key: str|None = None, secret: str|None = None):
        cls = getattr(ccxt, venue)
        self.client = cls({"apiKey": api_key, "secret": secret})

    def create_order(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.create_order(req["symbol"], req["type"], req["side"], req["size"], req.get("price"))
