from __future__ import annotations

"""Binance USDⓈ-M Futures normalized market stream.

This feed is *prints-first* (aggTrade) and timeframe-agnostic.

It merges:
  - WebSocket market streams:
      <symbol>@aggTrade
      <symbol>@depth{N}@{speed}
      <symbol>@markPrice@1s  (funding + mark + index)
  - REST polling:
      /fapi/v1/openInterest
      /futures/data/basis

Why REST? Binance doesn't provide a standard USDM *websocket* open interest stream.

Docs (Binance Open Platform):
  - WS Mark Price stream (funding):
      https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams/Mark-Price-Stream
  - REST Open Interest:
      https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest
  - REST Basis:
      https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Basis
"""

import asyncio
import contextlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List

import aiohttp
import websockets

from particle_bot.types import (
    BaseEvent,
    BasisTick,
    BookDelta,
    BookLevel,
    EventType,
    FundingTick,
    OITick,
    Symbol,
    TradePrint,
    TradeSide,
    Venue,
)


BINANCE_FSTREAM_BASE = "wss://fstream.binance.com/stream?streams="
BINANCE_FAPI_REST_BASE = "https://fapi.binance.com"

SYMBOL_MAP = {
    Symbol.BTC: "btcusdt",
    Symbol.ETH: "ethusdt",
    Symbol.SOL: "solusdt",
}


def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _infer_symbol(sym_raw: str) -> Symbol:
    s = sym_raw.upper()
    if s.startswith("BTC"):
        return Symbol.BTC
    if s.startswith("ETH"):
        return Symbol.ETH
    return Symbol.SOL


def _parse_trade(data: Dict[str, Any]) -> TradePrint:
    # aggTrade fields: p (price), q (qty), T (trade time), m (buyer is maker)
    symbol = _infer_symbol(str(data.get("s", "")))

    # If buyer is maker => aggressor sell; else aggressor buy
    m = bool(data.get("m", False))
    side = TradeSide.SELL if m else TradeSide.BUY

    return TradePrint(
        ts=_ms_to_dt(int(data["T"])),
        recv_ts=_now_utc(),
        symbol=symbol,
        venue=Venue.BINANCE,
        etype=EventType.TRADE_PRINT,
        price=float(data["p"]),
        size=float(data["q"]),
        side=side,
        meta={
            "stream_event_time_ms": int(data.get("E", data["T"])),
            "agg_id": data.get("a"),
        },
    )


def _parse_depth(data: Dict[str, Any], depth_n: int) -> BookDelta:
    symbol = _infer_symbol(str(data.get("s", "")))

    bids_raw = data.get("b", []) or []
    asks_raw = data.get("a", []) or []

    bids = [BookLevel(price=float(px), size=float(sz)) for px, sz in bids_raw[:depth_n]]
    asks = [BookLevel(price=float(px), size=float(sz)) for px, sz in asks_raw[:depth_n]]

    bids.sort(key=lambda x: x.price, reverse=True)
    asks.sort(key=lambda x: x.price)

    ts_ms = int(data.get("T", 0) or data.get("E", 0) or int(_now_utc().timestamp() * 1000))
    return BookDelta(
        ts=_ms_to_dt(ts_ms),
        recv_ts=_now_utc(),
        symbol=symbol,
        venue=Venue.BINANCE,
        etype=EventType.BOOK_DELTA,
        bids=bids,
        asks=asks,
        depth_n=depth_n,
        meta={
            "U": data.get("U"),
            "u": data.get("u"),
            "pu": data.get("pu"),
            "event_time_ms": data.get("E"),
        },
    )


def _parse_mark_price(data: Dict[str, Any]) -> List[BaseEvent]:
    """markPriceUpdate -> FundingTick + BasisTick (mark - index)."""
    symbol = _infer_symbol(str(data.get("s", "")))
    event_ms = int(data.get("E", 0) or int(_now_utc().timestamp() * 1000))
    ts = _ms_to_dt(event_ms)
    recv_ts = _now_utc()

    mark = float(data.get("p", 0.0))
    index = float(data.get("i", 0.0))
    funding_rate = float(data.get("r", 0.0))
    next_funding_ms = int(data.get("T", 0) or 0)
    next_funding_ts = _ms_to_dt(next_funding_ms) if next_funding_ms else None

    return [
        FundingTick(
            ts=ts,
            recv_ts=recv_ts,
            symbol=symbol,
            venue=Venue.BINANCE,
            etype=EventType.FUNDING_TICK,
            funding_rate=funding_rate,
            next_funding_ts=next_funding_ts,
            meta={"mark": mark, "index": index, "event_time_ms": event_ms},
        ),
        BasisTick(
            ts=ts,
            recv_ts=recv_ts,
            symbol=symbol,
            venue=Venue.BINANCE,
            etype=EventType.BASIS_TICK,
            basis=(mark - index),
            basis_type="mark_minus_index",
            meta={"mark": mark, "index": index, "event_time_ms": event_ms},
        ),
    ]


@dataclass
class BinanceFuturesStream:
    symbols: List[Symbol]
    depth_n: int = 20
    depth_ms: str = "100ms"  # '100ms' or '250ms'

    # Websocket markPrice update (includes funding rate)
    mark_price_1s: bool = True

    # REST polling (Binance has no standard WS open-interest stream)
    oi_poll_s: float = 5.0
    basis_poll_s: float = 60.0
    basis_period: str = "5m"  # basis endpoint period

    reconnect_backoff_s: float = 1.0
    max_backoff_s: float = 30.0

    def _build_url(self) -> str:
        streams: List[str] = []
        for sym in self.symbols:
            s = SYMBOL_MAP[sym]
            streams.append(f"{s}@aggTrade")
            streams.append(f"{s}@depth{self.depth_n}@{self.depth_ms}")
            streams.append(f"{s}@markPrice@1s" if self.mark_price_1s else f"{s}@markPrice")
        return BINANCE_FSTREAM_BASE + "/".join(streams)

    async def _ws_loop(self, q: "asyncio.Queue[BaseEvent]") -> None:
        url = self._build_url()
        backoff = self.reconnect_backoff_s
        while True:
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20, max_queue=2048) as ws:
                    backoff = self.reconnect_backoff_s
                    async for msg in ws:
                        raw = json.loads(msg)
                        data = raw.get("data", raw)
                        et = data.get("e")
                        if et == "aggTrade":
                            await q.put(_parse_trade(data))
                        elif et == "depthUpdate":
                            await q.put(_parse_depth(data, self.depth_n))
                        elif et == "markPriceUpdate":
                            for ev in _parse_mark_price(data):
                                await q.put(ev)
                        else:
                            continue
            except asyncio.CancelledError:
                return
            except Exception:
                await asyncio.sleep(backoff)
                backoff = min(self.max_backoff_s, backoff * 2)

    async def _rest_loop(self, q: "asyncio.Queue[BaseEvent]") -> None:
        """Poll OI + Basis and emit normalized ticks."""
        # small jitter so we don't spike immediately
        await asyncio.sleep(1.0)

        async with aiohttp.ClientSession() as session:
            last_oi_poll = 0.0
            last_basis_poll = 0.0

            while True:
                try:
                    now = asyncio.get_running_loop().time()

                    if self.oi_poll_s > 0 and (now - last_oi_poll) >= self.oi_poll_s:
                        last_oi_poll = now
                        for sym in self.symbols:
                            sym_u = SYMBOL_MAP[sym].upper()
                            url = f"{BINANCE_FAPI_REST_BASE}/fapi/v1/openInterest"
                            params = {"symbol": sym_u}
                            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as r:
                                js = await r.json()

                            oi = float(js.get("openInterest", 0.0))
                            ts_ms = int(js.get("time", int(_now_utc().timestamp() * 1000)))
                            await q.put(
                                OITick(
                                    ts=_ms_to_dt(ts_ms),
                                    recv_ts=_now_utc(),
                                    symbol=sym,
                                    venue=Venue.BINANCE,
                                    etype=EventType.OI_TICK,
                                    open_interest=oi,
                                    meta={"raw": js},
                                )
                            )

                    if self.basis_poll_s > 0 and (now - last_basis_poll) >= self.basis_poll_s:
                        last_basis_poll = now
                        for sym in self.symbols:
                            pair = SYMBOL_MAP[sym].upper()
                            url = f"{BINANCE_FAPI_REST_BASE}/futures/data/basis"
                            params = {
                                "pair": pair,
                                "contractType": "PERPETUAL",
                                "period": self.basis_period,
                                "limit": 1,
                            }
                            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as r:
                                js = await r.json()

                            if isinstance(js, list) and js:
                                row = js[0]
                                basis = float(row.get("basis", 0.0))
                                ts_ms = int(row.get("timestamp", int(_now_utc().timestamp() * 1000)))
                                await q.put(
                                    BasisTick(
                                        ts=_ms_to_dt(ts_ms),
                                        recv_ts=_now_utc(),
                                        symbol=sym,
                                        venue=Venue.BINANCE,
                                        etype=EventType.BASIS_TICK,
                                        basis=basis,
                                        basis_type=f"endpoint_PERPETUAL_{self.basis_period}",
                                        meta={"raw": row},
                                    )
                                )

                    await asyncio.sleep(0.25)
                except asyncio.CancelledError:
                    return
                except Exception:
                    # keep going; transient HTTP errors are common
                    await asyncio.sleep(1.0)

    async def events(self) -> AsyncIterator[BaseEvent]:
        """Merged event iterator (WS + REST)."""
        q: asyncio.Queue[BaseEvent] = asyncio.Queue(maxsize=5000)
        ws_task = asyncio.create_task(self._ws_loop(q))
        rest_task = asyncio.create_task(self._rest_loop(q))

        try:
            while True:
                yield await q.get()
        finally:
            ws_task.cancel()
            rest_task.cancel()
            with contextlib.suppress(Exception):
                await ws_task
            with contextlib.suppress(Exception):
                await rest_task
