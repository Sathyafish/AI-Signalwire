from src.discovery.dedupe import record_fingerprint
from src.models import ArticleRecord


def _item(source, type_, title, slug, body, date):
    return ArticleRecord(source_name=source, source_type=type_, title=title,
                         canonical_url=f"https://demo.example.com/{slug}", published_at=date, body=body,
                         fingerprint=record_fingerprint(title, body))


def canned_items() -> list[ArticleRecord]:
    ai_body = (
        "The lab announced a new large language model with stronger reasoning and tool use. "
        "The AI model scores higher on coding and math benchmarks and supports longer context. "
        "It is available through the API today, along with updated safety evaluations. "
    ) * 3
    agents_body = (
        "A new agent framework update adds durable execution and better tracing for AI agents. "
        "Developers can now pause, resume and inspect multi-step LLM workflows in production. "
        "The release also improves model provider integrations and structured output support. "
    ) * 3
    release_body = (
        "v1.2.0\n\n- Add streaming support for agent graphs\n- Fix checkpoint serialization for LLM state\n"
        "- Improve type hints for tools used by AI agents\n- Drop support for Python 3.9 in this release line\n"
    ) * 3
    recipe_body = (
        "This weekend's pasta dish needs only five ingredients and twenty minutes. "
        "Boil the noodles, toast the garlic in olive oil, and finish with parmesan and lemon zest. "
        "Serve warm with a green salad and a glass of sparkling water. "
    ) * 3
    return [
        _item("Demo Lab", "lab_post", "Demo Lab introduces a new reasoning model", "new-model", ai_body, "2026-06-01T10:00:00Z"),
        _item("Demo Lab", "lab_post", "Agent framework adds durable execution", "agent-update", agents_body, "2026-06-02T10:00:00Z"),
        _item("DemoGraph", "release", "DemoGraph v1.2.0", "demograph-1-2-0", release_body, "2026-06-03T10:00:00Z"),
        _item("Demo Kitchen", "lab_post", "Five-ingredient weeknight pasta", "pasta", recipe_body, "2026-06-04T10:00:00Z"),
        _item("Demo Lab", "lab_post", "Short announcement with no text", "empty", "", "2026-06-05T10:00:00Z"),
    ]
