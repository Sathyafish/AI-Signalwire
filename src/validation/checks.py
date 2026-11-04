import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional

import httpx

from src.models import BlogPost

SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def _valid_date(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        pass
    try:
        parsedate_to_datetime(value)
        return True
    except (TypeError, ValueError):
        return False


def _link_ok(url: str, client: httpx.Client) -> bool:
    try:
        resp = client.head(url, follow_redirects=True)
        if resp.status_code in (403, 405, 501):
            resp = client.get(url, follow_redirects=True)
        # 401/403/429 mean the site answered but blocks bots, so the link exists.
        return resp.status_code < 400 or resp.status_code in (401, 403, 429)
    except Exception:
        return False


def validate_post(post: BlogPost, check_links: bool = True, client: Optional[httpx.Client] = None) -> list[str]:
    errors = []
    for field in ("title", "excerpt", "source_name"):
        if not getattr(post, field).strip():
            errors.append(f"{field} is empty")
    if not post.body_markdown.strip():
        errors.append("body_markdown is empty")
    if not SLUG.match(post.slug):
        errors.append(f"slug {post.slug!r} must be lowercase letters, digits and hyphens")
    if not post.topics:
        errors.append("topics must have at least one entry")
    if not post.source_url.lower().startswith(("http://", "https://")):
        errors.append("source_url must start with http:// or https://")
    elif check_links:
        client = client or httpx.Client(timeout=10, headers={"User-Agent": "AI-Signalwire-demo"})
        if not _link_ok(post.source_url, client):
            errors.append(f"source link does not respond: {post.source_url}")
    if not _valid_date(post.source_published_at):
        errors.append(f"source_published_at {post.source_published_at!r} is not a valid date")
    return errors
