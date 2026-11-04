from src.agents.common import AgentError, invoke_structured, wrap_untrusted
from src.models import ArticleRecord, Relevance

MIN_BODY_CHARS = 100  # feed summaries are often ~120 characters; enough to judge relevance

SYSTEM = (
    "You decide whether an article is substantially about artificial intelligence, rather than merely "
    "mentioning AI in passing. Return label 'ai', 'not_ai', or 'ambiguous'; a score from 0 to 1; and evidence "
    "quoting or citing specific facts from the article."
)


def classify(llm, record: ArticleRecord) -> Relevance:
    if len(record.body.strip()) < MIN_BODY_CHARS:
        return Relevance(label="ambiguous", score=0.0, evidence="Article body too short to judge.")
    user = f"Title: {record.title}\nPublisher: {record.source_name}\n\n{wrap_untrusted(record.body)}"
    try:
        return invoke_structured(llm, Relevance, SYSTEM, user)
    except AgentError as exc:
        return Relevance(label="ambiguous", score=0.0, evidence=f"Relevance check failed: {exc}")
