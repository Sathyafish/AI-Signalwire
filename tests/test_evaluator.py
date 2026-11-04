from src.evaluation.evaluator import evaluate
from src.fake_llm import FakeLLM
from src.models import ArticleRecord, BlogPost, Relevance

REC = ArticleRecord(source_name="Lab", source_type="lab_post", title="AI news", canonical_url="https://e.com/a",
                    published_at="2026-01-01T00:00:00Z", body="Source text about a new AI model.", fingerprint="f")
REL = Relevance(label="ai", score=0.9, evidence="mentions AI model")
POST = BlogPost(title="AI news", slug="ai-news", excerpt="e", body_markdown="Summary.", topics=["ai"],
                source_name="Lab", source_url="https://e.com/a", source_published_at="2026-01-01T00:00:00Z")


def test_evaluate_pass():
    assert evaluate(FakeLLM(), REC, REL, POST).verdict == "pass"


def test_evaluate_marker_needs_review():
    rec = REC.model_copy(update={"body": "NEEDS_REVIEW_MARKER"})
    assert evaluate(FakeLLM(), rec, REL, POST).verdict == "needs_review"


def test_evaluate_llm_failure_is_needs_review():
    out = evaluate(FakeLLM(fail_times=2), REC, REL, POST)
    assert out.verdict == "needs_review" and "fake llm failure" in out.reason


def test_evaluator_prompt_includes_four_questions_and_inputs():
    llm = FakeLLM()
    evaluate(llm, REC, REL, POST)
    prompt = llm.calls[0].lower()
    assert "substantially about ai" in prompt and "evidence" in prompt and "faithful" in prompt
    assert "source link" in prompt and "<article>" in prompt and "mentions ai model" in prompt and "summary." in prompt
