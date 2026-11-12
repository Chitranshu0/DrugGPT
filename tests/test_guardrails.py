from druggpt.rag.guardrails import GuardrailDecision, classify_query


def test_allows_drug_study_question():
    assert classify_query("Explain aspirin pharmacology and adverse effects") == GuardrailDecision.ALLOW


def test_blocks_non_medical_question():
    assert classify_query("Write a Python sorting function") == GuardrailDecision.OUT_OF_SCOPE


def test_blocks_personal_dosage_question():
    assert classify_query("What dosage should I take for my pain?") == GuardrailDecision.SAFETY_REFUSAL
