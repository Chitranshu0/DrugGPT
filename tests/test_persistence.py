"""Regression tests for the real SQLite store (not the in-memory FakeStore).

The API/service tests inject FakeStore, so schema drift in LocalStore can slip
through unnoticed. These tests exercise the actual SQL against a temp database.
"""

import sqlite3

from src.core.persistence import LocalStore


def test_create_conversation_round_trips_with_default_mode(tmp_path):
    store = LocalStore(tmp_path / "druggpt.db")
    patient = store.create_patient("Guest patient", None, None)

    conversation = store.create_conversation(patient.id, "New medical chat")

    assert conversation.id
    assert conversation.patient_id == patient.id
    assert conversation.title == "New medical chat"
    assert conversation.mode == "ai"

    # Reading it back must succeed too (SELECT * now sees all six columns).
    stored = store.get_conversation(conversation.id)
    assert stored.mode == "ai"
    assert stored.title == "New medical chat"


def test_setup_backfills_mode_on_legacy_database(tmp_path):
    """Databases created before the mode column existed are migrated in place."""
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE conversations ("
            "id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, title TEXT NOT NULL, "
            "created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO conversations VALUES (?, ?, ?, ?, ?)",
            ("conv-legacy", "patient-1", "Old chat", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        )

    LocalStore(db_path)  # _setup() runs the idempotent migration

    columns = {row[1] for row in sqlite3.connect(db_path).execute("PRAGMA table_info(conversations)").fetchall()}
    assert "mode" in columns
    with sqlite3.connect(db_path) as conn:
        mode = conn.execute("SELECT mode FROM conversations WHERE id=?", ("conv-legacy",)).fetchone()[0]
    assert mode == "ai"
