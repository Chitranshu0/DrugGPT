"""Build the Pinecone vector store from the medical book PDFs.

This file only handles ingestion:
    PDFs -> documents -> chunks -> embeddings -> Pinecone

Nothing runs automatically on import. Use scripts/ingest.py to start it.
"""

import warnings

from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_pinecone import PineconeVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

from backend.core.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MEDICAL_BOOKS_DIR,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
)
from backend.core.embeddings import get_embedding

warnings.filterwarnings("ignore")

# all-MiniLM-L6-v2 produces 384-dimensional vectors.
EMBEDDING_DIMENSION = 384


def load_pdf_documents(pdf_directory: str):
    """Load every PDF in a folder as LangChain documents."""
    loader = DirectoryLoader(
        path=pdf_directory,
        glob="*.pdf",
        loader_cls=PyMuPDFLoader,
    )
    return loader.load()


def split_documents(documents):
    """Split long documents into smaller, overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def ensure_index_exists(pinecone_client: Pinecone, index_name: str):
    """Create the Pinecone index if it does not exist yet."""
    existing_indexes = pinecone_client.list_indexes().names()
    if index_name in existing_indexes:
        return

    pinecone_client.create_index(
        name=index_name,
        dimension=EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )


def ingest_medical_books(pdf_directory: str = MEDICAL_BOOKS_DIR):
    """Load PDFs, split them, and upload the chunks to Pinecone."""
    documents = load_pdf_documents(pdf_directory)
    chunks = split_documents(documents)

    pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
    ensure_index_exists(pinecone_client, PINECONE_INDEX_NAME)

    vectorstore = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=get_embedding(),
        index_name=PINECONE_INDEX_NAME,
        pinecone_api_key=PINECONE_API_KEY,
    )
    return vectorstore


if __name__ == "__main__":
    ingest_medical_books()
