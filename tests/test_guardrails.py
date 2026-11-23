from src.rag.guardrails import Triage, triage_query


def test_allows_drug_study_question():
    assert triage_query("Explain aspirin pharmacology and adverse effects") == Triage.GENERAL


def test_symptom_question_routes_to_symptom():
    assert triage_query("I have a fever and a headache") == Triage.SYMPTOM


def test_medication_question_routes_to_review():
    assert triage_query("What medicine should I take for my pain?") == Triage.MEDICATION_REVIEW


def test_emergency_question_routes_to_emergency():
    assert triage_query("I have chest pain and can't breathe") == Triage.EMERGENCY


def test_blocks_non_medical_question():
    assert triage_query("Write a Python sorting function") == Triage.OUT_OF_SCOPE


def test_blocks_personal_dosage_question():
    assert triage_query("What dosage should I take for my pain?") == Triage.MEDICATION_REVIEW


def test_test_decision_routes_to_review():
    assert triage_query("What blood test should I get?") == Triage.TEST_DECISION


def test_treatment_decision_routes_to_review():
    assert triage_query("What treatment should I start?") == Triage.TREATMENT_DECISION


def test_report_interpretation_routes_to_review():
    assert triage_query("What does my blood test report mean?") == Triage.REPORT_INTERPRETATION


def test_vague_message_routes_to_clarification():
    assert triage_query("help") == Triage.NEEDS_MORE_INFORMATION


def test_short_message_routes_to_clarification():
    assert triage_query("hi there") == Triage.NEEDS_MORE_INFORMATION


def test_emergency_beats_personal_decision_patterns():
    assert triage_query("I have chest pain, what medicine should I take?") == Triage.EMERGENCY


def test_educational_question_stays_general():
    assert triage_query("Explain how a blood test works") == Triage.GENERAL
