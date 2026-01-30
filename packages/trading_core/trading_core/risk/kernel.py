from __future__ import annotations
from typing import Dict, Any
from common.config import load_risk_config

class RiskKernel:
    def __init__(self) -> None:
        self._cfg = load_risk_config().get("risk", {})
        self._paused = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def is_paused(self) -> bool:
        return self._paused

    def limits(self) -> Dict[str, Any]:
        return self._cfg

    def check_order(self, symbol: str, notional_usd: float) -> None:
        if self._paused:
            raise ValueError("trading is paused by risk kernel")
        max_notional = float(self._cfg.get("max_position_notional_usd", 0))
        if max_notional and notional_usd > max_notional:
            raise ValueError(f"order exceeds max notional {max_notional} USD")

    def set_daily_pnl_pct(self, pnl_pct: float) -> None:
        self._daily_pnl_pct = float(pnl_pct)

    def check_daily_loss(self) -> None:
        max_loss = float(self._cfg.get("max_daily_loss_pct", 0))
        pnl = float(getattr(self, '_daily_pnl_pct', 0.0))
        if max_loss and pnl <= -max_loss:
            self.pause()
            raise ValueError(f'daily loss {pnl}% exceeds max {max_loss}% -> paused')

    def slippage_limit_bps(self) -> float:
        return float(self._cfg.get('slippage_bps_limit', 0.0))
