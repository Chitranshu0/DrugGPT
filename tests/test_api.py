import json

from fastapi.testclient import TestClient

from src.core.models import ChatStatus
from src.main import create_app
from src.rag.service import MedicalRAGService
from tests.conftest import FakeLLM, FakeRetriever, FakeStore


def test_health_returns_status_and_mode(app_settings):
    app = create_app(MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM))
    client = TestClient(app)
    body = client.get("/health").json()
    assert body["status"] == "running"
    assert body["mode"] == "local-development-only"


def test_models_shim_returns_configured_model(app_settings):
    app = create_app(MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM))
    body = TestClient(app).get("/v1/models").json()
    assert body["object"] == "list"
    assert body["data"][0]["id"] == app_settings.llm_model


def test_messages_since_returns_only_new_messages(app_settings, fake_store):
    fake_store.add_message("conv-1", "user", "First")
    second = fake_store.add_message("conv-1", "assistant", "Second")
    app = create_app(MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM, store=fake_store))
    client = TestClient(app)

    body = client.get("/conversations/conv-1/messages/since", params={"after": second.id}).json()
    assert body["messages"] == []
    assert body["version"] == 2
    all_messages = client.get("/conversations/conv-1/messages/since").json()
    assert len(all_messages["messages"]) == 2


def test_vector_db_status_ready(app_settings, evidence):
    app = create_app(MedicalRAGService(FakeRetriever(evidence, ready=True), app_settings, llm_factory=FakeLLM))
    client = TestClient(app)
    body = client.get("/vector-db/status").json()
    assert body["ready"] is True
    assert body["chunks_indexed"] == 1


def test_chat_falls_back_to_general_education_without_evidence(app_settings):
    app = create_app(
        MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM, store=FakeStore())
    )
    response = TestClient(app).post(
        "/conversations/conv-1/messages", json={"message": "Explain aspirin pharmacology"}
    )
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


def test_stream_endpoint_sends_sse_token_and_response_events(app_settings, evidence, fake_store):
    class StreamLLM(FakeLLM):
        def stream(self, values):
            for part in ("Aspirin ", "inhibits platelets."):
                yield type("Chunk", (), {"content": part})()

    app = create_app(
        MedicalRAGService(FakeRetriever(evidence), app_settings, llm_factory=StreamLLM, store=fake_store)
    )
    response = TestClient(app).post(
        "/conversations/conv-1/messages/stream", json={"message": "Explain aspirin pharmacology"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    payloads = [
        line.removeprefix("data: ")
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    events = [json.loads(payload) for payload in payloads]
    assert events[0]["type"] == "token"
    assert events[-1]["type"] == "response"
    assert events[-1]["response"]["answer_mode"] == "source_grounded"


def test_all_route_modules_are_wired_into_the_app(app_settings):
    """Every domain router must be registered through src.main's ROUTER_FACTORIES."""
    app = create_app(MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM))
    paths = set(app.openapi()["paths"])
    expected = {
        "/",
        "/health",
        "/vector-db/status",
        "/vector-db/rebuild",
        "/patients",
        "/patients/{patient_id}",
        "/patients/{patient_id}/summary",
        "/patients/{patient_id}/facts",
        "/patients/{patient_id}/conversations",
        "/conversations",
        "/conversations/{conversation_id}/messages",
        "/conversations/{conversation_id}/messages/since",
        "/conversations/{conversation_id}/messages/stream",
        "/conversations/{conversation_id}/transcript",
        "/conversations/{conversation_id}/clinician-reply",
        "/reviews",
        "/reviews/{review_id}",
        "/reviews/{review_id}/decision",
    }
    assert expected <= paths

