from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, Any, List

import websockets

from particle_bot.types import Symbol, Venue, EventType, TradePrint, BookDelta, BookLevel, TradeSide, BaseEvent

# OKX WS public endpoint and subscription format:
# - Public WebSocket: wss://ws.okx.com:8443/ws/v5/public
# - Docs: https://www.okx.com/docs-v5/en/#websocket-api-public-channel
# - Subscribe: {"op":"subscribe","args":[{"channel":"trades","instId":"BTC-USDT"}]}

OKX_PUBLIC_URL = "wss://ws.okx.com:8443/ws/v5/public"

INST_MAP = {
    Symbol.BTC: "BTC-USDT",
    Symbol.ETH: "ETH-USDT",
    Symbol.SOL: "SOL-USDT",
}

def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)

def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)

def _parse_trade(msg: Dict[str, Any]) -> List[TradePrint]:
    # OKX trades message includes data array: each item has px, sz, side, ts
    # side is "buy" or "sell" (taker side)
    out: List[TradePrint] = []
    arg = msg.get("arg", {})
    inst = arg.get("instId", "")
    symbol = Symbol.BTC if inst.startswith("BTC") else Symbol.ETH if inst.startswith("ETH") else Symbol.SOL
    for t in msg.get("data", []) or []:
        side_raw = str(t.get("side", "")).lower()
        side = TradeSide.BUY if side_raw == "buy" else TradeSide.SELL if side_raw == "sell" else TradeSide.UNKNOWN
        out.append(TradePrint(
            ts=_ms_to_dt(int(t["ts"])),
            recv_ts=_now_utc(),
            symbol=symbol,
            venue=Venue.OKX,
            etype=EventType.TRADE_PRINT,
            price=float(t["px"]),
            size=float(t["sz"]),
            side=side,
            meta={"trade_id": t.get("tradeId")},
        ))
    return out

def _parse_books(msg: Dict[str, Any], depth_n: int) -> BookDelta | None:
    arg = msg.get("arg", {})
    inst = arg.get("instId", "")
    symbol = Symbol.BTC if inst.startswith("BTC") else Symbol.ETH if inst.startswith("ETH") else Symbol.SOL
    data_list = msg.get("data", []) or []
    if not data_list:
        return None
    d0 = data_list[0]
    bids_raw = d0.get("bids", []) or []
    asks_raw = d0.get("asks", []) or []

    bids = [BookLevel(price=float(px), size=float(sz)) for px, sz, *_ in bids_raw[:depth_n]]
    asks = [BookLevel(price=float(px), size=float(sz)) for px, sz, *_ in asks_raw[:depth_n]]

    bids.sort(key=lambda x: x.price, reverse=True)
    asks.sort(key=lambda x: x.price)

    ts_ms = int(d0.get("ts", int(_now_utc().timestamp()*1000)))
    return BookDelta(
        ts=_ms_to_dt(ts_ms),
        recv_ts=_now_utc(),
        symbol=symbol,
        venue=Venue.OKX,
        etype=EventType.BOOK_DELTA,
        bids=bids,
        asks=asks,
        depth_n=depth_n,
        meta={"checksum": d0.get("checksum")},
    )

@dataclass
class OKXPublicStream:
    symbols: List[Symbol]
    depth_n: int = 20
    reconnect_backoff_s: float = 1.0
    max_backoff_s: float = 30.0

    async def _subscribe(self, ws) -> None:
        args = []
        for sym in self.symbols:
            inst = INST_MAP[sym]
            args.append({"channel": "trades", "instId": inst})
            args.append({"channel": "books", "instId": inst})
        req = {"id": "particle-bot", "op": "subscribe", "args": args}
        await ws.send(json.dumps(req))

    async def events(self) -> AsyncIterator[BaseEvent]:
        backoff = self.reconnect_backoff_s
        while True:
            try:
                async with websockets.connect(OKX_PUBLIC_URL, ping_interval=20, ping_timeout=20, max_queue=1024) as ws:
                    await self._subscribe(ws)
                    backoff = self.reconnect_backoff_s
                    async for msg in ws:
                        raw = json.loads(msg)
                        if "event" in raw:
                            # subscribe ack, error, etc.
                            continue
                        arg = raw.get("arg", {})
                        ch = arg.get("channel")
                        if ch == "trades":
                            for ev in _parse_trade(raw):
                                yield ev
                        elif ch == "books":
                            bd = _parse_books(raw, self.depth_n)
                            if bd:
                                yield bd
                        else:
                            continue
            except asyncio.CancelledError:
                return
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(self.max_backoff_s, backoff * 2)
