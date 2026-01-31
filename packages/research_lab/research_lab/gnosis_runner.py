from __future__ import annotations
import sys
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime, timezone

import pandas as pd

# Make the Yoshi-Bot (gnosis) src importable
_YOSHI_SRC = Path(__file__).resolve().parents[3] / "bots" / "Yoshi-Bot" / "src"
if _YOSHI_SRC.exists():
    sys.path.insert(0, str(_YOSHI_SRC))

# Optional imports guarded — raise friendly error if not present
try:
    from gnosis.harness.trade_walkforward import TradeWalkForwardHarness
    from gnosis.loop.ralph import RalphLoop
except Exception as e:  # pragma: no cover
    TradeWalkForwardHarness = None  # type: ignore
    RalphLoop = None  # type: ignore

# Reuse our particle adapter to turn JSONL events into a price series
from .ingest.particle_adapter import extract_trades


def _particle_jsonl_to_prints_df(path: str, symbol: str = "BTCUSDT") -> pd.DataFrame:
    ts, px = extract_trades(path)
    if not ts:
        raise ValueError("No trades found in particle JSONL")
    # Build a minimal prints DataFrame expected by gnosis.ingest.loader
    # Columns: timestamp (datetime), symbol, price, quantity, side, trade_id
    df = pd.DataFrame({
        "timestamp": pd.to_datetime(pd.Series(ts), unit="ms", utc=True),
        "symbol": symbol,
        "price": pd.Series(px, dtype=float),
    })
    # Fill quantity/side/trade_id with dummies (acceptable for feature building)
    df["quantity"] = 0.001
    # crude side: price change sign
    side = ["BUY"]
    for i in range(1, len(px)):
        side.append("BUY" if px[i] >= px[i-1] else "SELL")
    df["side"] = side
    df["trade_id"] = [f"{symbol}_{i}" for i in range(len(df))]
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def _default_base_config() -> Dict[str, Any]:
    return {
        "domains": {"D0": {"n_trades": 200}},
        "particle": {"flow": {"span": 100}},
        "targets": {"horizon_bars": 10},
        "regimes": {"confidence_floor_scale": 1.0},
        "models": {"predictor": {"l2_reg": 0.0}},
    }


def _default_hparams() -> Dict[str, Any]:
    return {
        "inner_folds": {"n_folds": 3, "train_ratio": 0.6, "val_ratio": 0.4},
        "inner_purge_trades": 200,
        "inner_embargo_trades": 200,
        "target_coverage": 0.90,
        # Simple grid; expand as needed
        "grid": {
            "domains_D0_n_trades": [100, 200, 400],
            "particle_flow_span": [50, 100, 150],
            "predictor_l2_reg": [0.0, 1e-4, 1e-3],
            "confidence_floor_scale": [0.8, 1.0, 1.2],
        },
    }


def run_gnosis(source: Dict[str, Any], base_config: Dict[str, Any] | None = None, hparams: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
    """
    Run the Yoshi/Gnosis Ralph Loop on provided source and persist artifacts under data/artifacts/gnosis/<run_id>/.

    source examples:
      {"type": "particle_jsonl", "path": "data/raw/particle_mock.jsonl", "symbol": "BTCUSDT"}
    """
    if RalphLoop is None or TradeWalkForwardHarness is None:
        raise RuntimeError("Gnosis (Yoshi-Bot) modules not available. Ensure bots/Yoshi-Bot submodule exists and is on PYTHONPATH.")

    stype = (source.get("type") or "").lower()
    if stype == "particle_jsonl":
        prints_df = _particle_jsonl_to_prints_df(source["path"], symbol=source.get("symbol", "BTCUSDT"))
    else:
        raise ValueError(f"Unsupported source.type: {stype}")

    # Configs
    base_cfg = base_config or _default_base_config()
    hparams_cfg = hparams or _default_hparams()

    # Outer walk-forward harness in trades space
    n_trades = len(prints_df)
    # Reasonable defaults based on sample size
    window = min(max(5000, n_trades // 3), max(5000, n_trades - 1000))
    step = max(1000, window // 4)
    horizon = int(base_cfg.get("targets", {}).get("horizon_bars", 10)) * int(base_cfg.get("domains", {}).get("D0", {}).get("n_trades", 200))
    purge = max(200, int(hparams_cfg.get("inner_purge_trades", 200)))
    embargo = max(200, int(hparams_cfg.get("inner_embargo_trades", 200)))

    harness = TradeWalkForwardHarness(
        window_trades=window,
        step_trades=step,
        horizon_trades=horizon,
        purge_trades=purge,
        embargo_trades=embargo,
    )

    loop = RalphLoop(base_cfg, hparams_cfg)
    trials_df, selected_json = loop.run(prints_df, harness)

    # Persist artifacts
    run_id = uuid.uuid4().hex
    out_dir = Path("data/artifacts/gnosis") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    trials_path = out_dir / "trials.parquet"
    try:
        trials_df.to_parquet(trials_path, index=False)
    except Exception:
        trials_df.to_csv(out_dir / "trials.csv", index=False)

    report = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "n_trades": n_trades,
        "outer_window_trades": window,
        "outer_step_trades": step,
        "horizon_trades": horizon,
        "selected": selected_json,
        "artifacts": {
            "trials": str(trials_path if trials_path.exists() else (out_dir / "trials.csv")),
        },
    }

    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    # Minimal markdown summary
    (out_dir / "report.md").write_text(
        f"# Gnosis Run {run_id}\n\n"
        f"Trades: {n_trades}\n\n"
        f"Window (trades): {window}, Step: {step}, Horizon: {horizon}\n\n"
        f"Selected: {json.dumps(selected_json, indent=2)}\n"
    )

    return run_id, report
