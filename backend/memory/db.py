"""Connection helpers and schema setup for the application SQLite database."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite

from backend.core.config import (
    DATA_DIR,
    SQLITE_APP_DB,
    SQLITE_BUSY_TIMEOUT_MS,
    SQLITE_CHECKPOINT_DB,
)

SCHEMA_VERSION = "2"

# Tables are created with the current shape. Older databases are upgraded in
# init_app_db() by adding missing columns before any index that needs them.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    TEXT PRIMARY KEY,
    email      TEXT NOT NULL UNIQUE,
    is_admin   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    thread_id     TEXT PRIMARY KEY,
    user_id       TEXT,
    title         TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_conversations_updated
    ON conversations(updated_at DESC);

CREATE TABLE IF NOT EXISTS app_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Kept separate because it references a column that older databases must add
# first (see _ensure_user_column).
USER_INDEX = """
CREATE INDEX IF NOT EXISTS idx_conversations_user
    ON conversations(user_id, updated_at DESC);
"""


def ensure_data_dir() -> None:
    """Create the folders that hold the SQLite files.

    This runs at application startup, never at import time.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SQLITE_CHECKPOINT_DB.parent.mkdir(parents=True, exist_ok=True)
    SQLITE_APP_DB.parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def open_app_db() -> AsyncIterator[aiosqlite.Connection]:
    """Open a short-lived connection to the application database.

    WAL mode lets the checkpointer and the metadata connection read and write
    without blocking each other for long. The busy timeout makes short
    concurrent writes wait instead of failing immediately.
    """
    conn = await aiosqlite.connect(SQLITE_APP_DB)
    conn.row_factory = aiosqlite.Row

    try:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        yield conn
    finally:
        await conn.close()


async def _ensure_user_column(conn: aiosqlite.Connection) -> None:
    """Add conversations.user_id to databases created before multi-user."""
    cursor = await conn.execute("PRAGMA table_info(conversations)")
    columns = {row["name"] for row in await cursor.fetchall()}
    if "user_id" not in columns:
        await conn.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")


async def init_app_db() -> None:
    """Create or upgrade the application tables."""
    ensure_data_dir()

    async with open_app_db() as conn:
        await conn.executescript(SCHEMA)
        await _ensure_user_column(conn)
        await conn.executescript(USER_INDEX)
        await conn.execute(
            """
            INSERT INTO app_meta (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            ("schema_version", SCHEMA_VERSION),
        )
        await conn.commit()
