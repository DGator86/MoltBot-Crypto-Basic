"""
Trading Core - FastAPI application for executing trades on Binance and Coinbase
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import ccxt
from decimal import Decimal
import asyncio
from datetime import datetime, timezone

app = FastAPI(title="Moltbot Trading Core", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class TradingState:
    def __init__(self):
        self.is_paused = False
        self.kill_switch_active = False
        self.positions: Dict[str, Any] = {}
        self.risk_limits = {
            'max_position_size': Decimal('10000'),
            'max_total_exposure': Decimal('50000'),
            'max_leverage': Decimal('3')
        }

state = TradingState()

# Models
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"

class Exchange(str, Enum):
    BINANCE = "binance"
    COINBASE = "coinbase"

class OrderRequest(BaseModel):
    exchange: Exchange
    symbol: str
    side: OrderSide
    type: OrderType
    amount: float
    price: Optional[float] = None

class OrderResponse(BaseModel):
    order_id: str
    exchange: Exchange
    symbol: str
    side: OrderSide
    amount: float
    price: Optional[float]
    status: str
    timestamp: datetime

class Position(BaseModel):
    exchange: Exchange
    symbol: str
    amount: float
    entry_price: float
    current_price: float
    unrealized_pnl: float

class RiskCheck(BaseModel):
    passed: bool
    reason: Optional[str] = None

# Exchange clients
class ExchangeManager:
    def __init__(self):
        self.exchanges = {}
    
    def get_exchange(self, exchange: Exchange, api_key: str = None, secret: str = None):
        """Get or create exchange instance"""
        if exchange == Exchange.BINANCE:
            if 'binance' not in self.exchanges:
                self.exchanges['binance'] = ccxt.binance({
                    'apiKey': api_key,
                    'secret': secret,
                    'enableRateLimit': True,
                })
            return self.exchanges['binance']
        elif exchange == Exchange.COINBASE:
            # Using CCXT for Coinbase as well for consistency
            if 'coinbase' not in self.exchanges:
                self.exchanges['coinbase'] = ccxt.coinbase({
                    'apiKey': api_key,
                    'secret': secret,
                    'enableRateLimit': True,
                })
            return self.exchanges['coinbase']
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")

exchange_manager = ExchangeManager()

# Risk management
def check_risk(order: OrderRequest) -> RiskCheck:
    """Check if order passes risk limits"""
    if state.kill_switch_active:
        return RiskCheck(passed=False, reason="Kill switch is active")
    
    if state.is_paused:
        return RiskCheck(passed=False, reason="Trading is paused")
    
    # Check position size
    order_value = Decimal(str(order.amount)) * Decimal(str(order.price or 0))
    if order_value > state.risk_limits['max_position_size']:
        return RiskCheck(
            passed=False, 
            reason=f"Order size {order_value} exceeds max position size {state.risk_limits['max_position_size']}"
        )
    
    # Check total exposure
    total_exposure = sum(Decimal(str(p.get('value', 0))) for p in state.positions.values())
    if total_exposure + order_value > state.risk_limits['max_total_exposure']:
        return RiskCheck(
            passed=False,
            reason=f"Total exposure would exceed limit"
        )
    
    return RiskCheck(passed=True)

# Routes
@app.get("/")
async def root():
    return {"status": "ok", "service": "Trading Core", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "paused": state.is_paused,
        "kill_switch": state.kill_switch_active,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/status")
async def get_status():
    """Get trading system status"""
    return {
        "is_paused": state.is_paused,
        "kill_switch_active": state.kill_switch_active,
        "positions_count": len(state.positions),
        "risk_limits": {k: str(v) for k, v in state.risk_limits.items()},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/positions")
async def get_positions() -> List[Position]:
    """Get current positions"""
    positions = []
    for key, pos in state.positions.items():
        positions.append(Position(
            exchange=pos['exchange'],
            symbol=pos['symbol'],
            amount=pos['amount'],
            entry_price=pos['entry_price'],
            current_price=pos.get('current_price', pos['entry_price']),
            unrealized_pnl=pos.get('unrealized_pnl', 0.0)
        ))
    return positions

@app.post("/orders")
async def place_order(order: OrderRequest) -> OrderResponse:
    """Place a new order"""
    # Risk check
    risk_check = check_risk(order)
    if not risk_check.passed:
        raise HTTPException(status_code=400, detail=risk_check.reason)
    
    try:
        exchange = exchange_manager.get_exchange(order.exchange)
        
        # Place order via CCXT
        if order.type == OrderType.MARKET:
            result = exchange.create_market_order(
                order.symbol,
                order.side.value,
                order.amount
            )
        else:  # LIMIT
            if not order.price:
                raise HTTPException(status_code=400, detail="Price required for limit orders")
            result = exchange.create_limit_order(
                order.symbol,
                order.side.value,
                order.amount,
                order.price
            )
        
        # Update positions
        position_key = f"{order.exchange}_{order.symbol}"
        if position_key not in state.positions:
            state.positions[position_key] = {
                'exchange': order.exchange,
                'symbol': order.symbol,
                'amount': 0.0,
                'entry_price': 0.0,
                'value': 0.0
            }
        
        # Update position (simplified)
        if order.side == OrderSide.BUY:
            state.positions[position_key]['amount'] += order.amount
        else:
            state.positions[position_key]['amount'] -= order.amount
        
        return OrderResponse(
            order_id=result['id'],
            exchange=order.exchange,
            symbol=order.symbol,
            side=order.side,
            amount=result.get('amount', order.amount),
            price=result.get('price'),
            status=result.get('status', 'open'),
            timestamp=datetime.now(timezone.utc)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order failed: {str(e)}")

@app.post("/pause")
async def pause_trading():
    """Pause all trading"""
    state.is_paused = True
    return {"status": "paused", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/resume")
async def resume_trading():
    """Resume trading"""
    state.is_paused = False
    return {"status": "resumed", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/flatten")
async def flatten_all_positions():
    """Close all positions (flatten)"""
    if state.kill_switch_active:
        raise HTTPException(status_code=400, detail="Kill switch is active")
    
    results = []
    for key, position in list(state.positions.items()):
        try:
            if position['amount'] != 0:
                exchange = exchange_manager.get_exchange(position['exchange'])
                side = 'sell' if position['amount'] > 0 else 'buy'
                amount = abs(position['amount'])
                
                result = exchange.create_market_order(
                    position['symbol'],
                    side,
                    amount
                )
                results.append({
                    'symbol': position['symbol'],
                    'status': 'closed',
                    'order_id': result['id']
                })
                
                # Remove position
                del state.positions[key]
        except Exception as e:
            results.append({
                'symbol': position['symbol'],
                'status': 'error',
                'error': str(e)
            })
    
    return {
        "status": "flattened",
        "results": results,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/kill-switch")
async def activate_kill_switch():
    """Activate kill switch - stops all trading and flattens positions"""
    state.kill_switch_active = True
    state.is_paused = True
    
    # Flatten all positions
    flatten_result = await flatten_all_positions()
    
    return {
        "status": "kill_switch_activated",
        "flatten_result": flatten_result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/kill-switch/deactivate")
async def deactivate_kill_switch():
    """Deactivate kill switch"""
    state.kill_switch_active = False
    return {
        "status": "kill_switch_deactivated",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/propose")
async def propose_trade(order: OrderRequest):
    """Propose a trade for approval"""
    # Just validate, don't execute
    risk_check = check_risk(order)
    return {
        "proposal_id": f"prop_{datetime.now(timezone.utc).timestamp()}",
        "order": order.model_dump(),
        "risk_check": risk_check.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/approve/{proposal_id}")
async def approve_trade(proposal_id: str, order: OrderRequest):
    """Approve and execute a proposed trade"""
    # In a real system, would validate proposal_id
    return await place_order(order)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
