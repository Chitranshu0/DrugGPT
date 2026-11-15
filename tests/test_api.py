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
