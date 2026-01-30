from __future__ import annotations
import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from moltbot_common_logging import setup_logging  # alias via import trick below

app = FastAPI(title="Trading Core")
setup_logging()

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
    ack = router.place_order(req.model_dump())
    return {"status": "filled_or_open", "ack": ack}
except Exception as e:
    return {"status": "error", "error": str(e), "echo": req.model_dump()}

# Poor-man aliasing to avoid deep install in dev containers
import sys
sys.modules["moltbot_common_logging"] = __import__("common.logging", fromlist=["setup_logging"]).logging
sys.modules["moltbot_common_config"] = __import__("common.config", fromlist=["load_risk_config"]).config
