from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Research Lab")

class IngestReq(BaseModel):
    urls: List[str]

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest")
def ingest(req: IngestReq):
    # TODO: enforce allowlist and fetch content into corpora
    return {"ingested": len(req.urls)}

@app.get("/candidates")
def candidates():
    return {"candidates": []}


from pydantic import BaseModel
from typing import Dict, Any
import pandas as pd
from .backtest.engine import ema_crossover_backtest
from .backtest.walkforward import walkforward
from .evaluate.scorecards import pass_fail
from .pipeline.promote import create_promotion

class BacktestReq(BaseModel):
    ohlcv: list[dict]

class EvaluateReq(BaseModel):
    ohlcv: list[dict]

class PromoteReq(BaseModel):
    candidate: Dict[str, Any]

@app.post("/backtest")
def backtest(req: BacktestReq):
    df = pd.DataFrame(req.ohlcv)
    if 'close' not in df.columns:
        return {"error": "missing close in ohlcv"}
    res = ema_crossover_backtest(df)
    return {"final_equity": float(res['equity'].iloc[-1]), "n": int(len(res))}

@app.post("/evaluate")
def evaluate(req: EvaluateReq):
    df = pd.DataFrame(req.ohlcv)
    res = ema_crossover_backtest(df)
    meta = pass_fail(res)
    wf = walkforward(df)
    return {"score": meta, "walkforward": wf}

@app.post("/promote")
def promote(req: PromoteReq):
    pid = create_promotion(req.candidate)
    return {"promotion_id": pid}


from .ingest.particle_adapter import extract_trades, trades_to_close_series

class ParticleIngestReq(BaseModel):
    path: str

@app.post("/ingest/particle")
def ingest_particle(req: ParticleIngestReq):
    ts, px = extract_trades(req.path)
    ohlcv = trades_to_close_series(ts, px)
    return {"trades": len(px), "series_points": len(ohlcv)}

class ParticleEvalReq(BaseModel):
    path: str

@app.post("/evaluate/particle")
def evaluate_particle(req: ParticleEvalReq):
    ts, px = extract_trades(req.path)
    ohlcv = trades_to_close_series(ts, px)
    import pandas as pd
    if not ohlcv:
        return {"error": "no trades found"}
    df = pd.DataFrame(ohlcv).sort_values('ts')
    res = ema_crossover_backtest(df.rename(columns={'ts':'index'}).set_index('index'))
    meta = pass_fail(res)
    wf = walkforward(res[['close','strat_ret','equity']].rename_axis('ts').reset_index().set_index('ts'))
    return {"score": meta, "walkforward": wf, "n": int(len(res))}


from .backtest.simulator import simulate_paper, SimOrder, SimConfig
from .optimize.sweeps import run_sweeps
import threading

class PaperReq(BaseModel):
    ohlcv: list[dict]
    orders: list[dict]
    config: dict | None = None

@app.post("/simulate/paper")
def simulate_paper_api(req: PaperReq):
    cfg = SimConfig(**(req.config or {}))
    orders = [SimOrder(**o) for o in req.orders]
    out = simulate_paper(req.ohlcv, orders, cfg)
    return out

_SWEEPS: dict[str, dict] = {}

class SweepReq(BaseModel):
    ohlcv: list[dict]
    fast_range: list[int]
    slow_range: list[int]
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    max_workers: int = 4

@app.post("/sweeps/start")
def sweeps_start(req: SweepReq):
    import uuid
    sid = str(uuid.uuid4())
    _SWEEPS[sid] = {"status": "running", "out": None}
    def _run():
        out_path = run_sweeps(req.ohlcv, req.fast_range, req.slow_range, req.fee_bps, req.slippage_bps, req.max_workers)
        _SWEEPS[sid] = {"status": "done", "out": out_path}
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return {"sweep_id": sid}

@app.get("/sweeps/status/{sid}")
def sweeps_status(sid: str):
    return _SWEEPS.get(sid, {"status": "unknown"})
