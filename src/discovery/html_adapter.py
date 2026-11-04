import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from src.config import Source
from src.discovery.dedupe import canonicalize, record_fingerprint
from src.discovery.extract import extract_text
from src.models import ArticleRecord

USER_AGENT = "AI-Signalwire-demo"


def _allowed(client: httpx.Client, url: str) -> bool:
    parts = urlsplit(url)
    parser = RobotFileParser()
    try:
        resp = client.get(f"{parts.scheme}://{parts.netloc}/robots.txt")
        parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
    except Exception:
        return True
    return parser.can_fetch(USER_AGENT, url)


def fetch_html_items(source: Source, limit: int, client: Optional[httpx.Client] = None) -> list[ArticleRecord]:
    """Read a news index page that has no feed: collect same-site article links, then extract each."""
    client = client or httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    if not _allowed(client, source.url):
        return []
    index = client.get(source.url)
    index.raise_for_status()
    base = urlsplit(source.url)
    prefix = base.path.rstrip("/") + "/"
    seen, links = set(), []
    for a in BeautifulSoup(index.text, "html.parser").find_all("a", href=True):
        url = canonicalize(urljoin(source.url, a["href"]))
        parts = urlsplit(url)
        if parts.netloc == base.netloc and parts.path.startswith(prefix) and url not in seen:
            seen.add(url)
            links.append((url, a.get_text(" ", strip=True)))
    items = []
    for i, (url, text) in enumerate(links[:limit]):
        if i:
            time.sleep(1)
        if not _allowed(client, url):
            continue
        body = extract_text(url, client)
        title = text or url
        items.append(ArticleRecord(source_name=source.name, source_type=source.type, title=title,
                                   canonical_url=url, published_at=datetime.now(timezone.utc).isoformat(),
                                   body=body, fingerprint=record_fingerprint(title, body)))
    return items
