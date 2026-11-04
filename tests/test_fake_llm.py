import pytest

from src.fake_llm import FakeLLM
from src.models import BlogPost, Evaluation, Relevance


def test_relevance_ai_text_is_ai():
    out = FakeLLM().with_structured_output(Relevance).invoke("New AI model released")
    assert out.label == "ai"


def test_relevance_cooking_text_is_not_ai():
    out = FakeLLM().with_structured_output(Relevance).invoke("Best pasta recipe for dinner")
    assert out.label == "not_ai"


def test_fail_times_raises_then_succeeds():
    chain = FakeLLM(fail_times=1).with_structured_output(Relevance)
    with pytest.raises(RuntimeError):
        chain.invoke("AI news")
    assert chain.invoke("AI news").label == "ai"


def test_evaluation_marker_needs_review():
    chain = FakeLLM().with_structured_output(Evaluation)
    assert chain.invoke("fine").verdict == "pass"
    assert chain.invoke("NEEDS_REVIEW_MARKER").verdict == "needs_review"


def test_blogpost_filled_from_prompt():
    out = FakeLLM().with_structured_output(BlogPost).invoke("Title: Hello World\nURL: https://e.com/x")
    assert out.title == "Hello World" and out.source_url == "https://e.com/x"
