"""Turn a user question into relevant text from the medical books."""

from langchain_pinecone import PineconeVectorStore

from backend.core.config import PINECONE_API_KEY, PINECONE_INDEX_NAME
from backend.core.embeddings import get_embedding


def get_vectorstore() -> PineconeVectorStore:
    """Connect to the existing Pinecone index.

    The connection is created on demand (not at import time), so importing
    this file never makes a network call.
    """
    return PineconeVectorStore(
        index_name=PINECONE_INDEX_NAME,
        embedding=get_embedding(),
        pinecone_api_key=PINECONE_API_KEY,
    )


def retrieve_context(query: str, k: int = 5) -> str:
    """Return the top `k` matching chunks joined into one context string."""
    vectorstore = get_vectorstore()
    documents = vectorstore.similarity_search(query=query, k=k)
    return "\n\n".join(document.page_content for document in documents)
