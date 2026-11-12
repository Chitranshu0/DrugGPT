from druggpt.core.models import ChatStatus, Evidence
from druggpt.rag.service import MedicalRAGService, citations_from_evidence
from tests.conftest import FakeLLM, FakeRetriever


def test_citations_preserve_page_and_source(evidence):
    citation = citations_from_evidence(evidence)[0]
    assert citation.title == "Pharmacology"
    assert citation.page == 42
    assert citation.relevance_score == 0.91


def test_service_answers_only_with_relevant_evidence(app_settings, evidence):
    service = MedicalRAGService(FakeRetriever(evidence), app_settings, llm_factory=FakeLLM)
    response = service.answer("Explain aspirin pharmacology", "thread-1")
    assert response.status == ChatStatus.ANSWERED
    assert response.sources[0].page == 42
    assert response.tool_activity.tool_name == "search_medical_sources"


def test_service_requests_rephrase_when_evidence_is_weak(app_settings, evidence):
    weak = [Evidence(**{**evidence[0].__dict__, "score": 0.1})]
    service = MedicalRAGService(FakeRetriever(weak), app_settings, llm_factory=FakeLLM)
    response = service.answer("Explain aspirin pharmacology", "thread-1")
    assert response.status == ChatStatus.REPHRASE_REQUIRED


def test_service_refuses_before_retrieval(app_settings):
    service = MedicalRAGService(FakeRetriever(), app_settings, llm_factory=FakeLLM)
    response = service.answer("Diagnose me", "thread-1")
    assert response.status == ChatStatus.SAFETY_REFUSAL
