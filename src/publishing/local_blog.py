import html
from datetime import datetime, timezone

import markdown
from bs4 import BeautifulSoup

from src.models import BlogPost
from src.storage.db import Database


def publish(db: Database, article_id: int) -> str:
    row = db.get(article_id)
    if row["status"] == "published":
        return row["post_url"]
    url = f"local://blog/{BlogPost(**row['post']).slug}"
    db.update(article_id, status="published", post_url=url, published_time=datetime.now(timezone.utc).isoformat())
    return url


def _escape_html_tags(text: str) -> str:
    return html.escape(text, quote=False)


def _safe_links(rendered: str) -> str:
    """Drop href/src values that are not http(s), such as javascript: URLs written by the model."""
    soup = BeautifulSoup(rendered, "html.parser")
    for tag in soup.find_all(["a", "img"]):
        attr = "href" if tag.name == "a" else "src"
        if not str(tag.get(attr, "")).lower().startswith(("http://", "https://")):
            del tag[attr]
    return str(soup)


def render_blog_html(db: Database) -> str:
    rows = db.list_articles("published")
    if not rows:
        return "<p>No published posts yet.</p>"
    cards = []
    for row in rows:
        p = BlogPost(**row["post"])
        # Escape model-written markdown before converting, so raw HTML in it cannot run.
        body = _safe_links(markdown.markdown(_escape_html_tags(p.body_markdown)))
        cards.append(
            "<article style='border:1px solid #ddd;border-radius:8px;padding:12px 16px;margin:12px 0'>"
            f"<h3>{html.escape(p.title)}</h3>{body}"
            f"<p style='color:#555;font-size:0.9em'>Source: {html.escape(p.source_name)}, published "
            f"{html.escape(p.source_published_at)}. "
            f"<a href=\"{html.escape(p.source_url)}\">Read the original</a></p></article>"
        )
    return "".join(cards)
