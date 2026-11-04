import pytest

from src.models import ArticleRecord, BlogPost
from src.storage.db import Database


def rec(url="https://e.com/a", fp="fp1", title="T"):
    return ArticleRecord(source_name="S", source_type="lab_post", title=title, canonical_url=url,
                         published_at="2026-01-01T00:00:00Z", body="body", fingerprint=fp)


@pytest.fixture
def db():
    return Database(":memory:")


def test_add_article_returns_id(db):
    aid = db.add_article(rec())
    assert isinstance(aid, int) and db.get(aid)["status"] == "discovered"


def test_duplicate_url_returns_none(db):
    db.add_article(rec())
    assert db.add_article(rec(fp="other")) is None


def test_duplicate_fingerprint_returns_none(db):
    db.add_article(rec())
    assert db.add_article(rec(url="https://e.com/b")) is None


def test_update_status_validates(db):
    aid = db.add_article(rec())
    with pytest.raises(ValueError):
        db.update(aid, status="bogus")
    db.update(aid, status="needs_review")
    assert db.get(aid)["status"] == "needs_review"


def test_update_json_roundtrip(db):
    aid = db.add_article(rec())
    post = BlogPost(title="t", slug="t", excerpt="e", body_markdown="b", topics=["a"],
                    source_name="S", source_url="https://e.com", source_published_at="2026-01-01")
    db.update(aid, post=post, validation=["err"], relevance={"label": "ai"})
    row = db.get(aid)
    assert row["post"]["title"] == "t" and row["validation"] == ["err"] and row["relevance"]["label"] == "ai"
    assert row["evaluation"] is None


def test_list_filters_by_status(db):
    a = db.add_article(rec())
    db.add_article(rec(url="https://e.com/b", fp="fp2"))
    db.update(a, status="published")
    assert [r["id"] for r in db.list_articles("published")] == [a]
    assert len(db.list_articles()) == 2


def test_exists(db):
    db.add_article(rec())
    assert db.exists("https://e.com/a", "zzz") and db.exists("https://nope", "fp1")
    assert not db.exists("https://nope", "zzz")


def test_reset_empties_table(db):
    db.add_article(rec())
    db.reset()
    assert db.list_articles() == []
