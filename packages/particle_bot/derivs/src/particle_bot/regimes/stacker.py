from __future__ import annotations
from typing import Dict, Any
from particle_bot.regimes.rules import kingdom, phylum, clazz, family
from particle_bot.regimes.taxonomy import RegimeStack
from particle_bot.utils.stats import clamp

def build_regime_stack(f: Dict[str, Any]) -> RegimeStack:
    # Universe (MVP): infer from funding+vol; replace with macro later
    univ = "risk_on" if f.get("funding_z", 0.0) > 0.25 and f.get("vol_percentile", 0.5) < 0.75 else "neutral"
    if f.get("tail_risk", 0.0) > 0.7 and f.get("vol_percentile", 0.5) > 0.75:
        univ = "risk_off"

    k, kp = kingdom(f)
    p, pp = phylum(f)
    c, cp = clazz(f)
    fam, fp = family(f)

    # Order/Genus/Species MVP placeholders (filled with fields + cone later)
    order = "liquidity_topology_pending"
    genus = "setup_pending"
    species = "execution_pending"

    # stability: inversely related to tail risk + near-breakout
    stability = float(clamp(1.0 - (f.get("tail_risk", 0.0) * 0.6 + f.get("breakout_prob", 0.0) * 0.4), 0.0, 1.0))

    return RegimeStack(
        universe=univ,
        kingdom=k,
        phylum=p,
        clazz=c,
        order=order,
        family=fam,
        genus=genus,
        species=species,
        probs={
            "universe": 0.6,
            "kingdom": kp,
            "phylum": pp,
            "clazz": cp,
            "family": fp,
        },
        stability=stability,
    )
