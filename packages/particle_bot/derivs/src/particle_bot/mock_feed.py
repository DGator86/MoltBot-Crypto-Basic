from __future__ import annotations
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional

from particle_bot.types import (
    Symbol, Venue, TradePrint, BookDelta, BookLevel, FundingTick, OITick, BasisTick,
    EventType, TradeSide
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def synthetic_event_stream(
    symbol: Symbol = Symbol.BTC,
    steps: int = 5000,
    seed: int = 7,
    start_price: float = 100_000.0,
) -> Iterator[object]:
    """Generate a deterministic synthetic stream with:
    - prints (dominant)
    - occasional L1 book snapshots
    - occasional funding/OI/basis
    This is for MVP validation + replay determinism.
    """
    rng = random.Random(seed)
    ts = _now()
    p = start_price
    v = 0.0

    # latent regime switches create trend/range/vol clusters
    regimes = ["range", "trend_up", "trend_down", "chop_highvol"]
    regime = "range"
    regime_ttl = 500

    funding = 0.0001
    oi = 1_000_000.0
    basis = 5.0

    for i in range(steps):
        if regime_ttl <= 0:
            regime = rng.choices(regimes, weights=[0.45, 0.2, 0.2, 0.15])[0]
            regime_ttl = rng.randint(300, 1200)

        regime_ttl -= 1

        # noise level changes by regime
        if regime == "range":
            drift = 0.0
            sigma = 8.0
        elif regime == "trend_up":
            drift = 0.9
            sigma = 10.0
        elif regime == "trend_down":
            drift = -0.9
            sigma = 10.0
        else:  # chop_highvol
            drift = 0.0
            sigma = 18.0

        # simple particle motion
        eps = rng.gauss(0.0, sigma)
        v = 0.90 * v + drift + eps
        p = max(1.0, p + v)

        # size correlates with volatility
        size = max(0.001, abs(rng.gauss(0.25, 0.18)) * (1.0 + sigma/20.0))

        # aggressor side correlates with velocity sign (weakly)
        if v > 2.0:
            side = TradeSide.BUY
        elif v < -2.0:
            side = TradeSide.SELL
        else:
            side = rng.choice([TradeSide.BUY, TradeSide.SELL, TradeSide.UNKNOWN])

        ts = ts + timedelta(milliseconds=200)
        recv_ts = ts + timedelta(milliseconds=rng.randint(1, 15))

        yield TradePrint(
            ts=ts,
            recv_ts=recv_ts,
            symbol=symbol,
            venue=Venue.MOCK,
            etype=EventType.TRADE_PRINT,
            price=float(p),
            size=float(size),
            side=side,
            meta={"regime_hint": regime},
        )

        # every ~20 prints, emit a simple L1 book snapshot
        if i % 20 == 0:
            spread = max(0.5, 0.02 * sigma)
            bids = []
            asks = []
            for lvl in range(20):
                dp = (lvl + 1) * spread
                bids.append(BookLevel(price=float(p - dp), size=float(max(0.1, rng.random()*5))))
                asks.append(BookLevel(price=float(p + dp), size=float(max(0.1, rng.random()*5))))
            yield BookDelta(
                ts=ts,
                recv_ts=recv_ts,
                symbol=symbol,
                venue=Venue.MOCK,
                etype=EventType.BOOK_DELTA,
                bids=bids,
                asks=asks,
                depth_n=20,
                meta={},
            )

        # every ~100 prints, emit funding/OI/basis dynamics
        if i % 100 == 0:
            # funding drifts positive in trend_up, negative in trend_down
            funding += (0.00002 if regime == "trend_up" else -0.00002 if regime == "trend_down" else 0.0) + rng.gauss(0.0, 0.00003)
            funding = max(-0.003, min(0.003, funding))

            # oi increases in trends, collapses sometimes in chop
            oi += (5000 if regime in ("trend_up", "trend_down") else 1000) + rng.gauss(0, 3000)
            if regime == "chop_highvol" and rng.random() < 0.03:
                oi *= 0.95  # deleveraging pulse

            basis += (0.15 if funding > 0 else -0.15) + rng.gauss(0, 0.25)

            yield FundingTick(
                ts=ts,
                recv_ts=recv_ts,
                symbol=symbol,
                venue=Venue.MOCK,
                etype=EventType.FUNDING_TICK,
                funding_rate=float(funding),
                next_funding_ts=None,
                meta={},
            )
            yield OITick(
                ts=ts,
                recv_ts=recv_ts,
                symbol=symbol,
                venue=Venue.MOCK,
                etype=EventType.OI_TICK,
                open_interest=float(oi),
                meta={"units": "contracts"},
            )
            yield BasisTick(
                ts=ts,
                recv_ts=recv_ts,
                symbol=symbol,
                venue=Venue.MOCK,
                etype=EventType.BASIS_TICK,
                basis=float(basis),
                basis_type="perp_minus_spot",
                meta={},
            )
