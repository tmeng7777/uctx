"""Local, user-owned context store (SQLite).

The whole point of uctx is that this file lives on *your* machine, not a
vendor's cloud. Default location: ~/.uctx/context.db (override with $UCTX_DB).

The `embedding` column (JSON list, nullable) supports semantic search when an
embedder is configured; it stays NULL in the default keyword mode. `source_app`
and `created_at` are the seed of "provenance" for later trust/versioning work.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .embeddings import cosine


def _db_path() -> Path:
    return Path(os.environ.get("UCTX_DB", Path.home() / ".uctx" / "context.db"))


def _conn() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS context (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            type       TEXT NOT NULL DEFAULT 'note',
            content    TEXT NOT NULL,
            tags       TEXT NOT NULL DEFAULT '',
            source_app TEXT NOT NULL DEFAULT 'unknown',
            created_at TEXT NOT NULL,
            embedding  TEXT
        )
        """
    )
    # Migrate DBs created before the embedding column existed.
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(context)")}
    if "embedding" not in cols:
        conn.execute("ALTER TABLE context ADD COLUMN embedding TEXT")
    return conn


def save(content: str, type: str = "note", tags: list[str] | None = None,
         source_app: str = "unknown", embedding: list[float] | None = None) -> int:
    if not content or not content.strip():
        raise ValueError("content must not be empty")
    tag_str = " ".join(t.strip() for t in (tags or []) if t.strip())
    created = datetime.now(timezone.utc).isoformat()
    emb_json = json.dumps(embedding) if embedding is not None else None
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO context (type, content, tags, source_app, created_at, embedding) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (type, content.strip(), tag_str, source_app, created, emb_json),
        )
        return int(cur.lastrowid)


def _clean(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item.pop("embedding", None)  # don't leak raw vectors to callers
    return item


def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Keyword (substring) search over content + tags, most recent first."""
    like = f"%{query.strip()}%"
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM context WHERE content LIKE ? OR tags LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (like, like, limit),
        ).fetchall()
    return [_clean(r) for r in rows]


def semantic_search(query_vec: list[float], limit: int = 10) -> list[dict[str, Any]]:
    """Rank items by cosine similarity to query_vec. Items with no stored
    embedding are skipped. Each result carries a 'score' in [0, 1]."""
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM context WHERE embedding IS NOT NULL").fetchall()
    scored = []
    for row in rows:
        vec = json.loads(row["embedding"])
        item = _clean(row)
        item["score"] = round(cosine(query_vec, vec), 4)
        scored.append(item)
    scored.sort(key=lambda i: i["score"], reverse=True)
    return scored[:limit]


def list_all(limit: int = 50) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM context ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_clean(r) for r in rows]


def forget(item_id: int) -> bool:
    with _conn() as conn:
        cur = conn.execute("DELETE FROM context WHERE id = ?", (item_id,))
        return cur.rowcount > 0
