from typing import Literal

from pydantic import BaseModel, Field

STATUSES = (
    "discovered",
    "extracted",
    "duplicate",
    "rejected_non_ai",
    "needs_review",
    "summarized",
    "formatted",
    "evaluation_failed",
    "pending_review",
    "approved",
    "published",
    "failed",
)


class ArticleRecord(BaseModel):
    source_name: str
    source_type: Literal["lab_post", "release"]
    title: str
    canonical_url: str
    published_at: str
    body: str
    fingerprint: str = ""


class Relevance(BaseModel):
    label: Literal["ai", "not_ai", "ambiguous"] = Field(description="Is the article substantially about AI?")
    score: float = Field(description="Confidence from 0 to 1")
    evidence: str = Field(description="Short quotes or facts from the article supporting the label")


class BlogPost(BaseModel):
    title: str
    slug: str
    excerpt: str
    body_markdown: str
    topics: list[str]
    source_name: str
    source_url: str
    source_published_at: str
    status: str = "pending_review"


class Evaluation(BaseModel):
    verdict: Literal["pass", "reject_non_ai", "needs_review"]
    reason: str
    evidence: str
