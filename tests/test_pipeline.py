import pytest

import src.pipeline as pl
from src.config import Settings
from src.fake_llm import FakeLLM
from src.models import BlogPost, Evaluation
from src.pipeline import run_pipeline
from src.storage.db import Database


def settings():
    return Settings(provider="openai", agent_model="m", evaluator_model="m", items_per_source=3,
                    demo_mode=True, fake_llm=True, db_path=":memory:")


class FailOn(FakeLLM):
    def __init__(self, schema):
        super().__init__()
        self.schema = schema

    def with_structured_output(self, schema):
        if schema is self.schema:
            raise RuntimeError("schema failure")
        return super().with_structured_output(schema)


@pytest.fixture
def db():
    return Database(":memory:")


def run(db, llm=None, eval_llm=None):
    return run_pipeline(db, settings(), [], llm or FakeLLM(), eval_llm or FakeLLM(), check_links=False)


def by_title(db):
    return {r["title"]: r["status"] for r in db.list_articles()}


def test_demo_run_routes_each_canned_item(db):
    result = run(db)
    s = by_title(db)
    assert result["new"] == 5 and result["duplicates"] == 0 and len(result["article_ids"]) == 5
    assert s["Demo Lab introduces a new reasoning model"] == "pending_review"
    assert s["Agent framework adds durable execution"] == "pending_review"
    assert s["DemoGraph v1.2.0"] == "pending_review"
    assert s["Five-ingredient weeknight pasta"] == "rejected_non_ai"
    assert s["Short announcement with no text"] == "needs_review"
    ev = db.get(db.list_articles("pending_review")[0]["id"])
    assert ev["relevance"]["label"] == "ai" and ev["post"]["title"] and ev["evaluation"]["verdict"] == "pass"
    assert ev["validation"] == []


def test_empty_body_makes_no_llm_calls(db):
    llm = FakeLLM()
    run(db, llm=llm)
    assert not any("Title: Short announcement" in c for c in llm.calls)


def test_rerun_creates_no_duplicates(db):
    run(db)
    before = by_title(db)
    again = run(db)
    assert again["new"] == 0 and again["duplicates"] == 5 and again["article_ids"] == []
    assert by_title(db) == before and len(db.list_articles()) == 5


def test_writer_failure_goes_to_needs_review(db):
    run(db, llm=FailOn(BlogPost))
    assert by_title(db)["DemoGraph v1.2.0"] == "needs_review"
    assert "schema failure" in db.list_articles("needs_review")[0]["error"]


def test_validation_failure_goes_to_needs_review(db, monkeypatch):
    monkeypatch.setattr(pl, "validate_post", lambda post, check_links=True: ["bad slug"])
    run(db)
    row = [r for r in db.list_articles() if r["title"] == "DemoGraph v1.2.0"][0]
    assert row["status"] == "needs_review" and row["validation"] == ["bad slug"]


def test_evaluator_verdicts_route(db, monkeypatch):
    verdicts = iter(["needs_review", "reject_non_ai", "pass"])
    monkeypatch.setattr(pl, "evaluate", lambda *a, **k: Evaluation(verdict=next(verdicts), reason="r", evidence="e"))
    run(db)
    statuses = sorted(r["status"] for r in db.list_articles() if r["evaluation"])
    assert statuses == ["needs_review", "pending_review", "rejected_non_ai"]


def test_unexpected_exception_marks_failed_and_continues(db, monkeypatch):
    real = pl.classify
    calls = {"n": 0}

    def flaky(llm, record):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("kaboom")
        return real(llm, record)

    monkeypatch.setattr(pl, "classify", flaky)
    run(db)
    failed = db.list_articles("failed")
    assert len(failed) == 1 and "kaboom" in failed[0]["error"] and failed[0]["attempts"] == 1
    assert len(db.list_articles("pending_review")) >= 2


def test_source_errors_reported(db, monkeypatch):
    monkeypatch.setattr(pl, "discover", lambda sources, settings: ([], {"X": "boom"}))
    result = run(db)
    assert result["source_errors"] == {"X": "boom"} and result["new"] == 0


def test_resumes_formatted_article_without_rewriting(db):
    run(db, llm=FailOn(BlogPost))  # all AI items stop at needs_review after writer fails
    # a formatted-but-unfinished article is picked up on the next run
    aid = db.list_articles("needs_review")[0]["id"]
    db.update(aid, status="formatted", post=BlogPost(title="t", slug="t", excerpt="e", body_markdown="b",
              topics=["ai"], source_name="S", source_url="https://e.com", source_published_at="2026-01-01"),
              relevance={"label": "ai", "score": 0.9, "evidence": "x"})
    llm = FakeLLM()
    result = run(db, llm=llm)
    assert aid in result["article_ids"] and db.get(aid)["status"] == "pending_review"
    assert db.get(aid)["post"]["title"] == "t"  # stored draft kept, writer not called again
