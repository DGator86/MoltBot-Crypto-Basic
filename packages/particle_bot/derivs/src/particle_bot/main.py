from __future__ import annotations
import argparse
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
import numpy as np

from particle_bot.types import Symbol, EventType, BaseEvent, Venue
from particle_bot.scales import Scale, DEFAULT_SCALES
from particle_bot.event_bus import EventBus
from particle_bot.mock_feed import synthetic_event_stream
from particle_bot.features.mvp import MVPFeatureEngine
from particle_bot.regimes.stacker import build_regime_stack
from particle_bot.fields.liquidity import build_price_grid, liquidity_potential
from particle_bot.fields.positioning import positioning_potential
from particle_bot.fields.total import total_potential
from particle_bot.forecast.trajectory import simulate_paths, cone_summary

from particle_bot.recording.jsonl import JSONLRecorder, iter_events
from particle_bot.feeds.binance_futures import BinanceFuturesStream
from particle_bot.feeds.okx_public import OKXPublicStream


def load_config(path: str | None) -> Dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_scales(cfg: Dict[str, Any]) -> List[Scale]:
    if "scales" not in cfg:
        return DEFAULT_SCALES
    scales = []
    for s in cfg["scales"]:
        scales.append(Scale(
            name=s["name"],
            trade_count=int(s.get("trade_count", 2000)),
            sigma_window_trades=int(s.get("sigma_window_trades", 5000)),
            sigma_k=float(s.get("sigma_k", 1.0)),
        ))
    return scales


def _open_jsonl(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    return open(path, "a", encoding="utf-8")


def build_pipeline(cfg: Dict[str, Any]):
    scales = parse_scales(cfg)
    snapshot_every = int(cfg.get("snapshot_every_trades", 200))
    cone_cfg = cfg.get("cone", {"steps": 250, "n_paths": 2000})
    cone_steps = int(cone_cfg.get("steps", 250))
    n_paths = int(cone_cfg.get("n_paths", 2000))
    book_depth = int(cfg.get("book_depth", 20))

    feat = MVPFeatureEngine(scales=scales)
    bus = EventBus()

    for et in [EventType.TRADE_PRINT, EventType.BOOK_DELTA, EventType.FUNDING_TICK, EventType.OI_TICK, EventType.BASIS_TICK]:
        bus.subscribe(et, feat.update)

    return scales, snapshot_every, cone_steps, n_paths, book_depth, feat, bus


def make_snapshot_callback(
    scales: List[Scale],
    feat: MVPFeatureEngine,
    snapshot_every: int,
    cone_steps: int,
    n_paths: int,
    seed: int,
):
    trade_counter = 0

    def on_event(ev: BaseEvent) -> Optional[Dict[str, Any]]:
        nonlocal trade_counter
        if ev.etype != EventType.TRADE_PRINT:
            return None

        trade_counter += 1
        if trade_counter % snapshot_every != 0:
            return None

        symbol = ev.symbol
        scale_snaps = []

        for sc in scales:
            f = feat.snapshot(symbol, sc)
            reg = build_regime_stack(f)

            p0 = f.get("last_price")
            sigma_local = f.get("ret_sd", 0.0)
            book = feat.last_book.get(symbol)

            if p0 is not None and sigma_local is not None:
                grid = build_price_grid(float(p0), float(sigma_local))
                U_liq = liquidity_potential(grid, book, float(p0))
                U_pos = positioning_potential(grid, f, float(p0), float(sigma_local))
                U = total_potential({"liq": U_liq, "pos": U_pos}, weights={"liq": 1.0, "pos": 1.0})

                F_flow = float(np.tanh(f.get("cvd_slope", 0.0) / 50.0))

                # regime-conditioned coefficients (simple baseline)
                alpha = 0.90 if reg.kingdom in ("trend", "breakout") else 0.80
                beta = 0.15 if reg.clazz in ("crowded_long", "crowded_short", "squeeze_setup") else 0.10
                gamma = 0.25

                paths = simulate_paths(
                    p0=float(p0),
                    v0=0.0,
                    grid=grid,
                    U=U,
                    F_flow=F_flow,
                    sigma_local=max(float(sigma_local), 1e-6),
                    alpha=float(alpha),
                    beta=float(beta),
                    gamma=float(gamma),
                    steps=cone_steps,
                    n_paths=n_paths,
                    seed=seed,
                )
                cone = cone_summary(paths)
            else:
                cone = None

            scale_snaps.append({
                "scale": sc.name,
                "features": f,
                "regimes": reg.model_dump(),
                "cone": cone,
            })

        return {
            "ts": ev.ts.isoformat(),
            "symbol": symbol.value,
            "snapshots": scale_snaps,
        }

    return on_event


async def run_live(
    venue: Venue,
    symbols: List[Symbol],
    cfg: Dict[str, Any],
    out_snapshots: Path,
    out_events: Optional[Path],
    seed: int,
    max_events: int,
) -> None:
    scales, snapshot_every, cone_steps, n_paths, book_depth, feat, bus = build_pipeline(cfg)
    snap_cb = make_snapshot_callback(scales, feat, snapshot_every, cone_steps, n_paths, seed)

    snap_fh = _open_jsonl(out_snapshots)
    recorder = JSONLRecorder(out_events) if out_events else None

    if venue == Venue.BINANCE:
        bcfg = cfg.get("binance", {}) if isinstance(cfg, dict) else {}
        stream = BinanceFuturesStream(
            symbols=symbols,
            depth_n=book_depth,
            depth_ms=str(bcfg.get("depth_ms", "100ms")),
            mark_price_1s=bool(bcfg.get("mark_price_1s", True)),
            oi_poll_s=float(bcfg.get("oi_poll_s", 5.0)),
            basis_poll_s=float(bcfg.get("basis_poll_s", 60.0)),
            basis_period=str(bcfg.get("basis_period", "5m")),
        )
        ev_iter = stream.events()
    elif venue == Venue.OKX:
        stream = OKXPublicStream(symbols=symbols, depth_n=book_depth)
        ev_iter = stream.events()
    else:
        raise ValueError(f"Unsupported live venue: {venue}")

    n = 0
    try:
        async for ev in ev_iter:
            n += 1
            if recorder:
                recorder.write_event(ev)
            bus.publish(ev)

            snap = snap_cb(ev)
            if snap:
                snap_fh.write(json.dumps(snap, separators=(",", ":")) + "\n")
                if (n % 200) == 0:
                    snap_fh.flush()

            if max_events > 0 and n >= max_events:
                break
    finally:
        snap_fh.flush()
        snap_fh.close()
        if recorder:
            recorder.close()


def run_replayfile(
    events_path: Path,
    cfg: Dict[str, Any],
    out_snapshots: Path,
    seed: int,
    max_events: int,
) -> None:
    scales, snapshot_every, cone_steps, n_paths, _book_depth, feat, bus = build_pipeline(cfg)
    snap_cb = make_snapshot_callback(scales, feat, snapshot_every, cone_steps, n_paths, seed)

    snap_fh = _open_jsonl(out_snapshots)

    n = 0
    for ev in iter_events(events_path):
        n += 1
        bus.publish(ev)

        snap = snap_cb(ev)
        if snap:
            snap_fh.write(json.dumps(snap, separators=(",", ":")) + "\n")
            if (n % 200) == 0:
                snap_fh.flush()

        if max_events > 0 and n >= max_events:
            break

    snap_fh.flush()
    snap_fh.close()


def run_synthetic(
    symbol: Symbol,
    steps: int,
    seed: int,
    cfg: Dict[str, Any],
    out_path: Path,
) -> None:
    scales, snapshot_every, cone_steps, n_paths, _book_depth, feat, bus = build_pipeline(cfg)
    snap_cb = make_snapshot_callback(scales, feat, snapshot_every, cone_steps, n_paths, seed)

    outputs: List[Dict[str, Any]] = []

    stream = synthetic_event_stream(symbol=symbol, steps=steps, seed=seed)
    for ev in stream:
        bus.publish(ev)  # type: ignore[arg-type]
        snap = snap_cb(ev)
        if snap:
            outputs.append(snap)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    print(f"Wrote {len(outputs)} snapshots to {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["synthetic", "record", "replayfile"], default="record")
    ap.add_argument("--venue", choices=["binance", "okx"], default="binance")
    ap.add_argument("--symbols", type=str, default="BTC,ETH,SOL", help="Comma-separated: BTC,ETH,SOL")
    ap.add_argument("--steps", type=int, default=5000, help="Synthetic only")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--config", type=str, default=None)

    ap.add_argument("--events", type=str, default="data/raw/events.jsonl", help="Record mode output (normalized events). Set '' to disable.")
    ap.add_argument("--in", dest="in_events", type=str, default="data/raw/events.jsonl", help="Replayfile input")

    ap.add_argument("--snapshots", type=str, default="data/derived/snapshots.jsonl", help="Snapshots output (JSONL)")

    ap.add_argument("--max-events", type=int, default=0, help="Stop after N events (0 = run forever)")
    args = ap.parse_args()

    cfg = load_config(args.config) if args.config else load_config("config/default.yaml") if Path("config/default.yaml").exists() else {}

    symbols = [Symbol(s.strip()) for s in args.symbols.split(",") if s.strip()]
    venue = Venue(args.venue)

    if args.mode == "synthetic":
        run_synthetic(symbol=symbols[0], steps=args.steps, seed=args.seed, cfg=cfg, out_path=Path("data/derived/out.json"))
        return

    out_snap = Path(args.snapshots)

    if args.mode == "record":
        out_events = Path(args.events) if args.events else None
        asyncio.run(run_live(
            venue=venue,
            symbols=symbols,
            cfg=cfg,
            out_snapshots=out_snap,
            out_events=out_events,
            seed=args.seed,
            max_events=int(args.max_events),
        ))
        print(f"Wrote snapshots (JSONL) to {out_snap}")
        if out_events:
            print(f"Wrote normalized events (JSONL) to {out_events}")
        return

    if args.mode == "replayfile":
        run_replayfile(
            events_path=Path(args.in_events),
            cfg=cfg,
            out_snapshots=out_snap,
            seed=args.seed,
            max_events=int(args.max_events),
        )
        print(f"Replayed events from {args.in_events} and wrote snapshots to {out_snap}")
        return


if __name__ == "__main__":
    main()
