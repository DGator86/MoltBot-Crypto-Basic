from __future__ import annotations
import os
from typing import Dict, Any
from execution_adapters.ccxt_exec import CCXTExecution

class ExecutionRouter:
    def __init__(self):
        api_key = os.getenv("BINANCE_API_KEY")
        secret = os.getenv("BINANCE_API_SECRET")
        # ccxt id for binance is 'binance'
        self._binance = CCXTExecution("binance", api_key=api_key, secret=secret)

    def place_order(self, req: Dict[str, Any]) -> Dict[str, Any]:
        venue = req.get("venue", "").lower()
        if venue != "binance":
            raise ValueError("Execution is enabled only for Binance. Coinbase is data-only.")
        return self._binance.create_order(req)
