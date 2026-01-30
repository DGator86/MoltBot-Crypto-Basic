from __future__ import annotations
from pydantic import BaseModel
from typing import Dict, Any

class CandidateStrategy(BaseModel):
    name: str
    version: str
    params: Dict[str, Any]
    source_ref: str  # e.g., URL or commit hash

class ApprovedStrategy(BaseModel):
    name: str
    version: str
    params: Dict[str, Any]
    signature: str  # promotion signature
