"""The shared state that moves between LangGraph nodes."""

<<<<<<< HEAD
from typing import TypedDict
=======
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
>>>>>>> fix/RAG


class MedicalState(TypedDict):
    """Everything the chatbot graph needs to produce an answer.

    question: what the user asked.
    context:  the text we retrieved from the medical books.
    answer:   the final answer produced by the LLM.
<<<<<<< HEAD
=======
    messages: the full conversation. The add_messages reducer appends new
              messages instead of replacing the existing list, so the
              checkpointer can reload the whole thread.
>>>>>>> fix/RAG
    """

    question: str
    context: str
    answer: str
<<<<<<< HEAD
=======
    messages: Annotated[list[AnyMessage], add_messages]
>>>>>>> fix/RAG
