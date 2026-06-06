from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from state import MedicalState
from rag import rag_tool


def rag_node(state: MedicalState):
    result = rag_tool(state["question"])

    return {
        "context": result["context"],
        "answer": result["answer"]
    }


checkpointer = InMemorySaver()

builder = StateGraph(MedicalState)

builder.add_node("medical_rag", rag_node)

builder.add_edge(START, "medical_rag")
builder.add_edge("medical_rag", END)

graph = builder.compile(
    checkpointer=checkpointer
)