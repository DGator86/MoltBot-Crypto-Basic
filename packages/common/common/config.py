from __future__ import annotations
import os
import yaml
from typing import Any, Dict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIG_DIR = os.path.join(BASE_DIR, "configs")


def _read_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_app_config() -> Dict[str, Any]:
    return _read_yaml(os.path.join(CONFIG_DIR, "app.yaml"))


def load_exchanges_config() -> Dict[str, Any]:
    return _read_yaml(os.path.join(CONFIG_DIR, "exchanges.yaml"))


def load_risk_config() -> Dict[str, Any]:
    return _read_yaml(os.path.join(CONFIG_DIR, "risk.yaml"))


def load_logging_config() -> Dict[str, Any]:
    return _read_yaml(os.path.join(CONFIG_DIR, "logging.yaml"))
