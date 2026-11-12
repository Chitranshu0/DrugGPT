"""Source document ingestion and Chroma index lifecycle."""

import chromadb
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from druggpt.core.config import Settings, settings
from druggpt.rag.retrieval import COLLECTION_NAME, get_embeddings


def rebuild_index(app_settings: Settings = settings) -> dict[str, int | str]:
    pdf_paths = sorted(app_settings.raw_documents_dir.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in {app_settings.raw_documents_dir}")
    documents = DirectoryLoader(
        path=str(app_settings.raw_documents_dir), glob="*.pdf", loader_cls=PyMuPDFLoader
    ).load()
    if not documents:
        raise ValueError("No document pages could be loaded from the supplied PDFs.")
    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150).split_documents(documents)
    if not chunks:
        raise ValueError("The PDF files did not produce any indexable text chunks.")
    app_settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(app_settings.chroma_dir))
    try:
        client.delete_collection(COLLECTION_NAME)
    except chromadb.errors.NotFoundError:
        pass
    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=COLLECTION_NAME,
        persist_directory=str(app_settings.chroma_dir),
    )
    return {"documents_indexed": len(pdf_paths), "chunks_indexed": len(chunks), "message": "Index rebuilt."}
