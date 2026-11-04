import httpx
import pytest

from src.config import Settings, Source
from src.discovery import discover
from src.discovery.demo import canned_items
from src.discovery.dedupe import canonicalize, fingerprint
from src.discovery.feeds import fetch_feed_items
from src.discovery.html_adapter import fetch_html_items

FEED = open("tests/fixtures/sample_feed.xml").read()
INDEX = open("tests/fixtures/sample_news_index.html").read()
LONG_TEXT = "Long article text about AI. " * 40


def settings(demo=False):
    return Settings(provider="openai", agent_model="m", evaluator_model="m", items_per_source=2,
                    demo_mode=demo, fake_llm=True, db_path=":memory:")


def src(adapter="feed", name="S", type="lab_post", url="https://example.com/feed"):
    return Source(name=name, type=type, url=url, adapter=adapter)


def test_canonicalize_strips_utm_and_fragment():
    assert canonicalize("https://Example.com/a/?utm_source=x&id=1#frag") == "https://example.com/a?id=1"


def test_fingerprint_ignores_whitespace_and_case():
    assert fingerprint("Hello   World\n") == fingerprint("hello world")
    assert fingerprint("a") != fingerprint("b")


def test_fetch_feed_items_respects_limit():
    items = fetch_feed_items(src(), 2, parse=lambda url: __import__("feedparser").parse(FEED), extract=lambda url: "")
    assert len(items) == 2
    assert items[0].canonical_url == "https://example.com/one"
    assert items[0].source_type == "lab_post" and items[0].fingerprint


def test_fetch_feed_items_malformed_raises():
    with pytest.raises(RuntimeError):
        fetch_feed_items(src(), 3, parse=lambda url: __import__("feedparser").parse("<<not xml"), extract=lambda url: "")


def test_discover_records_malformed_feed_as_source_error():
    import src.discovery as d

    real = d.fetch_feed_items
    d.fetch_feed_items = lambda source, limit: real(source, limit, parse=lambda url: __import__("feedparser").parse("<<not xml"))
    try:
        records, errors = discover([src(name="Broken")], settings())
    finally:
        d.fetch_feed_items = real
    assert records == [] and "Broken" in errors


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/robots.txt":
        return httpx.Response(200, text="User-agent: *\nAllow: /\n")
    if path == "/news":
        return httpx.Response(200, text=INDEX)
    return httpx.Response(200, text=f"<html><head><title>T {path}</title></head><body><article><p>{LONG_TEXT}</p></article></body></html>")


def test_fetch_html_items_collects_links(monkeypatch):
    monkeypatch.setattr("src.discovery.html_adapter.time.sleep", lambda s: None)
    client = httpx.Client(transport=httpx.MockTransport(_handler))
    items = fetch_html_items(src("html", url="https://example.com/news"), 2, client=client)
    assert [i.canonical_url for i in items] == ["https://example.com/news/first-post", "https://example.com/news/second-post"]
    assert all(i.body for i in items)


def test_fetch_html_items_respects_robots(monkeypatch):
    monkeypatch.setattr("src.discovery.html_adapter.time.sleep", lambda s: None)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        return _handler(request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fetch_html_items(src("html", url="https://example.com/news"), 2, client=client) == []


def test_discover_records_failing_source_and_continues(monkeypatch):
    import src.discovery as d

    def fake_feed(source, limit, **kw):
        if source.name == "Bad":
            raise RuntimeError("boom")
        return canned_items()[:1]

    monkeypatch.setattr(d, "fetch_feed_items", fake_feed)
    records, errors = discover([src(name="Bad"), src(name="Good")], settings())
    assert len(records) == 1 and "Bad" in errors and "boom" in errors["Bad"]


def test_discover_demo_mode_returns_canned():
    records, errors = discover([src()], settings(demo=True))
    assert len(records) == 5 and errors == {}


def test_canned_items_mix():
    items = canned_items()
    assert any(i.source_type == "release" for i in items)
    assert any(not i.body.strip() for i in items)
    assert len({i.canonical_url for i in items}) == 5 and len({i.fingerprint for i in items}) == 5
