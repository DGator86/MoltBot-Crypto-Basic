from __future__ import annotations
import json
from typing import List
import websockets
from ..store.parquet_writer import write_events

STREAM = "wss://advanced-trade-ws.coinbase.com"

async def collect_trades(products: List[str]):
    # products like ["BTC-USDC","ETH-USDC"]
    sub = {
        "type": "subscribe",
        "product_ids": products,
        "channel": "market_trades"
    }
    async with websockets.connect(STREAM) as ws:
        await ws.send(json.dumps(sub))
        batch = []
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if isinstance(data, dict) and data.get('type') == 'message':
                events = data.get('events') or []
                for ev in events:
                    if ev.get('type') == 'market_trades':
                        for t in ev.get('trades', []):
                            batch.append({
                                'venue': 'coinbase',
                                'symbol': ev.get('product_id') or t.get('product_id'),
                                'ts': 0,  # TODO: parse timestamp if provided in ms
                                'price': float(t.get('price', 0.0)),
                                'size': float(t.get('size', 0.0)),
                            })
            if len(batch) >= 100:
                write_events('coinbase_trades', batch)
                batch.clear()
