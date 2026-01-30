from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Research Lab")

class IngestReq(BaseModel):
    urls: List[str]

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest")
def ingest(req: IngestReq):
    # TODO: enforce allowlist and fetch content into corpora
    return {"ingested": len(req.urls)}

@app.get("/candidates")
def candidates():
    return {"candidates": []}
