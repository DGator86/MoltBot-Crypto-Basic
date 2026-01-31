from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, DefaultDict
from collections import defaultdict
import numpy as np

from particle_bot.types import BaseEvent, TradePrint, BookDelta, FundingTick, OITick, BasisTick, EventType, TradeSide, Symbol
from particle_bot.scales import Scale, DEFAULT_SCALES
from particle_bot.utils.ringbuffer import RingBuffer
from particle_bot.utils.stats import mean, stdev, zscore, clamp


@dataclass
class ScaleState:
    prices: RingBuffer[float]
    rets: RingBuffer[float]
    sizes: RingBuffer[float]
    signed_sizes: RingBuffer[float]
    # for simple linear slopes (use np.polyfit on snapshots)
    cvd: float = 0.0
    last_price: float | None = None


@dataclass
class DerivState:
    funding_hist: RingBuffer[float]
    oi_hist: RingBuffer[float]
    basis_hist: RingBuffer[float]
    funding: float = 0.0
    oi: float = 0.0
    basis: float = 0.0


class MVPFeatureEngine:
    """Incremental, prints-first features at multiple zoom scales."""
    def __init__(self, scales: list[Scale] | None = None) -> None:
        self.scales = scales or DEFAULT_SCALES
        self.scale_states: Dict[tuple[Symbol, str], ScaleState] = {}
        self.derivs: Dict[Symbol, DerivState] = {}
        self.last_book: Dict[Symbol, Dict[str, Any]] = {}
        self.trade_count: DefaultDict[Symbol, int] = defaultdict(int)

    def _get_scale_state(self, symbol: Symbol, scale: Scale) -> ScaleState:
        key = (symbol, scale.name)
        if key not in self.scale_states:
            n = scale.trade_count or 2000
            self.scale_states[key] = ScaleState(
                prices=RingBuffer(maxlen=n),
                rets=RingBuffer(maxlen=n),
                sizes=RingBuffer(maxlen=n),
                signed_sizes=RingBuffer(maxlen=n),
            )
        return self.scale_states[key]

    def _get_deriv_state(self, symbol: Symbol) -> DerivState:
        if symbol not in self.derivs:
            self.derivs[symbol] = DerivState(
                funding_hist=RingBuffer(maxlen=500),
                oi_hist=RingBuffer(maxlen=500),
                basis_hist=RingBuffer(maxlen=500),
            )
        return self.derivs[symbol]

    def update(self, ev: BaseEvent) -> None:
        if ev.etype == EventType.TRADE_PRINT:
            self._update_trade(ev)  # type: ignore[arg-type]
        elif ev.etype == EventType.BOOK_DELTA:
            self._update_book(ev)   # type: ignore[arg-type]
        elif ev.etype == EventType.FUNDING_TICK:
            self._update_funding(ev)  # type: ignore[arg-type]
        elif ev.etype == EventType.OI_TICK:
            self._update_oi(ev)        # type: ignore[arg-type]
        elif ev.etype == EventType.BASIS_TICK:
            self._update_basis(ev)     # type: ignore[arg-type]

    def _update_trade(self, t: TradePrint) -> None:
        self.trade_count[t.symbol] += 1
        sign = 0.0
        if t.side == TradeSide.BUY:
            sign = 1.0
        elif t.side == TradeSide.SELL:
            sign = -1.0

        for scale in self.scales:
            st = self._get_scale_state(t.symbol, scale)
            if st.last_price is None:
                st.last_price = t.price
            ret = (t.price - st.last_price)
            st.last_price = t.price

            st.prices.append(t.price)
            st.rets.append(ret)
            st.sizes.append(t.size)
            st.signed_sizes.append(sign * t.size)
            st.cvd += sign * t.size

    def _update_book(self, b: BookDelta) -> None:
        # store last snapshot; features derived in snapshot()
        self.last_book[b.symbol] = {
            "bids": [(lvl.price, lvl.size) for lvl in b.bids],
            "asks": [(lvl.price, lvl.size) for lvl in b.asks],
            "depth_n": b.depth_n,
        }

    def _update_funding(self, f: FundingTick) -> None:
        d = self._get_deriv_state(f.symbol)
        d.funding = f.funding_rate
        d.funding_hist.append(d.funding)

    def _update_oi(self, o: OITick) -> None:
        d = self._get_deriv_state(o.symbol)
        d.oi = o.open_interest
        d.oi_hist.append(d.oi)

    def _update_basis(self, b: BasisTick) -> None:
        d = self._get_deriv_state(b.symbol)
        d.basis = b.basis
        d.basis_hist.append(d.basis)

    def snapshot(self, symbol: Symbol, scale: Scale) -> Dict[str, Any]:
        st = self._get_scale_state(symbol, scale)
        d = self._get_deriv_state(symbol)

        prices = st.prices.values()
        rets = st.rets.values()
        sizes = st.sizes.values()
        ssz = st.signed_sizes.values()

        # realized volatility proxy in price units per print
        ret_sd = stdev(rets)
        ret_mu = mean(rets)

        # directional strength: |mean return| / (std return + eps) -> squash to 0..1
        dir_raw = abs(ret_mu) / (ret_sd + 1e-9)
        directional_strength = float(1.0 - np.exp(-dir_raw))  # saturating

        # mean-reversion proxy: negative autocorr of returns (quick approx)
        mr_score = 0.0
        if len(rets) > 20:
            r = np.array(rets[-200:], dtype=float)
            r1 = r[:-1]
            r2 = r[1:]
            if r1.std() > 1e-9 and r2.std() > 1e-9:
                corr = float(np.corrcoef(r1, r2)[0, 1])
                mr_score = clamp((-corr + 1.0) / 2.0, 0.0, 1.0)  # corr=-1 => 1.0

        # CVD slope (simple linear fit)
        cvd_slope = 0.0
        if len(ssz) > 50:
            y = np.cumsum(np.array(ssz[-300:], dtype=float))
            x = np.arange(len(y), dtype=float)
            # slope per step
            cvd_slope = float(np.polyfit(x, y, 1)[0])

        # progress in sigma units across the window
        progress_sigma = 0.0
        if len(prices) > 10:
            progress = prices[-1] - prices[0]
            progress_sigma = float(abs(progress) / (ret_sd * max(len(prices),1) ** 0.5 + 1e-9))

        # volume multiplier: last chunk vs average
        vol_mult = 1.0
        if len(sizes) > 100:
            chunk = sizes[-50:]
            vol_mult = float((mean(chunk) + 1e-9) / (mean(sizes) + 1e-9))

        # tail risk proxy: fraction of |ret| > 2*sd
        tail_risk = 0.0
        if len(rets) > 50 and ret_sd > 1e-9:
            arr = np.array(rets[-500:], dtype=float)
            tail_risk = float(np.mean(np.abs(arr) > 2.0 * ret_sd))

        # breakout probability proxy: compression + rising directional
        # compression is low ret_sd relative to its history (approx via percentile)
        vol_hist = []
        # compute simple rolling std samples from stored rets if enough
        if len(rets) > 600:
            rr = np.array(rets, dtype=float)
            for i in range(0, len(rr) - 200, 50):
                vol_hist.append(float(rr[i:i+200].std()))
        vol_percentile = 0.5
        if vol_hist:
            vol_hist_sorted = sorted(vol_hist)
            cur = ret_sd
            # percentile rank
            idx = np.searchsorted(vol_hist_sorted, cur, side="right")
            vol_percentile = float(idx / len(vol_hist_sorted))
        breakout_prob = float(clamp((1.0 - vol_percentile) * directional_strength, 0.0, 1.0))

        # derivatives z-scores
        funding_mu, funding_sd = mean(d.funding_hist.values()), stdev(d.funding_hist.values())
        funding_z = float(zscore(d.funding, funding_mu, funding_sd))

        oi_mu, oi_sd = mean(d.oi_hist.values()), stdev(d.oi_hist.values())
        oi_z = float(zscore(d.oi, oi_mu, oi_sd))

        basis_mu, basis_sd = mean(d.basis_hist.values()), stdev(d.basis_hist.values())
        basis_z = float(zscore(d.basis, basis_mu, basis_sd))

        # basis percentile (rough)
        basis_vals = d.basis_hist.values()
        basis_percentile = 0.5
        if basis_vals:
            s = sorted(basis_vals)
            idx = np.searchsorted(s, d.basis, side="right")
            basis_percentile = float(idx / len(s))

        # squeeze score (very rough): crowded + near thin book (computed in fields later)
        squeeze_score = float(clamp((abs(funding_z) + max(0.0, oi_z)) / 4.0, 0.0, 1.0))

        # deleveraging score: oi drop z + high tail risk
        deleveraging_score = float(clamp(max(0.0, -oi_z) * 0.5 + tail_risk, 0.0, 1.0))

        # impulse/exhaustion/stoprun proxies
        impulse_score = float(clamp(directional_strength * abs(cvd_slope) / (mean(sizes)+1e-9) / 10.0, 0.0, 1.0))
        exhaustion_score = float(clamp((1.0 - directional_strength) * tail_risk, 0.0, 1.0))
        stoprun_score = float(clamp(tail_risk * vol_mult, 0.0, 1.0))

        # book imbalance (if available)
        book = self.last_book.get(symbol)
        book_imbalance = 0.0
        mid = prices[-1] if prices else 0.0
        if book:
            bid_depth = sum(sz for _, sz in book["bids"][:10])
            ask_depth = sum(sz for _, sz in book["asks"][:10])
            book_imbalance = float((bid_depth - ask_depth) / (bid_depth + ask_depth + 1e-9))

        return {
            "scale": scale.name,
            "n_trades": len(prices),
            "last_price": prices[-1] if prices else None,
            "ret_sd": ret_sd,
            "directional_strength": directional_strength,
            "mean_reversion_score": mr_score,
            "tail_risk": tail_risk,
            "vol_percentile": vol_percentile,
            "breakout_prob": breakout_prob,
            "cvd_slope": cvd_slope,
            "progress_sigma": progress_sigma,
            "vol_mult": vol_mult,
            "funding": d.funding,
            "funding_z": funding_z,
            "oi": d.oi,
            "oi_z": oi_z,
            "basis": d.basis,
            "basis_z": basis_z,
            "basis_percentile": basis_percentile,
            "squeeze_score": squeeze_score,
            "deleveraging_score": deleveraging_score,
            "impulse_score": impulse_score,
            "exhaustion_score": exhaustion_score,
            "stoprun_score": stoprun_score,
            "book_imbalance": book_imbalance,
        }
