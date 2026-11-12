"""Triage rules for a conversational, educational medical assistant."""

import re
from enum import StrEnum


class Triage(StrEnum):
    GENERAL = "general"
    SYMPTOM = "symptom"
    MEDICATION_REVIEW = "medication_review"
    EMERGENCY = "emergency"
    OUT_OF_SCOPE = "out_of_scope"


MEDICAL_TERMS = {
    "aids", "adverse", "allergy", "anatomy", "antibiotic", "blood", "cancer", "carcinogen",
    "clinical", "condition", "covid", "disease", "doctor", "drug", "health", "heart", "hiv",
    "infection", "medicine", "medication", "mental", "pain", "patient", "pharmacology", "pregnancy",
    "prevention", "prescription", "risk", "side effect", "symptom", "therapy", "treatment", "tumor",
    "vaccine", "virus", "wellness", "diabetes", "asthma", "headache", "fever", "cough", "rash",
}
OUT_OF_SCOPE_TERMS = {"code", "python", "football", "weather", "recipe", "bitcoin", "movie", "song"}
EMERGENCY_PATTERNS = (
    r"\b(chest pain|can'?t breathe|difficulty breathing|severe bleeding|unconscious|stroke|overdose)\b",
    r"\b(suicid|kill myself|self harm)\b",
)
MEDICATION_PATTERNS = (
    r"\b(what|which) (medicine|medication|drug|tablet|pill|dose|dosage) (should|can) i (take|use)\b",
    r"\b(recommend|prescribe|suggest) (a |some )?(medicine|medication|drug|tablet|pill)\b",
    r"\bhow much (medicine|medication|drug|dose|dosage)\b",
    r"\b(can i|should i) (start|stop|change|increase|decrease)\b.*\b(medicine|medication|drug|dose)\b",
)
SYMPTOM_TERMS = {"pain", "fever", "cough", "rash", "nausea", "vomit", "diarrhea", "dizzy", "fatigue", "headache", "symptom", "sick"}


def triage_query(query: str) -> Triage:
    """Classify chat intent without excluding common medical language."""
    normalized = query.lower()
    if any(re.search(pattern, normalized) for pattern in EMERGENCY_PATTERNS):
        return Triage.EMERGENCY
    if any(re.search(pattern, normalized) for pattern in MEDICATION_PATTERNS):
        return Triage.MEDICATION_REVIEW
    tokens = set(re.findall(r"[a-z]+", normalized))
    if tokens.intersection(SYMPTOM_TERMS):
        return Triage.SYMPTOM
    if tokens.intersection(MEDICAL_TERMS) or not tokens.intersection(OUT_OF_SCOPE_TERMS):
        return Triage.GENERAL
    return Triage.OUT_OF_SCOPE


OUT_OF_SCOPE_MESSAGE = "I’m DrugGPT, so I can help with medical, health, medication, and wellbeing questions."
EMERGENCY_MESSAGE = (
    "Your message may describe an emergency. Please contact local emergency services or go to the nearest "
    "emergency department now. If possible, ask someone nearby to help you."
)
