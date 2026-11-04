from src.agents.common import AgentError, invoke_structured, wrap_untrusted
from src.models import ArticleRecord, BlogPost, Evaluation, Relevance

SYSTEM = (
    "You are an independent evaluator. You did not write the draft or make the relevance decision. Read the "
    "original source and answer:\n"
    "1. Is the article substantially about AI, rather than merely mentioning AI in passing?\n"
    "2. Does the evidence cited by the relevance agent support its decision?\n"
    "3. Is the summary faithful to the source, with no invented claims or misleading omissions?\n"
    "4. Does the post keep a working source link, attribution, and publication date?\n"
    "Return verdict 'pass' only if all four are yes; 'reject_non_ai' if the article is not substantially about "
    "AI; otherwise 'needs_review'. Give a reason and supporting evidence."
)


def evaluate(llm, record: ArticleRecord, relevance: Relevance, post: BlogPost) -> Evaluation:
    user = (
        f"Title: {record.title}\nPublisher: {record.source_name}\n\n{wrap_untrusted(record.body)}\n\n"
        f"Relevance decision: {relevance.label} (score {relevance.score})\nRelevance evidence: {relevance.evidence}\n\n"
        f"Draft headline: {post.title}\nDraft excerpt: {post.excerpt}\nDraft body:\n{post.body_markdown}\n"
        f"Source link: {post.source_url}\nAttribution: {post.source_name}\nPublished: {post.source_published_at}"
    )
    try:
        return invoke_structured(llm, Evaluation, SYSTEM, user)
    except AgentError as exc:
        return Evaluation(verdict="needs_review", reason=f"Evaluation failed: {exc}", evidence="")
