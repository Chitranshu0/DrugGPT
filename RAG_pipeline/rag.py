from dotenv import load_dotenv

from retriever import retrieve_context # type: ignore
from model import llm 
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_template("""
Context:
{context}

Question:
{question}

Answer:
""")

def rag_tool(question: str):
    context = retrieve_context(question)

    chain = prompt | llm

    response = chain.invoke({
        "context": context,
        "question": question
    })

    return {
        "context": context,
        "answer": response.content
    }