from typing import Optional

import httpx
import trafilatura


def extract_text(url: str, client: Optional[httpx.Client] = None) -> str:
    """Fetch a page and return its main text, or an empty string on any failure."""
    try:
        client = client or httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": "AI-Signalwire-demo"})
        resp = client.get(url)
        resp.raise_for_status()
        return trafilatura.extract(resp.text) or ""
    except Exception:
        return ""
