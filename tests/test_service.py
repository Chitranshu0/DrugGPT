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
