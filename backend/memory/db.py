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

SCHEMA_VERSION = "1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    thread_id     TEXT PRIMARY KEY,
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


async def init_app_db() -> None:
    """Create the application tables if they do not exist yet."""
    ensure_data_dir()

    async with open_app_db() as conn:
        await conn.executescript(SCHEMA)
        await conn.execute(
            "INSERT OR IGNORE INTO app_meta (key, value) VALUES (?, ?)",
            ("schema_version", SCHEMA_VERSION),
        )
        await conn.commit()
