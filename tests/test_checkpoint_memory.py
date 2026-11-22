"""Regression tests for conversation-scoped LangGraph checkpoint persistence.

The checkpointer was previously active but keyed per *message*, so every turn
started a fresh graph state and the assistant remembered nothing. These tests
use a real SQLite checkpointer on a temp database to prove that turns now share
one thread, survive a service restart, and work on the streaming path too.
"""

import sqlite3
from dataclasses import replace

from langgraph.checkpoint.sqlite import SqliteSaver

from src.core.config import Settings
from src.core.persistence import LocalStore
from src.rag.service import MedicalRAGService
from tests.conftest import FakeRetriever, FakeStore


class RecordingLLM:
    """Stub LLM that records the fully rendered prompt for each call."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def factory(self):
        recorder = self

        class LLM:
            def invoke(self, values):
                recorder.prompts.append(str(values))
                return type("Response", (), {"content": "A sourced educational answer."})()

            def stream(self, values):
                recorder.prompts.append(str(values))
                for part in ("A sourced ", "educational answer."):
                    yield type("Chunk", (), {"content": part})()

        return LLM()


def _make_service(tmp_path, recorder: RecordingLLM, store=None) -> MedicalRAGService:
    app_settings = replace(Settings(), data_dir=tmp_path / "data", relevance_threshold=0.35)
    checkpointer = SqliteSaver(sqlite3.connect(tmp_path / "checkpoints.db", check_same_thread=False))
    return MedicalRAGService(
        FakeRetriever([]),
        app_settings,
        llm_factory=recorder.factory,
        store=store or FakeStore(),
        checkpointer=checkpointer,
    )


def test_turns_share_one_conversation_thread_and_restore_history(tmp_path):
    recorder = RecordingLLM()
    service = _make_service(tmp_path, recorder)
    conversation_id = "conv-memory"

    service.send_message(conversation_id, "How does aspirin work in the body?")
    service.send_message(conversation_id, "Can I eat food with it?")

    assert len(recorder.prompts) == 2
    assert "How does aspirin work in the body?" in recorder.prompts[1]
    assert "A sourced educational answer." in recorder.prompts[1]

    with sqlite3.connect(tmp_path / "checkpoints.db") as conn:
        threads = [row[0] for row in conn.execute("SELECT DISTINCT thread_id FROM checkpoints")]
    assert threads == [f"conversation:{conversation_id}"]


def test_new_service_instance_restores_checkpoint_from_disk(tmp_path):
    conversation_id = "conv-restart"

    first = RecordingLLM()
    _make_service(tmp_path, first).send_message(conversation_id, "Aspirin is for the heart.")
    _make_service(tmp_path, first).send_message(conversation_id, "Remember that fact, please.")

    # A brand-new service/store has no in-memory transcript; only SQLite can
    # supply the earlier turns here.
    second = RecordingLLM()
    _make_service(tmp_path, second).send_message(conversation_id, "What did I say earlier?")

    assert "Aspirin is for the heart." in second.prompts[0]
    assert "Remember that fact, please." in second.prompts[0]


def test_streaming_path_reads_and_writes_checkpoint_memory(tmp_path):
    conversation_id = "conv-stream"

    first = RecordingLLM()
    service = _make_service(tmp_path, first)
    service.send_message(conversation_id, "Aspirin reduces platelet aggregation.")
    events = list(service.send_message_stream(conversation_id, "And what about food?"))

    assert any(event["type"] == "token" for event in events)
    assert "Aspirin reduces platelet aggregation." in first.prompts[-1]

    second = RecordingLLM()
    _make_service(tmp_path, second).send_message(conversation_id, "Recap our chat.")
    assert "And what about food?" in second.prompts[0]
    assert "A sourced educational answer." in second.prompts[0]


def test_review_interrupt_keeps_conversation_thread_free(tmp_path):
    app_settings = replace(Settings(), data_dir=tmp_path / "data", relevance_threshold=0.35)
    store = LocalStore(app_settings.application_db)
    patient = store.create_patient("Guest patient", None, None)
    conversation = store.create_conversation(patient.id, "Review chat")
    recorder = RecordingLLM()
    checkpointer = SqliteSaver(sqlite3.connect(tmp_path / "checkpoints.db", check_same_thread=False))
    service = MedicalRAGService(
        FakeRetriever([]), app_settings, llm_factory=recorder.factory, store=store, checkpointer=checkpointer
    )

    pending = service.send_message(conversation.id, "What medicine should I take for a headache?")
    assert pending.status.value == "review_pending"
    reviews = store.list_reviews(status="pending")
    assert len(reviews) == 1
    review = reviews[0]

    # A paused review must not block ordinary turns on the conversation thread.
    service.send_message(conversation.id, "Aspirin is commonly used.")

    store.decide_review(review.id, "approved", "Dr. Reviewer", "Looks fine", "Clinician guidance here.")
    resumed = service.resume_review(store.get_review(review.id))
    assert resumed.answer == "Clinician guidance here."

    with sqlite3.connect(tmp_path / "checkpoints.db") as conn:
        threads = [row[0] for row in conn.execute("SELECT DISTINCT thread_id FROM checkpoints")]
    assert f"conversation:{conversation.id}" in threads
    assert any(thread.startswith(f"conversation:{conversation.id}:review:") for thread in threads)
