from __future__ import annotations
import os
from urllib.parse import urlparse

CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..", "configs"))
ALLOW_PATH = os.path.join(CONFIG_DIR, "allowlist_domains.txt")

with open(ALLOW_PATH, 'r', encoding='utf-8') as f:
    ALLOW = set(x.strip().lower() for x in f if x.strip() and not x.startswith('#'))

def allowed(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
        return host.lower() in ALLOW
    except Exception:
        return False
