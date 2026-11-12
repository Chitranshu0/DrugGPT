"""Chroma retrieval that preserves document provenance."""

from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from druggpt.core.config import Settings, settings
from druggpt.core.models import DatabaseStatus, Evidence

COLLECTION_NAME = "medical_rag"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class VectorDatabaseNotReadyError(RuntimeError):
    """Raised when source-grounded chat is requested without an index."""


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


class MedicalRetriever:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def status(self) -> DatabaseStatus:
        client = chromadb.PersistentClient(path=str(self.settings.chroma_dir))
        try:
            collection = client.get_collection(COLLECTION_NAME)
        except chromadb.errors.NotFoundError:
            return DatabaseStatus(ready=False, chunks_indexed=0, documents_indexed=0)
        count = collection.count()
        metadatas = collection.get(include=["metadatas"])["metadatas"] or []
        document_count = len({str(metadata.get("source", "")) for metadata in metadatas})
        return DatabaseStatus(ready=count > 0, chunks_indexed=count, documents_indexed=document_count)

    def search(self, query: str) -> list[Evidence]:
        if not self.status().ready:
            raise VectorDatabaseNotReadyError(
                "The medical source index is not ready. Rebuild it before starting a chat."
            )
        store = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=str(self.settings.chroma_dir),
            embedding_function=get_embeddings(),
        )
        results = store.similarity_search_with_relevance_scores(query, k=self.settings.retrieval_k)
        evidence: list[Evidence] = []
        for document, score in results:
            metadata = document.metadata
            source_path = str(metadata.get("source", "Unknown source"))
            # Preserve useful citations when an existing local index was migrated from the legacy layout.
            migrated_path = self.settings.raw_documents_dir / Path(source_path).name
            if migrated_path.exists():
                source_path = str(migrated_path)
            page_value = metadata.get("page")
            evidence.append(
                Evidence(
                    content=document.page_content,
                    source_path=source_path,
                    source_title=Path(source_path).stem.replace("_", " ").title(),
                    page=(int(page_value) + 1) if page_value is not None else None,
                    score=max(0.0, min(1.0, float(score))),
                )
            )
        return evidence
