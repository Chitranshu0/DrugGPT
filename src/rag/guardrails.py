"""Triage rules for a conversational, educational medical assistant.

Triage is deterministic and rule-based. It decides which LangGraph branch a
message takes; it never decides clinical content. Personal clinical decisions
(medicines, tests, treatments, report interpretation) are routed to the
clinician-review branch instead of being answered by the model.
"""

import re
from enum import StrEnum


class Triage(StrEnum):
    GENERAL = "general"
    SYMPTOM = "symptom"
    MEDICATION_REVIEW = "medication_review"
    TEST_DECISION = "test_decision"
    TREATMENT_DECISION = "treatment_decision"
    REPORT_INTERPRETATION = "report_interpretation"
    EMERGENCY = "emergency"
    OUT_OF_SCOPE = "out_of_scope"
    NEEDS_MORE_INFORMATION = "needs_more_information"


# Every personal clinical decision pauses for a clinician instead of getting an AI answer.
CLINICIAN_REVIEW_TRIAGE = frozenset(
    {
        Triage.MEDICATION_REVIEW,
        Triage.TEST_DECISION,
        Triage.TREATMENT_DECISION,
        Triage.REPORT_INTERPRETATION,
    }
)

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
TEST_PATTERNS = (
    r"\b(what|which) (?:(?:blood|lab|medical|imaging) )?test (?:should|can|do) i (?:get|take|do|need|have)\b",
    r"\b(?:should i|do i need|can i) (?:get|take|do|have|need) (?:a |an )?"
    r"(?:(?:blood|lab|medical|imaging) )?(?:test|scan|x-?ray|mri|ct|ultrasound|screening)\b",
    r"\brecommend (?:a |an )?(?:(?:blood|lab|medical|imaging) )?(?:test|scan|screening)\b",
    r"\bwhich (?:test|scan) is (?:right|best|needed)\b",
)
TREATMENT_PATTERNS = (
    r"\b(what|which) (?:(?:medical|drug) )?treatment (?:should|can|do) i "
    r"(?:get|use|have|need|receive|start|begin|try|undergo)\b",
    r"\b(?:should i|can i) (?:start|begin|undergo|try) (?:treatment|therapy|medication)\b",
    r"\brecommend (?:a |some )?(?:treatment|therapy)\b",
)
REPORT_PATTERNS = (
    r"\b(interpret|explain|read|understand) (?:(?:my|the) )?"
    r"(?:(?:test|lab|blood|medical|imaging) )*(?:report|results?|scan)\b",
    r"\bwhat (?:does|do) (?:(?:my|the) )?"
    r"(?:(?:test|lab|blood|medical|imaging) )*(?:report|results?|scan) (?:mean|say|show|indicate)\b",
    r"\bmy (?:(?:test|lab|blood|medical|imaging) )*"
    r"(?:report|results?|scan) (?:show|shows|say|says|indicate|indicates|is|are)\b",
    r"\b(?:test report|lab report|lab results|blood test results|mri report|x-?ray report)\b",
)
SYMPTOM_TERMS = {
    "pain",
    "fever",
    "cough",
    "rash",
    "nausea",
    "vomit",
    "diarrhea",
    "dizzy",
    "fatigue",
    "headache",
    "symptom",
    "sick",
}
VAGUE_PATTERNS = (
    r"^(?:hi|hello|hey|help|what|why|how|hmm|uh|ok|okay|yes|no|maybe|something)\??!?$",
    r"^(?:i (?:have|feel|am) (?:something|bad|sick|unwell)|something is wrong|i need help|"
    r"my problem|not feeling well)\??!?$",
    r"^(?:tell me more|what about it|and then|so what)\??!?$",
)


def is_vague(query: str, tokens: set[str]) -> bool:
    """Return True when a message is too short or generic to answer meaningfully."""
    stripped = query.strip().lower().rstrip("?!.")
    if any(re.fullmatch(pattern, stripped) for pattern in VAGUE_PATTERNS):
        return True
    return len(tokens) < 3 and not tokens.intersection(MEDICAL_TERMS)


def triage_query(query: str) -> Triage:
    """Classify chat intent without excluding common medical language.

    Emergency signals always win. Personal clinical decisions are routed to a
    clinician; everything else is educational or a request for clarification.
    """
    normalized = query.lower()
    if any(re.search(pattern, normalized) for pattern in EMERGENCY_PATTERNS):
        return Triage.EMERGENCY
    if any(re.search(pattern, normalized) for pattern in MEDICATION_PATTERNS):
        return Triage.MEDICATION_REVIEW
    if any(re.search(pattern, normalized) for pattern in TEST_PATTERNS):
        return Triage.TEST_DECISION
    if any(re.search(pattern, normalized) for pattern in TREATMENT_PATTERNS):
        return Triage.TREATMENT_DECISION
    if any(re.search(pattern, normalized) for pattern in REPORT_PATTERNS):
        return Triage.REPORT_INTERPRETATION
    tokens = set(re.findall(r"[a-z]+", normalized))
    if tokens.intersection(SYMPTOM_TERMS):
        return Triage.SYMPTOM
    if tokens.intersection(OUT_OF_SCOPE_TERMS) and not tokens.intersection(MEDICAL_TERMS):
        return Triage.OUT_OF_SCOPE
    if is_vague(query, tokens):
        return Triage.NEEDS_MORE_INFORMATION
    return Triage.GENERAL


OUT_OF_SCOPE_MESSAGE = "I’m DrugGPT, so I can help with medical, health, medication, and wellbeing questions."
EMERGENCY_MESSAGE = (
    "Your message may describe an emergency. Please contact local emergency services or go to the nearest "
    "emergency department now. If possible, ask someone nearby to help you."
)
CLARIFY_MESSAGE = (
    "Could you tell me a little more about what you'd like to know? "
    "For example, are you asking about how something works, or do you need help with a personal health decision?"
)
