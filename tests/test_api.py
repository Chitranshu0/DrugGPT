from fastapi.testclient import TestClient

from druggpt.api.app import create_app
from druggpt.rag.service import MedicalRAGService
from tests.conftest import FakeLLM, FakeRetriever


def test_health_and_index_status(app_settings):
    app = create_app(MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM))
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "running"}
    assert client.get("/vector-db/status").status_code == 200


def test_chat_returns_structured_citations(app_settings, evidence):
    app = create_app(MedicalRAGService(FakeRetriever(evidence), app_settings, llm_factory=FakeLLM))
    response = TestClient(app).post("/chat", json={"message": "Explain aspirin pharmacology", "thread_id": "abc"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["sources"][0]["page"] == 42
