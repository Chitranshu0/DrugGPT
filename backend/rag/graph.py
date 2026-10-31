"""LangGraph workflow for the medical RAG chatbot.

Flow: START -> medical_rag -> END
"""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from backend.rag.generation import rag_tool
from backend.rag.state import MedicalState


def rag_node(state: MedicalState) -> dict:
    """Run the RAG step and store its results in the graph state."""
    result = rag_tool(state["question"])

    return {
        "context": result["context"],
        "answer": result["answer"],
    }


def create_graph():
    """Build and compile the chatbot graph."""
    builder = StateGraph(MedicalState)

    builder.add_node("medical_rag", rag_node)
    builder.add_edge(START, "medical_rag")
    builder.add_edge("medical_rag", END)

    return builder.compile(checkpointer=InMemorySaver())


# The compiled graph that the API uses.
graph = create_graph()
