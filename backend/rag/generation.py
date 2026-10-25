"""RAG step: add retrieved context to the question, then ask the LLM."""

from collections.abc import Sequence

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.core.config import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    MEMORY_WINDOW_MESSAGES,
)
from backend.rag.retrieval import format_context, retrieve_documents
from backend.rag.scope import REFUSAL_ANSWER, is_medical_question

NO_CONTEXT_ANSWER = (
    "I could not find this in the medical references available to me. "
    "Please try rephrasing the question or ask about a related medical topic."
)

SYSTEM_PROMPT = """You are DrugGPT, a medical information assistant.

SCOPE RULES (must always be followed):
1. Only answer questions about medicine, health, diseases, symptoms, drugs,
   doses, tests, treatment, nutrition, mental health, or public health.
2. If the question is not medical, politely refuse using this exact sentence:
   "I can only help with medical and health-related questions."
3. If the retrieved context does not contain the answer, say that you could
   not find it in the provided medical references. Never invent facts,
   medicine names, doses, or guideline numbers.
4. Use the retrieved context as the main source of truth. You may explain
   medical terms, but do not add treatment claims that the context does not
   support.
5. Cite the source at the end of a sentence when you use it, for example:
   (Current Essentials of Medicine, page 214).
6. Use simple English. Prefer short paragraphs or bullet points.
7. For urgent symptoms, dosing questions, pregnancy, children, or serious
   side effects, add a short note telling the user to contact a doctor or
   emergency service.

If no context is supplied, do not answer from memory. Say that the answer was
not found in the medical references."""

HUMAN_PROMPT = """Conversation so far:
{history}

Retrieved medical context:
{context}

Question:
{question}

Answer:"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", HUMAN_PROMPT),
    ]
)

llm = ChatGroq(
    model=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    max_tokens=1024,
)


def _message_text(message: BaseMessage) -> str:
    """Return plain text from a message, ignoring non-text content blocks."""
    if isinstance(message.content, str):
        return message.content

    parts: list[str] = []
    for block in message.content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            text = block.get("text")
            if text:
                parts.append(str(text))
    return " ".join(parts)


def format_history(messages: Sequence[BaseMessage]) -> str:
    """Format the recent conversation for the prompt."""
    recent = list(messages)[-MEMORY_WINDOW_MESSAGES:]
    if not recent:
        return "(no previous messages)"

    lines: list[str] = []
    for message in recent:
        role = "User" if message.type == "human" else "Assistant"
        lines.append(f"{role}: {_message_text(message)}")

    return "\n".join(lines)


def rag_tool(question: str, history: str = "(no previous messages)") -> dict:
    """Check the medical scope, retrieve context, and generate an answer."""
    if not is_medical_question(question):
        return {
            "context": "",
            "answer": REFUSAL_ANSWER,
            "sources": [],
        }

    chunks = retrieve_documents(question)
    if not chunks:
        return {
            "context": "",
            "answer": NO_CONTEXT_ANSWER,
            "sources": [],
        }

    context = format_context(chunks)
    response = (PROMPT | llm).invoke(
        {
            "context": context,
            "history": history,
            "question": question,
        }
    )

    sources: list[dict] = []
    seen_sources: set[tuple[str, int | None]] = set()
    for chunk in chunks:
        key = (chunk.title, chunk.page)
        if key in seen_sources:
            continue
        seen_sources.add(key)
        sources.append(
            {
                "title": chunk.title,
                "source": chunk.source,
                "page": chunk.page,
                "score": round(chunk.score, 6),
                "signals": list(chunk.signals),
            }
        )

    return {
        "context": context,
        "answer": _message_text(response),
        "sources": sources,
    }
