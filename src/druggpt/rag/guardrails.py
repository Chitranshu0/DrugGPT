"""Deterministic first-pass scope and clinical safety checks."""

import re
from enum import StrEnum


class GuardrailDecision(StrEnum):
    ALLOW = "allow"
    OUT_OF_SCOPE = "out_of_scope"
    SAFETY_REFUSAL = "safety_refusal"


MEDICAL_TERMS = {
    "drug", "medicine", "medication", "pharmacology", "pharmacokinetic", "dose",
    "dosage", "adverse", "side effect", "contraindication", "antibiotic", "disease",
    "anatomy", "physiology", "clinical", "medical", "treatment", "therapy", "diagnosis",
    "symptom", "pathology", "vaccine", "prescription", "patient", "trial",
}
PERSONAL_CARE_PATTERNS = (
    r"\b(what|which) (drug|medicine|medication|dose|dosage) (should|can) i (take|use)\b",
    r"\bdiagnos[ei] me\b",
    r"\bdo i have\b",
    r"\bfor my (symptom|condition|pain|child|baby|pregnancy)\b",
    r"\b(emergency|overdose|suicid|chest pain|can'?t breathe|difficulty breathing)\b",
)


def classify_query(query: str) -> GuardrailDecision:
    """Allow research questions, refusing personal or non-medical requests."""
    normalized = query.lower()
    if any(re.search(pattern, normalized) for pattern in PERSONAL_CARE_PATTERNS):
        return GuardrailDecision.SAFETY_REFUSAL
    tokens = set(re.findall(r"[a-z]+", normalized))
    if not tokens.intersection(MEDICAL_TERMS):
        return GuardrailDecision.OUT_OF_SCOPE
    return GuardrailDecision.ALLOW


OUT_OF_SCOPE_MESSAGE = (
    "DrugGPT is limited to educational medical science and drug-study questions. "
    "Please rephrase your question around pharmacology, medicine, or biomedical study."
)
SAFETY_MESSAGE = (
    "I can provide educational, source-based medical-study information, but I cannot diagnose, "
    "recommend a personal dose or treatment, or guide urgent care. Please contact a qualified "
    "healthcare professional; for urgent symptoms or a possible overdose, seek emergency help now."
)
