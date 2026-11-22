from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.core.config import Settings
from src.core.models import (
    Conversation,
    ConversationMessage,
    DatabaseStatus,
    Evidence,
    Patient,
)
from src.rag.service import MedicalRAGService


def _now() -> str:
    return datetime.now(UTC).isoformat()


class FakeRetriever:
    def __init__(self, evidence=None, ready: bool = True) -> None:
        self.evidence = evidence or []
        self.ready = ready

    def search(self, query):
        return self.evidence

    def status(self) -> DatabaseStatus:
        return DatabaseStatus(
            ready=self.ready,
            chunks_indexed=len(self.evidence),
            documents_indexed=1,
        )


class FakeLLM:
    def __init__(self, content: str = "A sourced educational answer.") -> None:
        self.content = content
        self.calls = 0

    def invoke(self, values):
        self.calls += 1

        class Response:
            content = self.content

        return Response()

    def stream(self, values):
        self.calls += 1
        for part in (self.content[:10], self.content[10:]):
            if part:
                yield type("Chunk", (), {"content": part})()


class FakeStore:
    """Minimal in-memory store stand-in used by service tests."""

    def __init__(self, patient_id: str = "patient-1") -> None:
        self.patient_id = patient_id
        self.messages: dict[str, list[ConversationMessage]] = {}
        self.reviews: dict[str, object] = {}
        self.deleted_patient_ids: list[str] = []
        self.deleted_conversation_ids: list[str] = []

    def get_patient(self, patient_id: str) -> Patient:
        return Patient(
            id=patient_id,
            name="Guest patient",
            date_of_birth=None,
            sex=None,
            created_at=_now(),
            updated_at=_now(),
        )

    def delete_patient(self, patient_id: str) -> None:
        if patient_id in self.deleted_patient_ids:
            raise KeyError("Patient not found")
        self.deleted_patient_ids.append(patient_id)

    def delete_conversation(self, conversation_id: str) -> None:
        if conversation_id in self.deleted_conversation_ids:
            raise KeyError("Conversation not found")
        self.deleted_conversation_ids.append(conversation_id)
        self.messages.pop(conversation_id, None)

    def list_facts(self, patient_id: str, approved_only: bool = False):
        return []

    def latest_summary(self, patient_id: str):
        return None

    def get_conversation(self, conversation_id: str) -> Conversation:
        return Conversation(
            id=conversation_id,
            patient_id=self.patient_id,
            title="New medical chat",
            created_at=_now(),
            updated_at=_now(),
        )

    def ensure_demo_patient(self) -> Patient:
        return self.get_patient(self.patient_id)

    def list_messages(self, conversation_id: str, limit: int | None = None):
        return self.messages.get(conversation_id, [])

    def add_message(self, conversation_id, role, content, status=None, metadata=None) -> ConversationMessage:
        msg = ConversationMessage(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            status=status,
            created_at=_now(),
            metadata=metadata or {},
        )
        self.messages.setdefault(conversation_id, []).append(msg)
        return msg

    def find_pending_review(self, thread_id: str):
        return None

    def open_review_for_conversation(self, conversation_id: str):
        return None

    def decide_review(self, review_id, decision, reviewer_name, note, guidance):
        return None

    def create_or_get_review(self, *args, **kwargs):
        raise NotImplementedError("not needed for general-answer tests")

    def review_context(self, review_id: str):
        raise NotImplementedError("not needed for general-answer tests")

    def get_review(self, review_id: str):
        raise NotImplementedError("not needed for general-answer tests")


@pytest.fixture
def app_settings(tmp_path: Path) -> Settings:
    return replace(Settings(), data_dir=tmp_path / "data", relevance_threshold=0.35)


@pytest.fixture
def evidence():
    return [
        Evidence(
            content="Aspirin irreversibly inhibits cyclooxygenase in platelets.",
            source_path="data/raw/pharmacology.pdf",
            source_title="Pharmacology",
            page=42,
            score=0.91,
        )
    ]


@pytest.fixture
def fake_store():
    return FakeStore()


@pytest.fixture
def service(app_settings, fake_store):
    return MedicalRAGService(
        FakeRetriever(),
        app_settings,
        llm_factory=FakeLLM,
        store=fake_store,
    )
