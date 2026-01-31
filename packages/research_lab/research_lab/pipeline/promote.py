from __future__ import annotations
import json
import os
import time
from typing import Dict, Any

ART_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "data", "artifacts", "promotions"))
os.makedirs(ART_DIR, exist_ok=True)

def create_promotion(candidate: Dict[str, Any]) -> str:
    ts = int(time.time())
    pid = f"promo_{candidate.get('name','cand')}_{ts}"
    path = os.path.join(ART_DIR, f"{pid}.json")
    out = {"candidate": candidate, "created_at": ts, "signature": "UNSIGNED-PLACEHOLDER"}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return pid
