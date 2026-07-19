"""Local, user-owned context store (SQLite).

The whole point of uctx is that this file lives on *your* machine, not a
vendor's cloud. Default location: ~/.uctx/context.db (override with $UCTX_DB).

v0 keeps the schema deliberately small. `source_app` and `created_at` are the
seed of "provenance" so that trust/versioning can be layered on later without a
migration. Access control, multi-user, signing, and temporal versioning are
intentionally NOT here yet — see the roadmap in README.md.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def save(content: str, type: str = "note", tags: list[str] | None = None,
         source_app: str = "unknown") -> int:
    """Insert one context item; returns its id."""
    if not content or not content.strip():
        raise ValueError("content must not be empty")
    tag_str = " ".join(t.strip() for t in (tags or []) if t.strip())
    created = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO context (type, content, tags, source_app, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (type, content.strip(), tag_str, source_app, created),
        )
        return int(cur.lastrowid)


def search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Keyword search over content + tags (most recent first)."""
    like = f"%{query.strip()}%"
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM context WHERE content LIKE ? OR tags LIKE ? "
            "ORDER BY id DESC LIMIT ?",
            (like, like, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def update(item_id: int, content: str | None = None, type: str | None = None,
           tags: list[str] | None = None) -> bool:
    """Update one item's content/type/tags (only the fields you pass). Returns True if a row changed."""
    sets: list[str] = []
    vals: list[Any] = []
    if content is not None:
        if not content.strip():
            raise ValueError("content must not be empty")
        sets.append("content = ?")
        vals.append(content.strip())
    if type is not None:
        sets.append("type = ?")
        vals.append(type)
    if tags is not None:
        sets.append("tags = ?")
        vals.append(" ".join(t.strip() for t in tags if t.strip()))
    if not sets:
        return False
    vals.append(item_id)
    with _conn() as conn:
        cur = conn.execute(f"UPDATE context SET {', '.join(sets)} WHERE id = ?", vals)
        return cur.rowcount > 0


def list_all(limit: int = 50) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM context ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def forget(item_id: int) -> bool:
    """Delete one item by id; returns True if a row was removed."""
    with _conn() as conn:
        cur = conn.execute("DELETE FROM context WHERE id = ?", (item_id,))
        return cur.rowcount > 0
