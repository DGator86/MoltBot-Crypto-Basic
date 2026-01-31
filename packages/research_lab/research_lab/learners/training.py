from __future__ import annotations
import os
import uuid
import threading
from typing import Dict, Any, List
import joblib
from .dataset import build_dataset
from .regime_classifier import RegimeClassifier

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "data", "artifacts", "models"))
os.makedirs(MODELS_DIR, exist_ok=True)

_JOBS: Dict[str, Dict[str, Any]] = {}


def start_training(ohlcv: List[dict], level: str, windows: Dict[str,int] | None = None, aux: Dict[str,Any] | None = None) -> str:
    jid = str(uuid.uuid4())
    _JOBS[jid] = {"status": "running", "model_path": None, "metrics": None}
    def _run():
        try:
            X, y = build_dataset(ohlcv, level, windows, aux)
            clf = RegimeClassifier()
            clf.fit(X, y)
            path = os.path.join(MODELS_DIR, f"regime_{level}.joblib")
            joblib.dump({"model": clf, "features": list(X.columns), "level": level}, path)
            _JOBS[jid] = {"status": "done", "model_path": path, "metrics": {"n": len(X), "classes": list(sorted(set(y)))}}
        except Exception as e:
            _JOBS[jid] = {"status": "error", "error": str(e)}
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jid


def job_status(jid: str) -> Dict[str, Any]:
    return _JOBS.get(jid, {"status": "unknown"})


def score_series(ohlcv: List[dict], model_level: str) -> Dict[str, Any]:
    import joblib
    path = os.path.join(MODELS_DIR, f"regime_{model_level}.joblib")
    if not os.path.exists(path):
        return {"error": "model not found"}
    payload = joblib.load(path)
    clf = payload['model']
    X, _ = build_dataset(ohlcv, model_level)
    probs = clf.predict_proba(X)
    preds = clf.predict(X)
    return {"n": len(X), "preds": preds.tolist(), "probs": probs.tolist(), "features": payload['features']}
