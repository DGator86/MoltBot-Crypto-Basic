from __future__ import annotations
import json
import uuid
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import pandas as pd

# Wire Yoshi-Bot (Gnosis) source path so we can import its modules
import sys
_GNOSIS_SRC = Path(__file__).resolve().parents[3] / 'bots' / 'Yoshi-Bot' / 'src'
if _GNOSIS_SRC.exists():
    sys.path.append(str(_GNOSIS_SRC))

try:
    from gnosis.loop.ralph import RalphLoop
    from gnosis.harness.trade_walkforward import TradeWalkForwardHarness
except Exception as e:  # pragma: no cover - handled at runtime
    RalphLoop = None  # type: ignore
    TradeWalkForwardHarness = None  # type: ignore


def _iter_jsonl(path: Path):
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def load_prints_from_particle(path: str, default_symbol: str = 'BTC-USD') -> pd.DataFrame:
    """
    Load trade prints from a particle-style JSONL file and produce a prints DataFrame
    with columns: symbol, timestamp (ms), price, quantity, side ('BUY'|'SELL').
    Falls back to neutral values when fields are missing.
    """
    p = Path(path)
    rows = []
    for ev in _iter_jsonl(p):
        etype = (ev.get('etype') or ev.get('event_type') or '').lower()
        if etype not in {'trade_print', 'trade'}:
            continue
        ts = ev.get('ts') or ev.get('timestamp') or ev.get('t')
        try:
            ts = int(ts)
        except Exception:
            continue
        price = ev.get('price')
        try:
            px = float(price)
        except Exception:
            continue
        qty = ev.get('size') or ev.get('quantity') or 1.0
        try:
            qty = float(qty)
        except Exception:
            qty = 1.0
        side = (ev.get('side') or ev.get('aggressor_side') or 'UNKNOWN').upper()
        if side.startswith('B'):
            side = 'BUY'
        elif side.startswith('S'):
            side = 'SELL'
        else:
            # Neutral default: alternate BUY/SELL by tick direction if possible
            side = 'BUY'
        symbol = ev.get('symbol') or default_symbol
        rows.append({'symbol': symbol, 'timestamp': ts, 'price': px, 'quantity': qty, 'side': side})
    if not rows:
        return pd.DataFrame(columns=['symbol', 'timestamp', 'price', 'quantity', 'side'])
    df = pd.DataFrame(rows)
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def run_gnosis(path: str,
               base_config: Optional[Dict[str, Any]] = None,
               hparams: Optional[Dict[str, Any]] = None,
               harness_cfg: Optional[Dict[str, Any]] = None,
               default_symbol: str = 'BTC-USD') -> Tuple[str, Dict[str, Any]]:
    """
    Execute Gnosis RalphLoop on trade prints from a particle JSONL file.

    Returns (run_id, summary_json) and writes artifacts under data/artifacts/gnosis/{run_id}/
    """
    if RalphLoop is None or TradeWalkForwardHarness is None:
        raise RuntimeError('Gnosis modules not available. Ensure bots/Yoshi-Bot submodule exists.')

    prints_df = load_prints_from_particle(path, default_symbol=default_symbol)
    if prints_df.empty:
        raise ValueError('No trade prints found in the provided file')

    # Defaults
    base_config = base_config or {
        'domains': {
            'D0': {'n_trades': 200},
        },
        'targets': {'horizon_bars': 10},
        'regimes': {},
        'particle': {'flow': {'span': 50}},
        'models': {'predictor': {}}
    }
    hparams = hparams or {
        'grid': {
            'domains_D0_n_trades': [100, 200, 300],
            'particle_flow_span': [25, 50, 100],
        },
        'inner_folds': {'n_folds': 3, 'train_ratio': 0.6, 'val_ratio': 0.4},
        'target_coverage': 0.90,
    }
    trades_per_bar = int(base_config.get('domains', {}).get('D0', {}).get('n_trades', 200))

    harness_cfg = harness_cfg or {
        'outer_folds': 6,
        'train_bars': 500,  # used only if *_trades not provided
        'val_bars': 100,
        'test_bars': 100,
        'horizon_bars': 10,
        'purge_trades': 'HORIZON',
        'embargo_trades': 'HORIZON',
    }

    harness = TradeWalkForwardHarness(harness_cfg, trades_per_bar=trades_per_bar, horizon_bars_default=10)
    loop = RalphLoop(base_config, hparams)

    trials_df, selection = loop.run(prints_df, harness)

    run_id = str(uuid.uuid4())
    out_dir = Path('data/artifacts/gnosis') / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    # Save trials and selection
    try:
        trials_df.to_parquet(out_dir / 'trials.parquet', index=False)
    except Exception:
        trials_df.to_csv(out_dir / 'trials.csv', index=False)
    (out_dir / 'selection.json').write_text(json.dumps(selection, indent=2))

    summary = {
        'run_id': run_id,
        'n_prints': int(len(prints_df)),
        'artifacts': {
            'trials': str(out_dir / ('trials.parquet' if (out_dir / 'trials.parquet').exists() else 'trials.csv')),
            'selection': str(out_dir / 'selection.json'),
        },
        'selection': selection,
    }
    return run_id, summary
