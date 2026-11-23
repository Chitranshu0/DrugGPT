"""Keep the chatbot inside the medical domain.

A very small Groq call classifies each question as MEDICAL or OTHER before
retrieval. The classifier is intentionally inclusive: if a question could
reasonably be about health, it is allowed.

If the classifier call fails for any reason, the question is allowed through
(fail open) so a temporary API problem does not break the chatbot. The main
answer prompt still contains strict medical-only rules.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from backend.core.config import GROQ_API_KEY, MEDICAL_SCOPE_GUARD, SCOPE_MODEL

logger = logging.getLogger(__name__)

REFUSAL_ANSWER = (
    "I can only help with medical and health-related questions. "
    "Please ask about symptoms, conditions, medicines, tests, treatment, "
    "nutrition, or another health topic."
)

_SCOPE_PROMPT = """You are a strict topic classifier for a medical chatbot.

Decide whether the user's message is a MEDICAL question or an OTHER request.

MEDICAL includes:
- symptoms, diseases, conditions, diagnosis, tests, treatment, procedures
- medicines, drugs, doses, side effects, interactions
- anatomy, physiology, nutrition, mental health, public health, guidelines
- health advice, prevention, first aid, and medical terminology

OTHER includes:
- coding, mathematics, politics, sports, entertainment, travel, shopping
- finance, general chit-chat, jokes, or relationship advice not about health
- requests to write code, essays, or do homework
- anything clearly unrelated to health or medicine

If the message is ambiguous but could reasonably be about health, choose MEDICAL.
Reply with exactly one word: MEDICAL or OTHER."""


@lru_cache(maxsize=1)
def _get_scope_llm() -> ChatGroq:
    """Create the small scope-classifier model once."""
    return ChatGroq(
        model=SCOPE_MODEL,
        temperature=0,
        max_tokens=32,
        reasoning_effort="low",
        reasoning_format="hidden",
    )


@lru_cache(maxsize=256)
def _classify(question: str) -> str:
    """Return the classifier's raw one-word answer."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing")

    response = _get_scope_llm().invoke(
        [
            SystemMessage(content=_SCOPE_PROMPT),
            HumanMessage(content=question),
        ]
    )
    content = response.content
    if isinstance(content, list):
        content = " ".join(
            str(block.get("text", "")) if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content).strip().upper()


def is_medical_question(question: str) -> bool:
    """Return True when the question is allowed to reach the medical RAG."""
    if not MEDICAL_SCOPE_GUARD:
        return True

    question = (question or "").strip()
    if not question:
        return False

    try:
        result = _classify(question)
    except Exception as error:  # noqa: BLE001 - never break chat on classifier errors
        logger.warning("Medical scope check failed; allowing question: %s", error)
        return True

    if result.startswith("MEDICAL"):
        return True
    if result.startswith("OTHER"):
        return False

    logger.warning("Unexpected scope classifier answer %r; allowing question.", result)
    return True
