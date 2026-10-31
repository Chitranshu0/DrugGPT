"""LangGraph workflow for the medical RAG chatbot.

Flow: START -> medical_rag -> END
"""

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from backend.rag.generation import (
    TOOL_NAME,
    TOOL_TITLE,
    format_history,
    rag_tool,
)
from backend.rag.state import MedicalState


def _tool_summary(sources: list[dict]) -> str:
    """Describe what the retrieval tool found for the UI."""
    count = len(sources)
    if count == 0:
        return "No matching passages found"
    if count == 1:
        return "Found 1 relevant passage"
    return f"Found {count} relevant passages"


def rag_node(state: MedicalState) -> dict:
    """Run the RAG step and store its results in the graph state."""
    messages = state.get("messages", [])

    # The current question is already in messages; keep it out of the
    # prompt history so it is not shown twice.
    prior_messages = (
        messages[:-1]
        if messages and messages[-1].type == "human"
        else messages
    )

    result = rag_tool(
        state["question"],
        history=format_history(prior_messages),
    )

    sources = result["sources"]

    # Persist the tool call and sources on the assistant message so the UI
    # can render the same Claude-style cards when a thread is reopened.
    tool_call = {
        "name": TOOL_NAME,
        "title": TOOL_TITLE,
        "input": {"question": state["question"]},
        "status": "completed",
        "summary": _tool_summary(sources),
    }
    message = AIMessage(
        content=result["answer"],
        additional_kwargs={
            "sources": sources,
            "ui_tool_calls": [tool_call],
        },
    )

    return {
        "context": result["context"],
        "answer": result["answer"],
        "sources": sources,
        "messages": [message],
    }


def create_graph(checkpointer=None):
    """Build and compile the chatbot graph.

    The FastAPI app passes an AsyncSqliteSaver so conversations survive a
    restart. Passing no checkpointer keeps this usable by scripts and tests.
    """
    builder = StateGraph(MedicalState)

    builder.add_node("medical_rag", rag_node)
    builder.add_edge(START, "medical_rag")
    builder.add_edge("medical_rag", END)

    return builder.compile(checkpointer=checkpointer)
