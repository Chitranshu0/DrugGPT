from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from state import MedicalState
from rag import rag_tool


# -----------------------------
# Checkpointer
# -----------------------------

memory = InMemorySaver()


# -----------------------------
# Nodes
# -----------------------------

def rag_node(state: MedicalState):

    result = rag_tool(
        state["question"]
    )

    return {
        "context": result["context"],
        "answer": result["answer"]
    }


# -----------------------------
# Graph Builder
# -----------------------------

builder = StateGraph(MedicalState)

builder.add_node(
    "medical_rag",
    rag_node
)

builder.add_edge(
    START,
    "medical_rag"
)

builder.add_edge(
    "medical_rag",
    END
)


# -----------------------------
# Compile Graph
# -----------------------------

graph = builder.compile(
    checkpointer=memory
)


# -----------------------------
# Local Test
# -----------------------------

if __name__ == "__main__":

    config = {
        "configurable": {
            "thread_id": "test_user"
        }
    }

    result = graph.invoke(
        {
            "question": "What is AIDS?"
        },
        config=config
    )

    print("\nAnswer:")
    print(result["answer"])