from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src.agents.common import AgentError
from src.agents.relevance import classify
from src.agents.writer import write_post
from src.config import Settings, Source
from src.discovery import discover
from src.evaluation.evaluator import evaluate
from src.models import ArticleRecord, BlogPost, Evaluation, Relevance
from src.storage.db import Database
from src.validation.checks import validate_post

RESUMABLE = ("discovered", "formatted")


class State(TypedDict, total=False):
    article_id: int
    next: str


def _record(row: dict) -> ArticleRecord:
    return ArticleRecord(source_name=row["source_name"], source_type=row["source_type"], title=row["title"],
                         canonical_url=row["canonical_url"], published_at=row["published_at"], body=row["body"],
                         fingerprint=row["fingerprint"])


def build_graph(db: Database, llm, eval_llm, check_links: bool = True):
    """Per-article graph: relevance -> writer -> validation -> evaluator, with review routing on every failure."""

    def safe(node):
        def run(state: State) -> State:
            try:
                return node(state["article_id"])
            except Exception as exc:
                attempts = (db.get(state["article_id"])["attempts"] or 0) + 1
                db.update(state["article_id"], status="failed", error=f"{type(exc).__name__}: {exc}", attempts=attempts)
                return {"next": "end"}

        return run

    def route(state: State) -> str:
        return state.get("next", "end")

    def entry(state: State) -> State:
        status = db.get(state["article_id"])["status"]
        return {"next": {"discovered": "relevance", "formatted": "validation"}.get(status, "end")}

    @safe
    def relevance_node(aid: int) -> State:
        row = db.get(aid)
        rel = classify(llm, _record(row))
        db.update(aid, relevance=rel)
        if rel.label == "ai":
            return {"next": "writer"}
        db.update(aid, status="rejected_non_ai" if rel.label == "not_ai" else "needs_review",
                  error=None if rel.label == "not_ai" else rel.evidence)
        return {"next": "end"}

    @safe
    def writer_node(aid: int) -> State:
        try:
            post = write_post(llm, _record(db.get(aid)))
        except AgentError as exc:
            db.update(aid, status="needs_review", error=f"Writer failed: {exc}")
            return {"next": "end"}
        db.update(aid, post=post, status="formatted")
        return {"next": "validation"}

    @safe
    def validation_node(aid: int) -> State:
        post = BlogPost(**db.get(aid)["post"])
        errors = validate_post(post, check_links=check_links)
        db.update(aid, validation=errors)
        if errors:
            db.update(aid, status="needs_review", error="Validation failed: " + "; ".join(errors))
            return {"next": "end"}
        return {"next": "evaluator"}

    @safe
    def evaluator_node(aid: int) -> State:
        row = db.get(aid)
        ev = evaluate(eval_llm, _record(row), Relevance(**row["relevance"]), BlogPost(**row["post"]))
        status = {"pass": "pending_review", "reject_non_ai": "rejected_non_ai", "needs_review": "needs_review"}[ev.verdict]
        db.update(aid, evaluation=ev, status=status, error=None if ev.verdict == "pass" else ev.reason)
        return {"next": "end"}

    g = StateGraph(State)
    g.add_node("entry", entry)
    for name, fn in (("relevance", relevance_node), ("writer", writer_node),
                     ("validation", validation_node), ("evaluator", evaluator_node)):
        g.add_node(name, fn)
    targets = {"relevance": "relevance", "writer": "writer", "validation": "validation",
               "evaluator": "evaluator", "end": END}
    g.add_edge(START, "entry")
    for name in ("entry", "relevance", "writer", "validation", "evaluator"):
        g.add_conditional_edges(name, route, targets)
    return g.compile()


def run_pipeline(db: Database, settings: Settings, sources: list[Source], llm, eval_llm,
                 check_links: bool = True) -> dict:
    """Discover new items, store them, and run the graph on every new or resumable article."""
    records, source_errors = discover(sources, settings)
    new_ids, duplicates = [], 0
    for rec in records:
        aid = db.add_article(rec)
        if aid is None:
            duplicates += 1
        else:
            new_ids.append(aid)
    resumable = [r["id"] for status in RESUMABLE for r in db.list_articles(status)]
    ids = list(dict.fromkeys(new_ids + resumable))
    graph = build_graph(db, llm, eval_llm, check_links)
    for aid in ids:
        graph.invoke({"article_id": aid})
    return {"new": len(new_ids), "duplicates": duplicates, "source_errors": source_errors, "article_ids": ids}
