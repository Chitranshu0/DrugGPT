import os
from dotenv import load_dotenv

from retriever import retrieve_context # type: ignore
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

model = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)

prompt = ChatPromptTemplate.from_template("""
Context:
{context}

Question:
{question}

Answer:
""")

def rag_tool(question: str):
    context = retrieve_context(question)

    chain = prompt | model

    response = chain.invoke({
        "context": context,
        "question": question
    })

    return {
        "context": context,
        "answer": response.content
    }