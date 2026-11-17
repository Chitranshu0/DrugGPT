from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.models import ChatStatus
from src.rag.service import MedicalRAGService
from tests.conftest import FakeLLM, FakeRetriever, FakeStore


def test_health_returns_status_and_mode(app_settings):
    app = create_app(MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM))
    client = TestClient(app)
    body = client.get("/health").json()
    assert body["status"] == "running"
    assert body["mode"] == "local-development-only"


def test_vector_db_status_ready(app_settings, evidence):
    app = create_app(MedicalRAGService(FakeRetriever(evidence, ready=True), app_settings, llm_factory=FakeLLM))
    client = TestClient(app)
    body = client.get("/vector-db/status").json()
    assert body["ready"] is True
    assert body["chunks_indexed"] == 1


def test_legacy_chat_returns_structured_citations(app_settings, evidence):
    app = create_app(
        MedicalRAGService(FakeRetriever(evidence), app_settings, llm_factory=FakeLLM, store=FakeStore())
    )
    response = TestClient(app).post("/chat", json={"message": "Explain aspirin pharmacology", "thread_id": "abc"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ChatStatus.ANSWERED.value
    assert body["sources"][0]["page"] == 42
    assert body["sources"][0]["title"] == "Pharmacology"
    assert body["tool_activity"]["tool_name"] == "search_medical_sources"


def test_chat_falls_back_to_general_education_without_evidence(app_settings):
    app = create_app(
        MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM, store=FakeStore())
    )
    response = TestClient(app).post("/chat", json={"message": "Explain aspirin pharmacology", "thread_id": "abc"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ChatStatus.ANSWERED.value
    assert body["answer_mode"] == "general_education"
    assert body["sources"] == []


class _StoreWithPendingReview(FakeStore):
    def __init__(self) -> None:
        super().__init__()
        self.decided: dict | None = None

    def open_review_for_conversation(self, conversation_id: str):
        class Review:
            id = "review-1"

        return Review()

    def decide_review(self, review_id, decision, reviewer_name, note, guidance):
        self.decided = {
            "review_id": review_id,
            "decision": decision,
            "reviewer_name": reviewer_name,
            "note": note,
            "guidance": guidance,
        }


def test_conversation_transcript_returns_messages_and_no_open_review(app_settings):
    store = FakeStore()
    app = create_app(MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM, store=store))
    client = TestClient(app)
    body = client.get("/conversations/conv-1/transcript").json()
    assert "messages" in body
    assert body["open_review"] is None
    assert body["context"] is None


def test_clinician_reply_endpoint(app_settings):
    store = _StoreWithPendingReview()
    app = create_app(MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM, store=store))
    client = TestClient(app)
    response = client.post(
        "/conversations/conv-1/clinician-reply",
        json={"message": "Take it with food.", "reviewer_name": "Dr. Smith"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer_mode"] == "clinician_reply"
    assert body["answer"] == "Take it with food."
    assert store.decided is not None
    assert store.decided["decision"] == "approved"
    assert store.decided["guidance"] == "Take it with food."
