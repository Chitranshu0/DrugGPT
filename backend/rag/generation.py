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
from backend.rag.retrieval import retrieve_context

PROMPT = ChatPromptTemplate.from_template(
    """
You are a medical information assistant. Answer using the retrieved
context. If the context does not contain the answer, say so clearly.

Conversation so far:
{history}

Context:
{context}

Question:
{question}

Answer:
"""
)

llm = ChatGroq(model=LLM_MODEL, temperature=LLM_TEMPERATURE)


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
    """Retrieve context for the question and generate an answer."""
    context = retrieve_context(question)

    chain = PROMPT | llm
    response = chain.invoke(
        {
            "context": context,
            "history": history,
            "question": question,
        }
    )

    return {
        "context": context,
        "answer": response.content,
    }
