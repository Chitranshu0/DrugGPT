"""Read and write conversation metadata in the application database.

Every query is scoped to a ``user_id`` so one account can never list, open,
rename, or delete another account's conversations.
"""

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


async def create_thread(
    user_id: str,
    thread_id: str,
    title: str = DEFAULT_TITLE,
) -> dict[str, Any]:
    """Create one conversation row and return its summary."""
    now = _now()

    async with open_app_db() as conn:
        await conn.execute(
            """
            INSERT INTO conversations
                (thread_id, user_id, title, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (thread_id, user_id, title, now, now),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT * FROM conversations WHERE thread_id = ? AND user_id = ?",
            (thread_id, user_id),
        )
        row = await cursor.fetchone()

    return _summary(row)


async def ensure_thread(
    user_id: str,
    thread_id: str,
) -> dict[str, Any] | None:
    """Create an empty thread if needed, then return it.

    Returns None when the id already belongs to a different user, so callers
    can answer 404 instead of revealing the conversation's existence.
    """
    now = _now()

    async with open_app_db() as conn:
        await conn.execute(
            """
            INSERT OR IGNORE INTO conversations
                (thread_id, user_id, title, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (thread_id, user_id, DEFAULT_TITLE, now, now),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT * FROM conversations WHERE thread_id = ?",
            (thread_id,),
        )
        row = await cursor.fetchone()

    if row is None or row["user_id"] != user_id:
        return None

    return _summary(row)


async def list_threads(user_id: str) -> list[dict[str, Any]]:
    """Return one user's conversations, most recently active first."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            """
            SELECT * FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC, thread_id DESC
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()

    return [_summary(row) for row in rows]


async def get_thread(
    user_id: str,
    thread_id: str,
) -> dict[str, Any] | None:
    """Return one conversation owned by the user, or None."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            "SELECT * FROM conversations WHERE thread_id = ? AND user_id = ?",
            (thread_id, user_id),
        )
        row = await cursor.fetchone()

    return _summary(row) if row else None


async def record_turn(
    user_id: str,
    thread_id: str,
    message: str,
    count: int = 2,
) -> None:
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
            UPDATE conversations SET
                updated_at = ?,
                message_count = message_count + ?,
                title = CASE WHEN title = ? THEN ? ELSE title END
            WHERE thread_id = ? AND user_id = ?
            """,
            (now, count, DEFAULT_TITLE, title, thread_id, user_id),
        )
        await conn.commit()


async def rename_thread(user_id: str, thread_id: str, title: str) -> bool:
    """Rename a conversation. Returns False when the thread is missing."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            """
            UPDATE conversations SET title = ?
            WHERE thread_id = ? AND user_id = ?
            """,
            (title, thread_id, user_id),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def delete_thread(user_id: str, thread_id: str) -> bool:
    """Delete a conversation row. Returns False when the thread is missing."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            "DELETE FROM conversations WHERE thread_id = ? AND user_id = ?",
            (thread_id, user_id),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def assign_unowned_threads(user_id: str) -> int:
    """Give conversations created before multi-user support to one user.

    Returns the number of rows that were backfilled.
    """
    async with open_app_db() as conn:
        cursor = await conn.execute(
            "UPDATE conversations SET user_id = ? WHERE user_id IS NULL",
            (user_id,),
        )
        await conn.commit()
        return cursor.rowcount
