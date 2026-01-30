from __future__ import annotations
import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from moltbot_common_logging import setup_logging  # alias via import trick below

app = FastAPI(title="Trading Core")
setup_logging()
from .risk.kernel import RiskKernel
risk_kernel = RiskKernel()

class OrderReq(BaseModel):
    venue: str
    symbol: str
    side: str
    type: str
    size: float
    price: float | None = None

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/risk")
def risk():
    from moltbot_common_config import load_risk_config
    return load_risk_config()

@app.post("/orders")
def orders(req: OrderReq):
    
from .execution.router import ExecutionRouter
router = ExecutionRouter()
try:
    
    # compute naive notional if price provided
    px = req.price or 0.0
    try:
        notional = float(px) * float(req.size)
    except Exception:
        notional = 0.0
    try:
        risk_kernel.check_order(req.symbol, notional)
    except Exception as e:
        return {"status": "risk_rejected", "error": str(e), "echo": req.model_dump()}
    ack = router.place_order(req.model_dump())
    return {"status": "filled_or_open", "ack": ack}
except Exception as e:
    return {"status": "error", "error": str(e), "echo": req.model_dump()}

# Poor-man aliasing to avoid deep install in dev containers
import sys
sys.modules["moltbot_common_logging"] = __import__("common.logging", fromlist=["setup_logging"]).logging
sys.modules["moltbot_common_config"] = __import__("common.config", fromlist=["load_risk_config"]).config


@app.get("/account")
def account():
    # TODO: wire real balances; placeholder
    return {"equity_usd": None, "note": "stub"}


@app.get("/positions")
def positions():
    # TODO: wire real positions; placeholder
    return {"positions": []}


class CancelReq(BaseModel):
    client_order_id: str

@app.post("/orders/cancel")
def cancel(req: CancelReq):
    # TODO: call adapter cancel; placeholder
    return {"status": "accepted", "client_order_id": req.client_order_id}


@app.post("/risk/pause")
def risk_pause():
    risk_kernel.pause()
    return {"paused": True}

@app.post("/risk/resume")
def risk_resume():
    risk_kernel.resume()
    return {"paused": False}

@app.post("/risk/flatten")
def risk_flatten():
    # TODO: implement flatten-all
    return {"flatten": "requested"}
