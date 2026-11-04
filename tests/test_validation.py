import httpx

from src.models import BlogPost
from src.validation.checks import validate_post


def post(**kw):
    base = dict(title="T", slug="t-1", excerpt="e", body_markdown="b", topics=["ai"], source_name="Lab",
                source_url="https://e.com/a", source_published_at="2026-01-01T00:00:00Z")
    base.update(kw)
    return BlogPost(**base)


def client(status=200):
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status)))


def test_valid_post_has_no_errors():
    assert validate_post(post(), client=client()) == []


def test_missing_source_url_flagged():
    errs = validate_post(post(source_url=""), check_links=False)
    assert any("source_url" in e for e in errs)


def test_bad_slug_flagged():
    assert any("slug" in e for e in validate_post(post(slug="Bad Slug!"), check_links=False))


def test_bad_date_flagged():
    assert any("source_published_at" in e for e in validate_post(post(source_published_at="yesterday"), check_links=False))


def test_rfc2822_date_accepted():
    assert validate_post(post(source_published_at="Mon, 01 Jun 2026 10:00:00 GMT"), check_links=False) == []


def test_dead_link_flagged():
    assert any("link" in e.lower() for e in validate_post(post(), client=client(404)))


def test_head_not_allowed_falls_back_to_get():
    def handler(request):
        return httpx.Response(405 if request.method == "HEAD" else 200)

    c = httpx.Client(transport=httpx.MockTransport(handler))
    assert validate_post(post(), client=c) == []


def test_check_links_false_skips_network():
    def boom(request):
        raise AssertionError("network used")

    c = httpx.Client(transport=httpx.MockTransport(boom))
    assert validate_post(post(), check_links=False, client=c) == []


def test_missing_topics_and_empty_fields_flagged():
    errs = validate_post(post(title="", topics=[], body_markdown=" "), check_links=False)
    assert any("title" in e for e in errs) and any("topics" in e for e in errs) and any("body" in e for e in errs)


def test_bot_blocked_link_counts_as_reachable():
    assert validate_post(post(), client=client(403)) == []
    assert validate_post(post(), client=client(429)) == []
