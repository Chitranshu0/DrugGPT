"""Regression tests for the real SQLite store (not the in-memory FakeStore).

The API/service tests inject FakeStore, so schema drift in LocalStore can slip
through unnoticed. These tests exercise the actual SQL against a temp database.
"""

from src.core.persistence import LocalStore


def test_create_conversation_round_trips(tmp_path):
    store = LocalStore(tmp_path / "druggpt.db")
    patient = store.create_patient("Guest patient", None, None)

    conversation = store.create_conversation(patient.id, "New medical chat")

    assert conversation.id
    assert conversation.patient_id == patient.id
    assert conversation.title == "New medical chat"

    stored = store.get_conversation(conversation.id)
    assert stored.title == "New medical chat"
