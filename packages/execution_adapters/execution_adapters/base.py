from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any

class ExecutionAdapter(ABC):
    @abstractmethod
    def create_order(self, req: Dict[str, Any]) -> Dict[str, Any]:
        ...
