from __future__ import annotations
import asyncio
import json
import websockets
from typing import List
from ..store.parquet_writer import write_events

STREAM = "wss://stream.binance.com:9443/ws"

async def collect_trades(symbols: List[str]):
    subs = [{"method":"SUBSCRIBE","params":[f"{sym}@trade" for sym in symbols],"id":1}]
    async with websockets.connect(STREAM) as ws:
        await ws.send(json.dumps(subs[0]))
        batch = []
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if 'e' in data and data.get('e') == 'trade':
                batch.append({
                    'venue': 'binance',
                    'symbol': data.get('s'),
                    'ts': int(data.get('T',0)),
                    'price': float(data.get('p',0.0)),
                    'size': float(data.get('q',0.0)),
                })
            if len(batch) >= 100:
                write_events('binance_trades', batch)
                batch.clear()
