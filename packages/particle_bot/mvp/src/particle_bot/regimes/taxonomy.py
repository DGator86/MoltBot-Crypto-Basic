from __future__ import annotations
from pydantic import BaseModel
from typing import Dict

class RegimeStack(BaseModel):
    universe: str
    kingdom: str
    phylum: str
    clazz: str
    order: str
    family: str
    genus: str
    species: str
    probs: Dict[str, float]
    stability: float
