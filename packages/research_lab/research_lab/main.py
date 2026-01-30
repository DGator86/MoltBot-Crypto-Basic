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
