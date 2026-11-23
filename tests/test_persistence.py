"""Regression tests for the real SQLite store (not the in-memory FakeStore).

The API/service tests inject FakeStore, so schema drift in LocalStore can slip
through unnoticed. These tests exercise the actual SQL against a temp database.
"""

import pytest

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


def test_delete_conversation_removes_messages_and_reviews(tmp_path):
    store = LocalStore(tmp_path / "druggpt.db")
    patient = store.create_patient("Guest patient", None, None)
    conversation = store.create_conversation(patient.id, "New medical chat")
    message = store.add_message(conversation.id, "user", "Hello")
    review = store.create_or_get_review(
        patient.id, conversation.id, message.id, "thread-1", "Draft guidance", {"topic": "demo"}
    )

    store.delete_conversation(conversation.id)

    assert store.list_messages(conversation.id) == []
    with pytest.raises(KeyError):
        store.get_review(review.id)
    with pytest.raises(KeyError):
        store.get_conversation(conversation.id)
    with pytest.raises(KeyError):
        store.delete_conversation(conversation.id)
    # The patient itself survives the deletion of one of its chats.
    assert store.get_patient(patient.id).id == patient.id


def test_delete_patient_removes_all_dependent_records(tmp_path):
    store = LocalStore(tmp_path / "druggpt.db")
    patient = store.create_patient("Guest patient", None, None)
    store.add_fact(patient.id, "allergy", "penicillin", True)
    store.save_summary(patient.id, "Demo summary")
    conversation = store.create_conversation(patient.id, "New medical chat")
    message = store.add_message(conversation.id, "user", "Hello")
    review = store.create_or_get_review(
        patient.id, conversation.id, message.id, "thread-1", "Draft guidance", {"topic": "demo"}
    )

    store.delete_patient(patient.id)

    assert store.list_patients() == []
    assert store.list_facts(patient.id) == []
    assert store.latest_summary(patient.id) is None
    assert store.list_conversations(patient.id) == []
    assert store.list_messages(conversation.id) == []
    with pytest.raises(KeyError):
        store.get_patient(patient.id)
    with pytest.raises(KeyError):
        store.get_conversation(conversation.id)
    with pytest.raises(KeyError):
        store.get_review(review.id)
    with pytest.raises(KeyError):
        store.delete_patient(patient.id)
