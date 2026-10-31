"""The shared state that moves between LangGraph nodes."""

from typing import TypedDict


class MedicalState(TypedDict):
    """Everything the chatbot graph needs to produce an answer.

    question: what the user asked.
    context:  the text we retrieved from the medical books.
    answer:   the final answer produced by the LLM.
    """

    question: str
    context: str
    answer: str
