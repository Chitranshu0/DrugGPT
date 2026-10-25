"""LangGraph workflow for the medical RAG chatbot.

Flow: START -> medical_rag -> END
"""

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from backend.rag.generation import format_history, rag_tool
from backend.rag.state import MedicalState


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

    return {
        "context": result["context"],
        "answer": result["answer"],
        "messages": [AIMessage(content=result["answer"])],
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
