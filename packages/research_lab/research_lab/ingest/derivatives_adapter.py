from __future__ import annotations
import json
from typing import Iterable, Dict, Any, Tuple, List

# Event types expected from particle/derivs JSONL: funding_tick, oi_tick, basis_tick

DERIV_TYPES = {
    'funding_tick', 'funding', 'FUNDING_TICK',
    'oi_tick', 'open_interest', 'OI_TICK',
    'basis_tick', 'basis', 'BASIS_TICK'
}


def iter_events_jsonl(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def extract_derivatives_series(path: str) -> Dict[str, List[float]]:
    funding: List[float] = []
    oi: List[float] = []
    basis: List[float] = []
    ts_f: List[int] = []
    ts_oi: List[int] = []
    ts_b: List[int] = []
    for ev in iter_events_jsonl(path):
        et = str(ev.get('etype') or ev.get('event_type') or '').lower()
        if 'funding' in et:
            val = ev.get('funding_rate') or ev.get('funding') or 0.0
            ts = ev.get('ts') or ev.get('timestamp') or 0
            try:
                funding.append(float(val))
                ts_f.append(int(ts))
            except Exception:
                pass
        elif et.endswith('oi_tick') or 'open_interest' in et or 'oi' == et:
            val = ev.get('open_interest') or ev.get('oi') or 0.0
            ts = ev.get('ts') or ev.get('timestamp') or 0
            try:
                oi.append(float(val))
                ts_oi.append(int(ts))
            except Exception:
                pass
        elif 'basis' in et:
            val = ev.get('basis') or 0.0
            ts = ev.get('ts') or ev.get('timestamp') or 0
            try:
                basis.append(float(val))
                ts_b.append(int(ts))
            except Exception:
                pass
    return {"funding": funding, "oi": oi, "basis": basis, "ts_f": ts_f, "ts_oi": ts_oi, "ts_b": ts_b}
