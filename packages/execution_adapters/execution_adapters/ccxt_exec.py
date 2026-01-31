from __future__ import annotations
import ccxt
from typing import Dict, Any

class CCXTExecution:
    def __init__(self, venue: str, api_key: str|None = None, secret: str|None = None):
        cls = getattr(ccxt, venue)
        self.client = cls({"apiKey": api_key, "secret": secret})

    def create_order(self, req: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.create_order(req["symbol"], req["type"], req["side"], req["size"], req.get("price"))


    def fetch_balance(self):
        return self.client.fetch_balance()

    def fetch_positions(self):
        try:
            return self.client.fetch_positions()
        except Exception:
            return []

    def fetch_ticker(self, symbol: str):
        return self.client.fetch_ticker(symbol)

    def close_all_positions(self):
        results = []
        try:
            poss = self.client.fetch_positions()
        except Exception:
            poss = []
        for pos in (poss or []):
            try:
                amt = pos.get('contracts') or pos.get('amount') or 0
                try:
                    amt = abs(float(amt))
                except Exception:
                    amt = 0.0
                if not amt:
                    continue
                side = (pos.get('side') or '').lower()
                symbol = pos.get('symbol') or (pos.get('info', {}) if isinstance(pos.get('info'), dict) else {}).get('symbol')
                if not symbol:
                    continue
                close_side = 'sell' if side == 'long' else 'buy'
                params = {'reduceOnly': True}
                try:
                    ack = self.client.create_order(symbol, 'market', close_side, amt, None, params)
                except TypeError:
                    # some exchanges require omitting price/params signature differences
                    ack = self.client.create_order(symbol, 'market', close_side, amt)
                results.append({'symbol': symbol, 'closed': amt, 'ack': ack})
            except Exception as e:
                results.append({'error': str(e), 'pos': pos})
        return results
