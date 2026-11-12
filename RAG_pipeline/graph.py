from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

from state import MedicalState
from rag import rag_tool

from model import llm 


def chat_node(state: MedicalState):
    '''
    This is main node which doing the chat operations. 
    '''
    result = rag_tool(state["question"])

    return {
        "context": result["context"],
        "answer": result["answer"]
    }

def rag_node(state: MedicalState):
    """Run retrieval-augmented generation for the incoming medical question."""
    result = rag_tool(state["question"])

    return {
        "context": result["context"],
        "answer": result["answer"]
    }


conn = sqlite3.connect(database="medicine_chat.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

builder = StateGraph(MedicalState)

builder.add_node("medical_rag", rag_node)

builder.add_edge(START, "medical_rag")
builder.add_edge("medical_rag", END)

graph = builder.compile(checkpointer=checkpointer)
