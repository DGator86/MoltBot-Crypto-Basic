from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Research Lab")
# Mount Gnosis (Yoshi-Bot) API routes if available
try:
    from .gnosis_api import router as __gnosis_router
    app.include_router(__gnosis_router)
except Exception:
    pass

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


from .learners.training import start_training, job_status, score_series

class LearnReq(BaseModel):
    ohlcv: list[dict]
    level: str  # kingdom|phylum|clazz|order|family
    windows: dict | None = None
    aux: dict | None = None  # optional: funding, oi, basis arrays aligned to ohlcv

@app.post("/learn/regime/start")
def learn_regime_start(req: LearnReq):
    jid = start_training(req.ohlcv, req.level, req.windows, req.aux)
    return {"job_id": jid}

@app.get("/learn/regime/status/{job_id}")
def learn_regime_status(job_id: str):
    return job_status(job_id)

class ScoreReq(BaseModel):
    ohlcv: list[dict]
    level: str

@app.post("/score/regime")
def score_regime(req: ScoreReq):
    return score_series(req.ohlcv, req.level)


from .ingest.derivatives_adapter import extract_derivatives_series
from .features.orderbook_profile import volume_profile_from_trades, hvn_lvn

class DerivsReq(BaseModel):
    path: str
    ohlcv: list[dict] | None = None

@app.post("/ingest/derivs")
def ingest_derivs(req: DerivsReq):
    series = extract_derivatives_series(req.path)
    out = {"counts": {k: len(v) for k, v in series.items()}, "aux": {k: series[k] for k in ("funding","oi","basis")}}
    if req.ohlcv:
        # Optionally create a simple profile from provided series
        prof = volume_profile_from_trades(req.ohlcv)
        nodes = hvn_lvn(prof)
        out["profile"] = prof
        out["nodes"] = nodes
    return out

# -----------------------------
# Gnosis (Yoshi-Bot) integration
# -----------------------------
from pydantic import BaseModel as _GnosisBM
from .gnosis_runner import run_gnosis
from .gnosis_api import router as gnosis_router

class GnosisRunReq(_GnosisBM):
    source: dict
    base_config: dict | None = None
    hparams: dict | None = None

@app.post("/gnosis/run")
def gnosis_run(req: GnosisRunReq):
    run_id, report = run_gnosis(req.source, req.base_config, req.hparams)
    return {"run_id": run_id, "report": report}

@app.get("/gnosis/report/{run_id}")
def gnosis_report(run_id: str):
    from pathlib import Path
    import json
    p = Path("data/artifacts/gnosis")/run_id/"report.json"
    if not p.exists():
        return {"error": "not_found", "run_id": run_id}
    return json.loads(p.read_text())

# Mount alternate Gnosis API that can consume OHLCV JSONL directly
app.include_router(gnosis_router)
