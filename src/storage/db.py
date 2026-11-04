import json
import os
import sqlite3
from typing import Optional

from pydantic import BaseModel

from src.models import STATUSES, ArticleRecord

JSON_FIELDS = ("relevance", "post", "validation", "evaluation")

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT, source_type TEXT, title TEXT,
    canonical_url TEXT UNIQUE, published_at TEXT, body TEXT,
    fingerprint TEXT UNIQUE,
    status TEXT DEFAULT 'discovered',
    relevance TEXT, post TEXT, validation TEXT, evaluation TEXT,
    attempts INTEGER DEFAULT 0, error TEXT,
    post_url TEXT, published_time TEXT
)
"""


class Database:
    def __init__(self, path: str):
        if path != ":memory:":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def add_article(self, rec: ArticleRecord) -> Optional[int]:
        if self.exists(rec.canonical_url, rec.fingerprint):
            return None
        cur = self.conn.execute(
            "INSERT INTO articles (source_name, source_type, title, canonical_url, published_at, body, fingerprint)"
            " VALUES (?,?,?,?,?,?,?)",
            (rec.source_name, rec.source_type, rec.title, rec.canonical_url, rec.published_at, rec.body, rec.fingerprint),
        )
        self.conn.commit()
        return cur.lastrowid

    def exists(self, canonical_url: str, fingerprint: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM articles WHERE canonical_url=? OR fingerprint=?", (canonical_url, fingerprint)
        ).fetchone()
        return row is not None

    def get(self, article_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM articles WHERE id=?", (article_id,)).fetchone()
        if row is None:
            raise KeyError(article_id)
        return self._decode(row)

    def list_articles(self, status: Optional[str] = None) -> list[dict]:
        if status:
            rows = self.conn.execute("SELECT * FROM articles WHERE status=? ORDER BY id", (status,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM articles ORDER BY id").fetchall()
        return [self._decode(r) for r in rows]

    def update(self, article_id: int, **fields) -> None:
        if "status" in fields and fields["status"] not in STATUSES:
            raise ValueError(f"unknown status {fields['status']!r}")
        values = []
        for key, val in fields.items():
            if isinstance(val, BaseModel):
                val = val.model_dump()
            if key in JSON_FIELDS or isinstance(val, (dict, list)):
                val = json.dumps(val)
            values.append(val)
        sets = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE articles SET {sets} WHERE id=?", (*values, article_id))
        self.conn.commit()

    def reset(self) -> None:
        self.conn.execute("DELETE FROM articles")
        self.conn.commit()

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict:
        d = dict(row)
        for f in JSON_FIELDS:
            d[f] = json.loads(d[f]) if d[f] is not None else None
        return d
