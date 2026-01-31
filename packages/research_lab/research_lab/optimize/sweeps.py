from __future__ import annotations
import os
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Any, Iterable, List, Tuple
import itertools
import pandas as pd
from ..backtest.engine import ema_crossover_backtest
from ..evaluate.scorecards import pass_fail

ART_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "data", "artifacts", "evaluations"))
os.makedirs(ART_DIR, exist_ok=True)


def _run_one(params: Dict[str, Any], df_ser: List[Dict[str, Any]]) -> Dict[str, Any]:
    df = pd.DataFrame(df_ser).rename(columns={'ts': 'index'}).set_index('index')
    res = ema_crossover_backtest(df)
    score = pass_fail(res)
    return {"params": params, "score": score, "n": int(len(res))}


def run_sweeps(
    df_ser: List[Dict[str, Any]],
    fast_range: Iterable[int],
    slow_range: Iterable[int],
    fee_bps: float = 5.0,
    slippage_bps: float = 5.0,
    max_workers: int = 4,
    out_path: str | None = None,
) -> str:
    """
    Run parameter grid sweeps (fast/slow EMAs) over the provided series.
    Writes JSONL results incrementally to avoid memory pressure.
    Designed to scale to 100k+ runs by chunking.
    """
    if out_path is None:
        out_path = os.path.join(ART_DIR, f"sweep_ema_{os.getpid()}.jsonl")
    # Build param combinations
    combos = [
        {"fast": f, "slow": s, "fee_bps": fee_bps, "slippage_bps": slippage_bps}
        for f, s in itertools.product(fast_range, slow_range) if f < s
    ]

    # Chunk to batches of e.g. 500-2000
    chunk_size = 1000
    with open(out_path, 'w', encoding='utf-8') as wf:
        for i in range(0, len(combos), chunk_size):
            batch = combos[i:i+chunk_size]
            with ProcessPoolExecutor(max_workers=max_workers) as ex:
                futs = [ex.submit(_run_one, p, df_ser) for p in batch]
                for fut in as_completed(futs):
                    try:
                        r = fut.result()
                        wf.write(json.dumps(r) + "\n")
                    except Exception as e:
                        wf.write(json.dumps({"error": str(e)}) + "\n")
    return out_path
