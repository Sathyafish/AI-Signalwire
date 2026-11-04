import re

from src.agents.common import invoke_structured, wrap_untrusted
from src.models import ArticleRecord, BlogPost

NEWS_SYSTEM = (
    "You write an original, concise blog summary of a news article, grounded only in the source. Preserve key "
    "facts and attribution. Do not reproduce the article, invent details, or add commentary. Return a headline, "
    "slug, one or two sentence excerpt, a markdown body, and topic tags."
)

RELEASE_SYSTEM = (
    "You write short release notes for a software release, grounded only in the source: the version, the key "
    "changes as a short list, and what it means for developers. Do not invent changes. Return a headline, slug, "
    "one or two sentence excerpt, a markdown body, and topic tags."
)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "post"


def write_post(llm, record: ArticleRecord) -> BlogPost:
    system = RELEASE_SYSTEM if record.source_type == "release" else NEWS_SYSTEM
    user = (f"Title: {record.title}\nPublisher: {record.source_name}\nURL: {record.canonical_url}\n"
            f"Published: {record.published_at}\n\n{wrap_untrusted(record.body)}")
    post = invoke_structured(llm, BlogPost, system, user)
    return post.model_copy(update={
        "slug": slugify(post.title),
        "source_name": record.source_name,
        "source_url": record.canonical_url,
        "source_published_at": record.published_at,
        "status": "pending_review",
    })
