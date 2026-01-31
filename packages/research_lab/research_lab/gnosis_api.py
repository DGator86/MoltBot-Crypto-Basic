from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# Try to import Yoshi-Bot (gnosis) code if submodule exists
try:
    import sys
    from pathlib import Path
    _YOSHI_SRC = Path(__file__).resolve().parents[3] / 'bots' / 'Yoshi-Bot' / 'src'
    if _YOSHI_SRC.exists():
        sys.path.append(str(_YOSHI_SRC))
        from gnosis.harness.trade_walkforward import TradeWalkForwardHarness
        from gnosis.loop.ralph import RalphLoop
        _GNOSIS_READY = True
    else:
        _GNOSIS_READY = False
except Exception:
    _GNOSIS_READY = False

class GnosisRunReq(BaseModel):
    path: Optional[str] = None  # JSONL (ts, price|close) or Parquet with prints
    symbol: str = 'BTCUSDT'
    domains_D0_n_trades: int = 200
    horizon_bars: int = 10
    grid: Optional[dict] = None  # hparam grid (keys mapped in RalphLoop)

@router.post("/gnosis/run")
def gnosis_run(req: GnosisRunReq):
    if not _GNOSIS_READY:
        return {"error": "Yoshi-Bot (gnosis) not available; ensure bots/Yoshi-Bot submodule exists"}
    import pandas as pd, json
    from pathlib import Path

    prints = []
    if req.path:
        p = Path(req.path)
        if not p.exists():
            return {"error": f"path not found: {req.path}"}
        if p.suffix.lower() == '.jsonl':
            with p.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except Exception:
                        continue
                    ts = ev.get('ts') or ev.get('timestamp')
                    px = ev.get('price') or ev.get('close')
                    if ts is None or px is None:
                        continue
                    prints.append({
                        'timestamp': pd.to_datetime(int(ts), unit='ms', utc=True),
                        'symbol': req.symbol,
                        'price': float(px),
                        'quantity': 0.001,
                        'side': 'BUY',
                    })
        elif p.suffix.lower() == '.parquet':
            try:
                dfp = pd.read_parquet(p)
                if 'timestamp' in dfp.columns and 'price' in dfp.columns:
                    dfp['timestamp'] = pd.to_datetime(dfp['timestamp'], utc=True)
                    prints = dfp[['timestamp','symbol','price','quantity','side']].to_dict('records')
            except Exception as e:
                return {"error": f"failed to read parquet: {e}"}
    if not prints:
        return {"error": "no prints derived from input"}

    prints_df = pd.DataFrame(prints).sort_values('timestamp').reset_index(drop=True)

    base_cfg = {
        'domains': {'D0': {'n_trades': int(req.domains_D0_n_trades)}},
        'targets': {'horizon_bars': int(req.horizon_bars)},
        'regimes': {},
        'particle': {},
        'models': {},
    }
    grid = req.grid or {
        'domains_D0_n_trades': [int(req.domains_D0_n_trades)],
        'particle_flow_span': [10, 20],
        'predictor_l2_reg': [0.0, 1e-3],
        'confidence_floor_scale': [1.0],
    }
    hparams = {'grid': grid, 'inner_folds': {'n_folds': 3, 'train_ratio': 0.6, 'val_ratio': 0.4}}

    tpb = int(req.domains_D0_n_trades)
    outer = {
        'outer_folds': 4,
        'train_bars': 500,
        'val_bars': 100,
        'test_bars': 100,
        'horizon_bars': int(req.horizon_bars),
    }

    try:
        harness = TradeWalkForwardHarness(outer, trades_per_bar=tpb, horizon_bars_default=int(req.horizon_bars))
        loop = RalphLoop(base_cfg, hparams)
        trials_df, selected = loop.run(prints_df, harness)
    except Exception as e:
        return {"error": f"gnosis run failed: {e}"}

    import json
    from pathlib import Path
    run_id = __import__('uuid').uuid4().hex
    out_dir = Path('data/artifacts/gnosis') / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        trials_csv = out_dir / 'trials.csv'
        trials_df.to_csv(trials_csv, index=False)
        (out_dir / 'selected.json').write_text(json.dumps(selected, indent=2))
        (out_dir / 'run_meta.json').write_text(json.dumps({
            'n_prints': int(len(prints_df)),
            'domains_D0_n_trades': tpb,
            'horizon_bars': int(req.horizon_bars),
        }, indent=2))
    except Exception as e:
        return {"error": f"save artifacts failed: {e}"}

    return {"run_id": run_id, "artifacts": {
        "trials_csv": str(trials_csv),
        "selected_json": str(out_dir / 'selected.json'),
        "meta": str(out_dir / 'run_meta.json'),
    }, "selected": selected, "n_prints": int(len(prints_df))}

@router.get("/gnosis/report/{run_id}")
def gnosis_report(run_id: str):
    from pathlib import Path
    import json
    out_dir = Path('data/artifacts/gnosis') / run_id
    if not out_dir.exists():
        return {"error": "run_id not found"}
    res = {"run_id": run_id}
    try:
        res["selected"] = json.loads((out_dir / 'selected.json').read_text())
    except Exception:
        res["selected"] = None
    res["artifacts"] = [str(p) for p in out_dir.glob('*')]
    return res