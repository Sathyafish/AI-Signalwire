import re

from src.models import BlogPost, Evaluation, Relevance

_AI_WORDS = re.compile(r"\b(ai|model|models|llm|llms|agent|agents)\b", re.I)


def _parts(messages) -> list[tuple[str, str]]:
    if isinstance(messages, str):
        return [("human", messages)]
    out = []
    for m in messages:
        if isinstance(m, tuple):
            out.append((m[0], m[1]))
        else:
            out.append((getattr(m, "type", "human"), getattr(m, "content", str(m))))
    return out


def _text(messages) -> str:
    return "\n".join(content for _, content in _parts(messages))


def _human(messages) -> str:
    return "\n".join(content for role, content in _parts(messages) if role in ("human", "user"))


class _Chain:
    def __init__(self, llm: "FakeLLM", schema):
        self.llm, self.schema = llm, schema

    def invoke(self, messages):
        self.llm.calls.append(_text(messages))
        if self.llm.failures_left > 0:
            self.llm.failures_left -= 1
            raise RuntimeError("fake llm failure")
        text = _text(messages)
        if self.schema is Relevance:
            is_ai = bool(_AI_WORDS.search(_human(messages)))
            return Relevance(
                label="ai" if is_ai else "not_ai",
                score=0.9 if is_ai else 0.1,
                evidence="Mentions AI terms." if is_ai else "No AI content found.",
            )
        if self.schema is Evaluation:
            if "NEEDS_REVIEW_MARKER" in text:
                return Evaluation(verdict="needs_review", reason="Marker found", evidence="NEEDS_REVIEW_MARKER")
            return Evaluation(verdict="pass", reason="Draft matches source", evidence="Fake evaluator")
        if self.schema is BlogPost:
            title = (re.search(r"^Title: (.*)$", text, re.M) or [None, "Untitled"])[1]
            url = (re.search(r"^URL: (.*)$", text, re.M) or [None, "https://example.com"])[1]
            return BlogPost(
                title=title,
                slug="x",
                excerpt=f"Summary of {title}.",
                body_markdown=f"A short original summary of {title}.",
                topics=["ai"],
                source_name="x",
                source_url=url,
                source_published_at="2026-01-01T00:00:00Z",
            )
        raise ValueError(f"unsupported schema {self.schema}")


class FakeLLM:
    """Offline stand-in for a chat model. Raises for the first `fail_times` calls."""

    def __init__(self, fail_times: int = 0):
        self.failures_left = fail_times
        self.calls: list[str] = []

    def with_structured_output(self, schema):
        return _Chain(self, schema)
