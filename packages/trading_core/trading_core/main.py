from __future__ import annotations
import os
import sys
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

# Poor-man aliasing to avoid deep install in dev containers
sys.modules["moltbot_common_logging"] = __import__("common.logging", fromlist=["setup_logging"]).logging
sys.modules["moltbot_common_config"] = __import__("common.config", fromlist=["load_risk_config"]).config

from moltbot_common_logging import setup_logging  # type: ignore

app = FastAPI(title="Trading Core")
setup_logging()

from .risk.kernel import RiskKernel
from .execution.router import ExecutionRouter

risk_kernel = RiskKernel()
router = ExecutionRouter()


class OrderReq(BaseModel):
    venue: str
    symbol: str
    side: str
    type: str
    size: float
    price: float | None = None


class CancelReq(BaseModel):
    client_order_id: str


class PreviewReq(BaseModel):
    symbol: str
    side: str
    type: str
    size: float
    price: float | None = None
    mid_price: float | None = None


class PnLReq(BaseModel):
    pnl_pct: float


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/risk")
def risk():
    from moltbot_common_config import load_risk_config  # type: ignore
    return load_risk_config()


@app.post("/orders")
def orders(req: OrderReq):
    # basic notional check
    px = req.price or 0.0
    try:
        notional = float(px) * float(req.size)
    except Exception:
        notional = 0.0
    try:
        risk_kernel.check_order(req.symbol, notional)
    except Exception as e:
        return {"status": "risk_rejected", "error": str(e), "echo": req.model_dump()}

    try:
        ack = router.place_order(req.model_dump())
        return {"status": "filled_or_open", "ack": ack}
    except Exception as e:
        return {"status": "error", "error": str(e), "echo": req.model_dump()}


@app.post("/orders/cancel")
def cancel(req: CancelReq):
    # TODO: wire adapter cancel
    return {"status": "accepted", "client_order_id": req.client_order_id}


@app.post("/orders/preview")
def orders_preview(req: PreviewReq):
    from .execution.slippage import slippage_bps as _slip
    lim = risk_kernel.slippage_limit_bps()
    mid = req.mid_price or 0.0
    if not mid:
        try:
            from execution_adapters.ccxt_exec import CCXTExecution
            ex = CCXTExecution('binance', os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
            tk = ex.fetch_ticker(req.symbol)
            bid = float(tk.get('bid') or 0)
            ask = float(tk.get('ask') or 0)
            if bid and ask:
                mid = (bid + ask) / 2.0
        except Exception:
            pass
    px = req.price or mid
    s_bps = _slip(px, mid) if mid else 0.0
    ok = (s_bps <= lim) if lim else True
    return {"ok": ok, "slippage_bps": s_bps, "limit_bps": lim}


@app.post("/risk/telemetry/pnl")
def risk_telemetry_pnl(req: PnLReq):
    try:
        risk_kernel.set_daily_pnl_pct(req.pnl_pct)
        risk_kernel.check_daily_loss()
        return {"ok": True, "paused": risk_kernel.is_paused()}
    except Exception as e:
        return {"ok": False, "error": str(e), "paused": risk_kernel.is_paused()}


@app.get("/account")
def account():
    try:
        from execution_adapters.ccxt_exec import CCXTExecution
        ex = CCXTExecution('binance', os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
        bal = ex.fetch_balance()
        return {"balance": bal}
    except Exception as e:
        return {"error": str(e)}


@app.get("/positions")
def positions():
    try:
        from execution_adapters.ccxt_exec import CCXTExecution
        ex = CCXTExecution('binance', os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
        poss = ex.fetch_positions()
        return {"positions": poss}
    except Exception as e:
        return {"error": str(e), "positions": []}


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
    # TODO: implement flatten-all: iterate positions and send opposing orders
    return {"flatten": "requested"}


@app.get("/regime/current")
def regime_current(product: str = "BTC-USD", level: str = "order", lookback: int = 1000):
    """Return current regime scores by proxying Research Lab scoring.
    Loads cached Coinbase OHLCV from data/raw.
    """
    import os, json
    from pathlib import Path

    base = Path("data/raw")
    files = [
        base / f"cbx_{product.replace('-', '_')}_1m_30d.jsonl",
        base / f"cbx_{product.replace('-', '_')}_1m.jsonl",
    ]
    ohlcv: list[dict] = []
    for fp in files:
        if fp.exists():
            with fp.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ohlcv.append(json.loads(line))
                    except Exception:
                        pass
            break
    if not ohlcv:
        return {"error": f"no cached OHLCV for {product}"}

    ohlcv = ohlcv[-max(10, int(lookback)) :]
    rl_url = os.environ.get("RESEARCH_LAB_URL", "http://localhost:8002")
    try:
        import requests
        r = requests.post(f"{rl_url}/score/regime", json={"ohlcv": ohlcv, "level": level}, timeout=20)
        return {"product": product, "level": level, "scores": r.json(), "n": len(ohlcv)}
    except Exception as e:
        return {"error": str(e), "product": product, "level": level}
