import pytest

from src.models import ArticleRecord, BlogPost
from src.publishing.local_blog import publish, render_blog_html
from src.review.queue import approve, needs_attention, pending_review, reject
from src.storage.db import Database


def post(title="Hello", slug="hello"):
    return BlogPost(title=title, slug=slug, excerpt="e", body_markdown="Summary **bold**.", topics=["ai"],
                    source_name="Lab", source_url="https://e.com/a", source_published_at="2026-01-01T00:00:00Z")


@pytest.fixture
def db():
    d = Database(":memory:")
    d.add_article(ArticleRecord(source_name="Lab", source_type="lab_post", title="Hello", canonical_url="https://e.com/a",
                                published_at="2026-01-01T00:00:00Z", body="b", fingerprint="f"))
    return d


def make_pending(db, p=None):
    db.update(1, status="pending_review", post=p or post())


def test_approve_publishes_pending_item(db):
    make_pending(db)
    approve(db, 1)
    row = db.get(1)
    assert row["status"] == "published" and row["post_url"] == "local://blog/hello" and row["published_time"]


def test_approve_rejects_wrong_status(db):
    with pytest.raises(ValueError):
        approve(db, 1)


def test_reject_moves_to_needs_review(db):
    make_pending(db)
    reject(db, 1, "not good")
    row = db.get(1)
    assert row["status"] == "needs_review" and row["error"] == "not good"


def test_queues(db):
    make_pending(db)
    assert [r["id"] for r in pending_review(db)] == [1] and needs_attention(db) == []
    reject(db, 1)
    assert [r["id"] for r in needs_attention(db)] == [1] and pending_review(db) == []


def test_publish_is_idempotent(db):
    make_pending(db)
    url = publish(db, 1)
    t = db.get(1)["published_time"]
    assert publish(db, 1) == url and db.get(1)["published_time"] == t


def test_blog_html_has_source_link_and_attribution(db):
    make_pending(db)
    approve(db, 1)
    html = render_blog_html(db)
    assert 'href="https://e.com/a"' in html and "Lab" in html and "2026-01-01" in html and "<strong>bold</strong>" in html


def test_blog_html_escapes_markup_in_title(db):
    make_pending(db, post(title="<script>alert(1)</script>"))
    approve(db, 1)
    html = render_blog_html(db)
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_blog_html_empty_message():
    assert "No published posts" in render_blog_html(Database(":memory:"))


def test_blog_html_strips_javascript_links(db):
    p = post()
    p = p.model_copy(update={"body_markdown": "[click](javascript:alert(1)) and [ok](https://e.com/x) ![i](javascript:evil)"})
    make_pending(db, p)
    approve(db, 1)
    html = render_blog_html(db)
    assert "javascript:" not in html and 'href="https://e.com/x"' in html
