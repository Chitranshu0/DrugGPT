from src.core.models import ChatStatus, Evidence
from src.rag.service import MedicalRAGService, citations_from_evidence
from tests.conftest import FakeLLM, FakeRetriever


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
