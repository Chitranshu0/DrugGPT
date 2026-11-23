"""Read and write conversation metadata in the application database."""

from datetime import datetime, timezone
from typing import Any

from backend.core.config import THREAD_TITLE_MAX_LEN
from backend.memory.db import open_app_db

DEFAULT_TITLE = "New chat"


def _now() -> str:
    """Return a sortable UTC timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _summary(row: Any) -> dict[str, Any]:
    """Convert a database row into a plain dictionary for the API layer."""
    return {
        "thread_id": row["thread_id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "message_count": row["message_count"],
    }


def auto_title(message: str) -> str:
    """Build a short thread title from the first user message."""
    title = " ".join(message.split())
    if not title:
        return DEFAULT_TITLE
    if len(title) <= THREAD_TITLE_MAX_LEN:
        return title
    return f"{title[:THREAD_TITLE_MAX_LEN].rstrip()}..."


async def create_thread(thread_id: str, title: str = DEFAULT_TITLE) -> dict[str, Any]:
    """Create one conversation row and return its summary."""
    now = _now()

    async with open_app_db() as conn:
        await conn.execute(
            """
            INSERT INTO conversations
                (thread_id, title, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, 0)
            """,
            (thread_id, title, now, now),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT * FROM conversations WHERE thread_id = ?",
            (thread_id,),
        )
        row = await cursor.fetchone()

    return _summary(row)


async def ensure_thread(thread_id: str) -> dict[str, Any]:
    """Create an empty thread if it does not exist, then return it."""
    now = _now()

    async with open_app_db() as conn:
        await conn.execute(
            """
            INSERT OR IGNORE INTO conversations
                (thread_id, title, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, 0)
            """,
            (thread_id, DEFAULT_TITLE, now, now),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT * FROM conversations WHERE thread_id = ?",
            (thread_id,),
        )
        row = await cursor.fetchone()

    return _summary(row)


async def list_threads() -> list[dict[str, Any]]:
    """Return every conversation, most recently active first."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC, thread_id DESC"
        )
        rows = await cursor.fetchall()

    return [_summary(row) for row in rows]


async def get_thread(thread_id: str) -> dict[str, Any] | None:
    """Return one conversation, or None when it does not exist."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            "SELECT * FROM conversations WHERE thread_id = ?",
            (thread_id,),
        )
        row = await cursor.fetchone()

    return _summary(row) if row else None


async def record_turn(thread_id: str, message: str, count: int = 2) -> None:
    """Update thread activity after a completed user/assistant turn.

    A thread created with the default title is renamed from the first user
    message. Renaming an existing titled thread is left to the explicit
    rename endpoint.
    """
    now = _now()
    title = auto_title(message)

    async with open_app_db() as conn:
        await conn.execute(
            """
            INSERT INTO conversations
                (thread_id, title, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(thread_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                message_count = conversations.message_count + excluded.message_count,
                title = CASE
                    WHEN conversations.title = ? THEN excluded.title
                    ELSE conversations.title
                END
            """,
            (thread_id, title, now, now, count, DEFAULT_TITLE),
        )
        await conn.commit()


async def rename_thread(thread_id: str, title: str) -> bool:
    """Rename a conversation. Returns False when the thread is missing."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            "UPDATE conversations SET title = ? WHERE thread_id = ?",
            (title, thread_id),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def delete_thread(thread_id: str) -> bool:
    """Delete a conversation row. Returns False when the thread is missing."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            "DELETE FROM conversations WHERE thread_id = ?",
            (thread_id,),
        )
        await conn.commit()
        return cursor.rowcount > 0
