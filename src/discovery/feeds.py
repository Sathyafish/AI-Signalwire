from datetime import datetime, timezone
from typing import Callable

import feedparser
from bs4 import BeautifulSoup

from src.config import Source
from src.discovery.dedupe import canonicalize, record_fingerprint
from src.discovery.extract import extract_text
from src.models import ArticleRecord

SHORT_BODY = 500


def _plain(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def fetch_feed_items(source: Source, limit: int, parse: Callable = feedparser.parse,
                     extract: Callable = extract_text) -> list[ArticleRecord]:
    """Read an RSS/Atom feed. Raises if the feed is unreachable or malformed, so discover() records the error."""
    feed = parse(source.url)
    if feed.get("bozo") and not feed.entries:
        raise RuntimeError(f"feed unreachable or malformed: {feed.get('bozo_exception')}")
    items = []
    for entry in feed.entries[:limit]:
        link = entry.get("link")
        if not link:
            continue
        raw = entry.content[0].value if entry.get("content") else entry.get("summary", "")
        body = _plain(raw)
        if source.type == "lab_post" and len(body) < SHORT_BODY:
            body = extract(link) or body
        published = entry.get("published") or entry.get("updated") or datetime.now(timezone.utc).isoformat()
        title = entry.get("title", "Untitled")
        items.append(ArticleRecord(source_name=source.name, source_type=source.type, title=title,
                                   canonical_url=canonicalize(link), published_at=published, body=body,
                                   fingerprint=record_fingerprint(title, body)))
    return items
