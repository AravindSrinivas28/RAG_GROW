"""Phase 7: SQLite thread store (no PII columns; rag-architecture.md §8)."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS threads (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            citation_url TEXT,
            last_updated TEXT,
            footer_line TEXT,
            refusal INTEGER NOT NULL DEFAULT 0,
            abstain INTEGER NOT NULL DEFAULT 0,
            route TEXT,
            abstain_reason TEXT,
            model_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (thread_id) REFERENCES threads(id)
        );

        CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
        """
    )
    conn.commit()


@dataclass
class StoredMessage:
    id: int
    thread_id: str
    role: str
    content: str
    citation_url: str | None
    last_updated: str | None
    footer_line: str | None
    refusal: bool
    abstain: bool
    route: str | None
    abstain_reason: str | None
    model_id: str | None
    created_at: str


class ThreadStore:
    """Per-thread ordered messages."""

    def __init__(self, db_path: Path | str) -> None:
        self._path = Path(db_path)
        self._conn = _connect(self._path)
        init_schema(self._conn)

    def close(self) -> None:
        self._conn.close()

    def create_thread(self, thread_id: str | None = None) -> str:
        tid = thread_id or str(uuid.uuid4())
        now = _utc_now()
        self._conn.execute(
            "INSERT OR IGNORE INTO threads (id, created_at) VALUES (?, ?)",
            (tid, now),
        )
        self._conn.commit()
        return tid

    def has_thread(self, thread_id: str) -> bool:
        cur = self._conn.execute("SELECT 1 FROM threads WHERE id = ? LIMIT 1", (thread_id,))
        return cur.fetchone() is not None

    def append_message(
        self,
        thread_id: str,
        *,
        role: str,
        content: str,
        citation_url: str | None = None,
        last_updated: str | None = None,
        footer_line: str | None = None,
        refusal: bool = False,
        abstain: bool = False,
        route: str | None = None,
        abstain_reason: str | None = None,
        model_id: str | None = None,
    ) -> int:
        now = _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO messages (
                thread_id, role, content, citation_url, last_updated, footer_line,
                refusal, abstain, route, abstain_reason, model_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                thread_id,
                role,
                content,
                citation_url or "",
                last_updated or "",
                footer_line or "",
                1 if refusal else 0,
                1 if abstain else 0,
                route or "",
                abstain_reason or "",
                model_id or "",
                now,
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid or 0)

    def list_messages(self, thread_id: str) -> list[StoredMessage]:
        cur = self._conn.execute(
            """
            SELECT id, thread_id, role, content, citation_url, last_updated, footer_line,
                   refusal, abstain, route, abstain_reason, model_id, created_at
            FROM messages WHERE thread_id = ? ORDER BY id ASC
            """,
            (thread_id,),
        )
        out: list[StoredMessage] = []
        for row in cur.fetchall():
            out.append(
                StoredMessage(
                    id=int(row["id"]),
                    thread_id=str(row["thread_id"]),
                    role=str(row["role"]),
                    content=str(row["content"]),
                    citation_url=row["citation_url"] or None,
                    last_updated=row["last_updated"] or None,
                    footer_line=row["footer_line"] or None,
                    refusal=bool(row["refusal"]),
                    abstain=bool(row["abstain"]),
                    route=row["route"] or None,
                    abstain_reason=row["abstain_reason"] or None,
                    model_id=row["model_id"] or None,
                    created_at=str(row["created_at"]),
                )
            )
        return out
