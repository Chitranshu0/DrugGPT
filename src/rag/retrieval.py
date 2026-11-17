"""Chroma retrieval that preserves document provenance."""

import logging
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.core.config import Settings, settings
from src.core.models import DatabaseStatus, Evidence

COLLECTION_NAME = "medical_rag"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

logger = logging.getLogger("druggpt.rag.retrieval")


class VectorDatabaseNotReadyError(RuntimeError):
    """Raised when source-grounded chat is requested without an index."""


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


class MedicalRetriever:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def status(self) -> DatabaseStatus:
        try:
            client = chromadb.PersistentClient(path=str(self.settings.chroma_dir))
            collection = client.get_collection(COLLECTION_NAME)
            count = collection.count()
            metadatas = collection.get(include=["metadatas"])["metadatas"] or []
            document_count = len({str(metadata.get("source", "")) for metadata in metadatas})
            return DatabaseStatus(ready=count > 0, chunks_indexed=count, documents_indexed=document_count)
        except chromadb.errors.NotFoundError:
            logger.info(
                "Vector index not built yet at %s - status=not ready (run `python -m src.cli index`)",
                self.settings.chroma_dir,
            )
            return DatabaseStatus(ready=False, chunks_indexed=0, documents_indexed=0)
        except Exception as error:  # corrupt store, bad permissions, locked file, …
            logger.warning(
                "Vector index at %s is unreadable (%s: %s). "
                "Chat will fall back to general education until it is rebuilt with "
                "`python -m src.cli index`.",
                self.settings.chroma_dir,
                type(error).__name__,
                error,
            )
            return DatabaseStatus(ready=False, chunks_indexed=0, documents_indexed=0)

    def search(self, query: str) -> list[Evidence]:
        if not self.status().ready:
            raise VectorDatabaseNotReadyError(
                "The medical source index is not ready. Rebuild it before starting a chat."
            )
        try:
            store = Chroma(
                collection_name=COLLECTION_NAME,
                persist_directory=str(self.settings.chroma_dir),
                embedding_function=get_embeddings(),
            )
            results = store.similarity_search_with_relevance_scores(query, k=self.settings.retrieval_k)
        except Exception as error:  # a corrupt/locked index must not crash the chat
            logger.warning(
                "Vector search failed (%s: %s) - chat will fall back to general education",
                type(error).__name__,
                error,
            )
            raise VectorDatabaseNotReadyError("The medical source index could not be read.") from error
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
        logger.info("Vector search complete: %d candidate chunks returned for scoring", len(evidence))
        return evidence
