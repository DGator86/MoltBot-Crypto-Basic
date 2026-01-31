from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple
from particle_bot.utils.stats import clamp

@dataclass
class Thresholds:
    trend_strength: float = 0.75
    mr_strength: float = 0.60
    compression_pct: float = 0.15
    expansion_pct: float = 0.75
    funding_z_crowded: float = 1.25
    oi_z_hot: float = 1.0
    absorption_vol_mult: float = 1.5
    absorption_progress_sigma: float = 0.25

T = Thresholds()

def kingdom(f: Dict[str, Any]) -> Tuple[str, float]:
    dir_strength = f.get("directional_strength", 0.0)
    mr_score = f.get("mean_reversion_score", 0.0)
    tail_risk = f.get("tail_risk", 0.0)
    breakout_prob = f.get("breakout_prob", 0.0)

    if tail_risk > 0.8 and dir_strength > 0.7:
        return ("crash_or_melt", clamp(0.5 + 0.5 * tail_risk, 0, 1))

    if breakout_prob > 0.75:
        return ("breakout", breakout_prob)

    if dir_strength > T.trend_strength and mr_score < 0.45:
        return ("trend", clamp(dir_strength, 0, 1))

    if mr_score > T.mr_strength and dir_strength < 0.55:
        return ("mean_revert", clamp(mr_score, 0, 1))

    return ("range", 0.55)

def phylum(f: Dict[str, Any]) -> Tuple[str, float]:
    vol_pct = f.get("vol_percentile", 0.5)
    vov = min(1.0, f.get("tail_risk", 0.0) + max(0.0, f.get("basis_z", 0.0)) * 0.1)

    if vol_pct < T.compression_pct and vov < 0.35:
        return ("compression", clamp(1.0 - vol_pct, 0, 1))
    if vol_pct > T.expansion_pct or vov > 0.7:
        return ("expansion", clamp(vol_pct, 0, 1))
    if vol_pct > 0.6:
        return ("elevated", vol_pct)
    return ("decay", 0.55)

def clazz(f: Dict[str, Any]) -> Tuple[str, float]:
    fz = f.get("funding_z", 0.0)
    oiz = f.get("oi_z", 0.0)
    basis_pct = f.get("basis_percentile", 0.5)
    deleveraging = f.get("deleveraging_score", 0.0)

    if deleveraging > 0.7:
        return ("deleveraging", deleveraging)

    if fz > T.funding_z_crowded and oiz > T.oi_z_hot and basis_pct > 0.7:
        return ("crowded_long", clamp((fz/2.0 + oiz/2.0) / 2.0, 0, 1))

    if fz < -T.funding_z_crowded and oiz > T.oi_z_hot and basis_pct < 0.3:
        return ("crowded_short", clamp((-fz/2.0 + oiz/2.0) / 2.0, 0, 1))

    squeeze = f.get("squeeze_score", 0.0)
    if squeeze > 0.65:
        return ("squeeze_setup", squeeze)

    return ("balanced", 0.55)

def family(f: Dict[str, Any]) -> Tuple[str, float]:
    vol_mult = f.get("vol_mult", 1.0)
    progress_sigma = f.get("progress_sigma", 0.0)
    impulse = f.get("impulse_score", 0.0)
    exhaustion = f.get("exhaustion_score", 0.0)
    stoprun = f.get("stoprun_score", 0.0)

    if stoprun > 0.7:
        return ("stop_run", stoprun)

    if vol_mult > T.absorption_vol_mult and progress_sigma < T.absorption_progress_sigma:
        conf = clamp((vol_mult/2.0) * (1.0 - progress_sigma), 0, 1)
        return ("absorption", conf)

    if exhaustion > 0.65:
        return ("exhaustion", exhaustion)

    if impulse > 0.65:
        return ("impulse", impulse)

    return ("neutral", 0.55)
