from __future__ import annotations
import re
import time
from typing import Dict, Any
from common.schemas.strategies import CandidateStrategy

PATTERNS = [
    re.compile(r"EMA\s*(\d+).+EMA\s*(\d+).+(crossover|cross over)", re.I),
    re.compile(r"RSI\s*(\d+).+(overbought|oversold)", re.I),
]

def extract_candidate(url: str, text: str) -> CandidateStrategy | None:
    for pat in PATTERNS:
        if pat.search(text):
            name = "ema_crossover"
            ts = int(time.time())
            params: Dict[str, Any] = {"fast": 20, "slow": 100, "timeframe": "1m"}
            return CandidateStrategy(
                name=name,
                version=f"{ts}",
                params=params,
                source_ref=url,
            )
    return None
