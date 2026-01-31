from __future__ import annotations
import requests
from bs4 import BeautifulSoup
from .allowlist import allowed

class FetchError(Exception):
    pass

def fetch_text(url: str) -> str:
    if not allowed(url):
        raise FetchError("domain not allowlisted")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator='\n')
    return '\n'.join(line.strip() for line in text.splitlines() if line.strip())
