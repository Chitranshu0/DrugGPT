"""Creation and management of the local Chroma medical-document index."""

from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent
MEDICAL_BOOKS_DIR = BASE_DIR / "Medical Books"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "medical_rag"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_embeddings() -> HuggingFaceBgeEmbeddings:
    """Create the embedding model used for both indexing and retrieval."""
    return HuggingFaceBgeEmbeddings(model_name=EMBEDDING_MODEL)


def get_database_status() -> dict[str, int | bool]:
    """Return whether the local collection exists and how many chunks it has."""
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except chromadb.errors.NotFoundError:
        return {"ready": False, "chunks_indexed": 0}

    return {"ready": collection.count() > 0, "chunks_indexed": collection.count()}


def rebuild_vector_database() -> dict[str, int | str]:
    """Replace the collection with chunks from every PDF in Medical Books."""
    pdf_paths = sorted(MEDICAL_BOOKS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in {MEDICAL_BOOKS_DIR}")

    loader = DirectoryLoader(
        path=str(MEDICAL_BOOKS_DIR),
        glob="*.pdf",
        loader_cls=PyMuPDFLoader,
    )
    documents = loader.load()
    if not documents:
        raise ValueError("No document pages could be loaded from the PDF files.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(documents)
    if not chunks:
        raise ValueError("The PDF files did not produce any indexable text chunks.")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except chromadb.errors.NotFoundError:
        pass

    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
    )

    return {
        "documents_indexed": len(pdf_paths),
        "chunks_indexed": len(chunks),
        "message": "ChromaDB was rebuilt from the medical PDF files.",
    }
