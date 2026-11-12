"""Retrieval from the persistent local Chroma medical index."""

from langchain_chroma import Chroma

from vector_db import CHROMA_DIR, COLLECTION_NAME, get_database_status, get_embeddings


class VectorDatabaseNotReadyError(RuntimeError):
    """Raised when chat is requested before any medical documents are indexed."""


def ensure_database_ready() -> None:
    status = get_database_status()
    if not status["ready"]:
        raise VectorDatabaseNotReadyError(
            "The medical vector database has not been built yet. "
            "Use the Streamlit sidebar or POST /vector-db/rebuild first."
        )


def retrieve_context(query: str, k: int = 5) -> str:
    """Retrieve and combine the most relevant medical-document chunks."""
    ensure_database_ready()
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
        embedding_function=get_embeddings(),
    )
    documents = vectorstore.similarity_search(query=query, k=k)
    return "\n\n".join(document.page_content for document in documents)
