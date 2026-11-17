import pytest

from src.core.models import ChatStatus, Evidence
from src.rag.service import MedicalRAGService, citations_from_evidence
from tests.conftest import FakeLLM, FakeRetriever, FakeStore


def test_citations_preserve_page_and_source(evidence):
    citation = citations_from_evidence(evidence)[0]
    assert citation.title == "Pharmacology"
    assert citation.page == 42
    assert citation.relevance_score == 0.91


def test_service_answers_only_with_relevant_evidence(app_settings, evidence, fake_store):
    service = MedicalRAGService(FakeRetriever(evidence), app_settings, llm_factory=FakeLLM, store=fake_store)
    response = service.send_message("conv-1", "Explain aspirin pharmacology")
    assert response.status == ChatStatus.ANSWERED
    assert response.sources[0].page == 42
    assert response.sources[0].title == "Pharmacology"
    assert response.tool_activity.tool_name == "search_medical_sources"
    assert response.answer_mode == "source_grounded"


def test_service_falls_back_to_general_education_when_evidence_is_weak(app_settings, evidence, fake_store):
    weak = [Evidence(**{**evidence[0].__dict__, "score": 0.1})]
    service = MedicalRAGService(FakeRetriever(weak), app_settings, llm_factory=FakeLLM, store=fake_store)
    response = service.send_message("conv-1", "Explain aspirin pharmacology")
    assert response.status == ChatStatus.ANSWERED
    assert response.answer_mode == "general_education"
    assert response.sources == []


def test_service_refuses_before_retrieval_when_database_is_not_ready(app_settings, fake_store):
    service = MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM, store=fake_store)
    response = service.send_message("conv-1", "Explain aspirin pharmacology")
    assert response.status == ChatStatus.ANSWERED
    assert response.answer_mode == "general_education"


class _PendingReview:
    def __init__(self, review_id: str = "review-1") -> None:
        self.id = review_id


class _StoreWithPendingReview(FakeStore):
    def __init__(self) -> None:
        super().__init__()
        self.decided: dict | None = None

    def open_review_for_conversation(self, conversation_id: str):
        return _PendingReview("review-1")

    def decide_review(self, review_id, decision, reviewer_name, note, guidance):
        self.decided = {
            "review_id": review_id,
            "decision": decision,
            "reviewer_name": reviewer_name,
            "note": note,
            "guidance": guidance,
        }


def test_send_message_human_handoff_queues_for_clinician(app_settings, fake_store):
    fake_store.set_conversation_mode("conv-1", "human")
    service = MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM, store=fake_store)
    response = service.send_message("conv-1", "Should I take this drug?")
    assert response.status == ChatStatus.REVIEW_PENDING
    assert response.answer_mode == "human_hold"
    assert response.review_id is None
    roles = [m.role for m in fake_store.messages["conv-1"]]
    assert roles == ["user", "assistant"]


class _CountingRetriever(FakeRetriever):
    def __init__(self, evidence=None) -> None:
        super().__init__(evidence)
        self.calls = 0

    def search(self, query):
        self.calls += 1
        return super().search(query)


class _Review:
    id = "review-1"
    patient_id = "patient-1"
    conversation_id = "conv-1"
    message_id = "msg-1"
    draft_guidance = "Internal draft for clinician review."
    status = "pending"


class _ReviewStore(FakeStore):
    def __init__(self) -> None:
        super().__init__()
        self.review = _Review()

    def create_or_get_review(self, *args, **kwargs):
        return self.review

    def review_context(self, review_id: str):
        return {"issue_type": "personal_health_decision"}

    def find_pending_review(self, thread_id: str):
        return self.review


def test_unclear_message_asks_follow_up_without_rag(app_settings):
    retriever = _CountingRetriever()
    service = MedicalRAGService(retriever, app_settings, llm_factory=FakeLLM, store=FakeStore())
    response = service.send_message("conv-1", "help")
    assert response.status == ChatStatus.NEEDS_MORE_INFORMATION
    assert response.answer_mode == "clarification"
    assert response.sources == []
    assert retriever.calls == 0


def test_clarification_is_deterministic_and_does_not_call_llm(app_settings):
    created = []

    class _Factory:
        def __call__(self):
            created.append(1)
            return FakeLLM()

    service = MedicalRAGService(FakeRetriever(), app_settings, llm_factory=_Factory, store=FakeStore())
    response = service.send_message("conv-1", "hi")
    assert response.answer_mode == "clarification"
    assert created == []


class _StreamLLM(FakeLLM):
    def stream(self, values):
        for part in ("Aspirin ", "inhibits ", "platelets."):
            yield type("Chunk", (), {"content": part})()


def test_stream_emits_tokens_then_answer_response(app_settings, evidence, fake_store):
    service = MedicalRAGService(
        FakeRetriever(evidence), app_settings, llm_factory=_StreamLLM, store=fake_store
    )
    events = list(service.send_message_stream("conv-1", "Explain aspirin pharmacology"))
    tokens = [event["token"] for event in events if event["type"] == "token"]
    terminal = [event for event in events if event["type"] == "response"]
    assert "".join(tokens) == "Aspirin inhibits platelets."
    assert len(terminal) == 1
    assert terminal[0]["response"]["answer_mode"] == "source_grounded"
    assert terminal[0]["response"]["sources"][0]["page"] == 42
    roles = [message.role for message in fake_store.messages["conv-1"]]
    assert roles == ["user", "assistant"]


def test_stream_non_answer_route_reuses_guardrail_response(app_settings):
    service = MedicalRAGService(
        FakeRetriever(), app_settings, llm_factory=_StreamLLM, store=_ReviewStore()
    )
    events = list(service.send_message_stream("conv-1", "What medicine should I take?"))
    assert [event["type"] for event in events] == ["response"]
    assert events[0]["response"]["answer_mode"] == "clinician_review"


@pytest.mark.parametrize(
    "message",
    [
        "What blood test should I get?",
        "What treatment should I start?",
        "What does my blood test report mean?",
        "What medicine should I take?",
    ],
)
def test_personal_health_decisions_pause_for_clinician_without_rag(app_settings, message):
    retriever = _CountingRetriever()
    service = MedicalRAGService(retriever, app_settings, llm_factory=FakeLLM, store=_ReviewStore())
    response = service.send_message("conv-1", message)
    assert response.status == ChatStatus.REVIEW_PENDING
    assert response.answer_mode == "clinician_review"
    assert response.review_id == "review-1"
    assert retriever.calls == 0


def test_reply_as_clinician_closes_review_and_returns_ai_mode(app_settings):
    store = _StoreWithPendingReview()
    store.set_conversation_mode("conv-1", "human")
    service = MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM, store=store)
    response = service.reply_as_clinician(
        conversation_id="conv-1", message="Take it with food.", reviewer_name="Dr. Smith"
    )
    assert response.status == ChatStatus.ANSWERED
    assert response.answer_mode == "clinician_reply"
    assert response.review_id == "review-1"
    assert store.decided is not None
    assert store.decided["decision"] == "approved"
    assert store.decided["guidance"] == "Take it with food."
    assert store.decided["reviewer_name"] == "Dr. Smith"
    assert store.conversation_mode("conv-1") == "ai"
    clinician_msgs = [m for m in store.messages["conv-1"] if m.role == "clinician"]
    assert len(clinician_msgs) == 1
    assert clinician_msgs[0].content == "Take it with food."
