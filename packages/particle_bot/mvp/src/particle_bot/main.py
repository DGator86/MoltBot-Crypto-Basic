from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List
import yaml
import numpy as np

from particle_bot.types import Symbol, EventType, BaseEvent, TradePrint
from particle_bot.scales import Scale, DEFAULT_SCALES
from particle_bot.event_bus import EventBus
from particle_bot.mock_feed import synthetic_event_stream
from particle_bot.features.mvp import MVPFeatureEngine
from particle_bot.regimes.stacker import build_regime_stack
from particle_bot.fields.liquidity import build_price_grid, liquidity_potential
from particle_bot.fields.positioning import positioning_potential
from particle_bot.fields.total import total_potential
from particle_bot.forecast.trajectory import simulate_paths, cone_summary


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["replay"], default="replay")
    ap.add_argument("--symbol", choices=["BTC","ETH","SOL"], default="BTC")
    ap.add_argument("--steps", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--config", type=str, default=None)
    ap.add_argument("--out", type=str, default="data/derived/out.json")
    args = ap.parse_args()

    cfg = load_config(args.config) if args.config else load_config("config/default.yaml") if Path("config/default.yaml").exists() else {}
    scales = parse_scales(cfg)
    snapshot_every = int(cfg.get("snapshot_every_trades", 200))
    cone_cfg = cfg.get("cone", {"steps": 250, "n_paths": 2000})
    cone_steps = int(cone_cfg.get("steps", 250))
    n_paths = int(cone_cfg.get("n_paths", 2000))

    symbol = Symbol(args.symbol)

    feat = MVPFeatureEngine(scales=scales)
    bus = EventBus()

    # Subscribe feature engine to all relevant events
    for et in [EventType.TRADE_PRINT, EventType.BOOK_DELTA, EventType.FUNDING_TICK, EventType.OI_TICK, EventType.BASIS_TICK]:
        bus.subscribe(et, feat.update)

    outputs: List[Dict[str, Any]] = []

    trade_counter = {"n": 0}
    last_trade: TradePrint | None = None

    def on_trade(ev: BaseEvent) -> None:
        nonlocal last_trade
        t = ev  # type: ignore[assignment]
        last_trade = t  # type: ignore[assignment]
        trade_counter["n"] += 1

        if trade_counter["n"] % snapshot_every != 0:
            return

        # build outputs for each scale
        scale_snaps = []
        for sc in scales:
            f = feat.snapshot(symbol, sc)
            reg = build_regime_stack(f)

            # fields + cone only if we have price
            p0 = f.get("last_price")
            sigma_local = f.get("ret_sd", 0.0)
            book = feat.last_book.get(symbol)

            if p0 is not None and sigma_local is not None:
                grid = build_price_grid(float(p0), float(sigma_local))
                U_liq = liquidity_potential(grid, book, float(p0))
                U_pos = positioning_potential(grid, f, float(p0), float(sigma_local))
                U = total_potential({"liq": U_liq, "pos": U_pos}, weights={"liq": 1.0, "pos": 1.0})

                # Flow force proxy: use cvd_slope scaled down
                F_flow = float(np.tanh(f.get("cvd_slope", 0.0) / 50.0))

                # regime-conditioned coefficients (simple)
                alpha = 0.90 if reg.kingdom in ("trend","breakout") else 0.80
                beta = 0.15 if reg.clazz in ("crowded_long","crowded_short","squeeze_setup") else 0.10
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
                    seed=args.seed,
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

        outputs.append({
            "ts": ev.ts.isoformat(),
            "symbol": symbol.value,
            "snapshots": scale_snaps,
        })

    bus.subscribe(EventType.TRADE_PRINT, on_trade)

    # run replay using synthetic feed
    stream = synthetic_event_stream(symbol=symbol, steps=args.steps, seed=args.seed)
    for ev in stream:
        bus.publish(ev)  # type: ignore[arg-type]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(outputs, indent=2), encoding="utf-8")

    print(f"Wrote {len(outputs)} snapshots to {out_path}")

if __name__ == "__main__":
    main()
