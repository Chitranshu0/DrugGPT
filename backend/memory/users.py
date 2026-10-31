"""Local user records that mirror Supabase accounts.

Supabase Auth is the source of truth for credentials and sessions. This table
exists so chat metadata can be scoped to a user without a network call, and so
the bootstrap admin can own pre-existing conversations.
"""

from datetime import datetime, timezone
from typing import Any

from backend.memory.db import open_app_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _summary(row: Any) -> dict[str, Any]:
    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "is_admin": bool(row["is_admin"]),
        "created_at": row["created_at"],
    }


async def upsert_user(
    user_id: str,
    email: str,
    is_admin: bool | None = None,
) -> dict[str, Any]:
    """Insert a user or refresh their email.

    ``is_admin`` is only changed when explicitly provided, so a normal sign-in
    cannot accidentally remove admin rights.
    """
    now = _now()

    async with open_app_db() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, email, is_admin, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                email = excluded.email,
                is_admin = CASE
                    WHEN ? IS NULL THEN users.is_admin
                    ELSE excluded.is_admin
                END
            """,
            (user_id, email, 1 if is_admin else 0, now,
             None if is_admin is None else (1 if is_admin else 0)),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()

    return _summary(row)


async def get_user(user_id: str) -> dict[str, Any] | None:
    """Return one local user, or None when they are not registered."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()

    return _summary(row) if row else None


async def set_admin(user_id: str, is_admin: bool) -> bool:
    """Grant or revoke admin rights. Returns False when the user is missing."""
    async with open_app_db() as conn:
        cursor = await conn.execute(
            "UPDATE users SET is_admin = ? WHERE user_id = ?",
            (1 if is_admin else 0, user_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
