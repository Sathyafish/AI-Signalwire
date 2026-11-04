from src.publishing.local_blog import publish
from src.storage.db import Database


def pending_review(db: Database) -> list[dict]:
    return db.list_articles("pending_review")


def needs_attention(db: Database) -> list[dict]:
    return [r for s in ("needs_review", "evaluation_failed", "failed") for r in db.list_articles(s)]


def approve(db: Database, article_id: int) -> None:
    status = db.get(article_id)["status"]
    if status != "pending_review":
        raise ValueError(f"article {article_id} is {status}, not pending_review")
    db.update(article_id, status="approved")
    publish(db, article_id)


def reject(db: Database, article_id: int, reason: str = "") -> None:
    db.update(article_id, status="needs_review", error=reason)
