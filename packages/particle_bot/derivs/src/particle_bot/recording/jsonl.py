from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Iterable, Iterator, Dict, Any
import json
from datetime import datetime, timezone

from particle_bot.types import (
    BaseEvent, EventType, TradePrint, BookDelta, FundingTick, OITick, BasisTick,
    LiquidationSnapshot, OnchainSnapshot, MacroSnapshot, Venue, Symbol, TradeSide, BookLevel
)

EVENT_MODEL_BY_TYPE = {
    EventType.TRADE_PRINT: TradePrint,
    EventType.BOOK_DELTA: BookDelta,
    EventType.FUNDING_TICK: FundingTick,
    EventType.OI_TICK: OITick,
    EventType.BASIS_TICK: BasisTick,
    EventType.LIQUIDATION_SNAPSHOT: LiquidationSnapshot,
    EventType.ONCHAIN_SNAPSHOT: OnchainSnapshot,
    EventType.MACRO_SNAPSHOT: MacroSnapshot,
}

def _dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def _iso_to_dt(s: str) -> datetime:
    # Python 3.11+ supports fromisoformat with offsets; we assume UTC 'Z' not used.
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

@dataclass
class JSONLRecorder:
    path: Path
    flush_every: int = 200
    _n: int = 0
    _fh: Optional[object] = None

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def close(self) -> None:
        if self._fh:
            self._fh.flush()
            self._fh.close()
            self._fh = None

    def write_event(self, ev: BaseEvent) -> None:
        assert self._fh is not None
        d = ev.model_dump()
        # Ensure datetimes are ISO strings (pydantic may already do this, but keep explicit).
        d["ts"] = _dt_to_iso(ev.ts)
        d["recv_ts"] = _dt_to_iso(ev.recv_ts)
        self._fh.write(json.dumps(d, separators=(",", ":")) + "\n")
        self._n += 1
        if self._n % self.flush_every == 0:
            self._fh.flush()

def iter_events(path: Path) -> Iterator[BaseEvent]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw: Dict[str, Any] = json.loads(line)
            et = EventType(raw["etype"])
            model = EVENT_MODEL_BY_TYPE.get(et)
            if model is None:
                # fall back to BaseEvent
                raw["ts"] = _iso_to_dt(raw["ts"])
                raw["recv_ts"] = _iso_to_dt(raw["recv_ts"])
                yield BaseEvent(**raw)
            else:
                raw["ts"] = _iso_to_dt(raw["ts"])
                raw["recv_ts"] = _iso_to_dt(raw["recv_ts"])
                yield model(**raw)
