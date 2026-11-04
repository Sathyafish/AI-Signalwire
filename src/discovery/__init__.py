from src.config import Settings, Source
from src.discovery.demo import canned_items
from src.discovery.feeds import fetch_feed_items
from src.discovery.html_adapter import fetch_html_items
from src.models import ArticleRecord


def discover(sources: list[Source], settings: Settings) -> tuple[list[ArticleRecord], dict[str, str]]:
    """Collect items from every source. A failing source is recorded in the error map; the rest still run."""
    if settings.demo_mode:
        return canned_items(), {}
    records: list[ArticleRecord] = []
    errors: dict[str, str] = {}
    for source in sources:
        try:
            fetch = fetch_html_items if source.adapter == "html" else fetch_feed_items
            records.extend(fetch(source, settings.items_per_source))
        except Exception as exc:
            errors[source.name] = f"{type(exc).__name__}: {exc}"
    return records, errors
