"""RAG step: add retrieved context to the question, then ask the LLM."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from backend.core.config import LLM_MODEL, LLM_TEMPERATURE
from backend.rag.retrieval import retrieve_context

PROMPT = ChatPromptTemplate.from_template(
    """
Context:
{context}

Question:
{question}

Answer:
"""
)

llm = ChatGroq(model=LLM_MODEL, temperature=LLM_TEMPERATURE)


def rag_tool(question: str) -> dict:
    """Retrieve context for the question and generate an answer."""
    context = retrieve_context(question)

    chain = PROMPT | llm
    response = chain.invoke({"context": context, "question": question})

    return {
        "context": context,
        "answer": response.content,
    }
