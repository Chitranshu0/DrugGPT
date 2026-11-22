"""Chroma retrieval that preserves document provenance and score semantics."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src.core.config import PROJECT_ROOT, Settings, settings
from src.core.models import DatabaseStatus, Evidence
from src.core.runtime import configure_runtime

configure_runtime()

COLLECTION_NAME = "medical_rag"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Cosine space plus a schema marker lets us reject incompatible older indexes.
COLLECTION_METADATA = {"hnsw:space": "cosine", "schema_version": 2}
INDEX_SCHEMA_VERSION = 2

logger = logging.getLogger("druggpt.rag.retrieval")


class VectorDatabaseNotReadyError(RuntimeError):
    """Raised when source-grounded chat is requested without a usable index."""


@lru_cache(maxsize=4)
def get_embeddings(model_name: str = EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    """One normalized embedder per process.

    Normalizing makes cosine distance well-defined in [0, 2] and, crucially,
    makes ``1 - distance`` a true cosine similarity in [-1, 1] that we can
    clamp and compare against the configured threshold.
    """
    return HuggingFaceEmbeddings(
        model_name=model_name,
        encode_kwargs={"normalize_embeddings": True},
    )


@lru_cache(maxsize=4)
def _get_client(chroma_dir: str) -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=chroma_dir)


@lru_cache(maxsize=4)
def _get_store(chroma_dir: str) -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=chroma_dir,
        embedding_function=get_embeddings(),
    )


def invalidate_caches() -> None:
    """Drop cached clients/stores after an index rebuild.

    Without this, a rebuilt collection would be shadowed by the old cached
    ``Chroma`` object and searches would still hit deleted embeddings. The
    embedding model itself is static and intentionally kept warm.
    """
    _get_client.cache_clear()
    _get_store.cache_clear()


def cosine_relevance(distance: float) -> float:
    """Convert a Chroma cosine distance into a clamped [0, 1] similarity."""
    return max(0.0, min(1.0, 1.0 - float(distance)))


def normalize_source_path(source: str, app_settings: Settings) -> str:
    """Return a portable, repo-relative citation path.

    Absolute paths are made relative to the repository or data directory so
    citations never leak local filesystem details.
    """
    raw = Path(source)
    if not raw.is_absolute():
        return raw.as_posix()
    candidates = (PROJECT_ROOT, app_settings.data_dir.parent)
    for root in candidates:
        try:
            return raw.resolve().relative_to(root.resolve()).as_posix()
        except (ValueError, OSError):
            continue
    return raw.name


class MedicalRetriever:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def status(self) -> DatabaseStatus:
        try:
            client = _get_client(str(self.settings.chroma_dir))
            collection = client.get_collection(COLLECTION_NAME)
            count = collection.count()
            metadatas = collection.get(include=["metadatas"])["metadatas"] or []
            document_count = len({str(metadata.get("source", "")) for metadata in metadatas})
            metadata = collection.metadata or {}
            stored_version = metadata.get("schema_version")
            metric = metadata.get("hnsw:space", "l2")
            needs_rebuild = stored_version != INDEX_SCHEMA_VERSION or metric != "cosine"
            message = None
            if needs_rebuild:
                message = (
                    f"Index schema is outdated (space={metric}, version={stored_version}); "
                    "rebuild it from the Admin page or POST /vector-db/rebuild to use cosine similarity."
                )
                logger.warning(message)
            return DatabaseStatus(
                ready=count > 0 and not needs_rebuild,
                chunks_indexed=count,
                documents_indexed=document_count,
                schema_version=stored_version,
                distance_metric=metric,
                needs_rebuild=needs_rebuild,
                message=message,
            )
        except chromadb.errors.NotFoundError:
            logger.info(
                "Vector index not built yet at %s - status=not ready (POST /vector-db/rebuild to create it)",
                self.settings.chroma_dir,
            )
            return DatabaseStatus(ready=False, chunks_indexed=0, documents_indexed=0)
        except Exception as error:  # corrupt store, bad permissions, locked file, …
            logger.warning(
                "Vector index at %s is unreadable (%s: %s). "
                "Chat will fall back to general education until it is rebuilt via "
                "POST /vector-db/rebuild.",
                self.settings.chroma_dir,
                type(error).__name__,
                error,
            )
            return DatabaseStatus(ready=False, chunks_indexed=0, documents_indexed=0)

    def search(self, query: str) -> list[Evidence]:
        index_status = self.status()
        if not index_status.ready:
            detail = index_status.message or "The medical source index is not ready. Rebuild it before starting a chat."
            raise VectorDatabaseNotReadyError(detail)
        try:
            store = _get_store(str(self.settings.chroma_dir))
            # Use raw distances; LangChain's relevance helper is version-dependent
            # and logs full documents for out-of-range scores.
            results = store.similarity_search_with_score(query, k=self.settings.retrieval_k)
        except Exception as error:  # a corrupt/locked index must not crash the chat
            logger.warning(
                "Vector search failed (%s: %s) - chat will fall back to general education",
                type(error).__name__,
                error,
            )
            raise VectorDatabaseNotReadyError("The medical source index could not be read.") from error

        evidence: list[Evidence] = []
        for document, distance in results:
            metadata = document.metadata
            source_path = str(metadata.get("source", "Unknown source"))
            # Prefer the current file on disk when an index still stores an older path.
            migrated_path = self.settings.raw_documents_dir / Path(source_path).name
            if migrated_path.exists():
                source_path = str(migrated_path)
            source_path = normalize_source_path(source_path, self.settings)
            page_value = metadata.get("page")
            evidence.append(
                Evidence(
                    content=document.page_content,
                    source_path=source_path,
                    source_title=Path(source_path).stem.replace("_", " ").title(),
                    page=(int(page_value) + 1) if page_value is not None else None,
                    score=cosine_relevance(distance),
                )
            )
        top = f"{evidence[0].score:.3f}" if evidence else "n/a"
        logger.info(
            "Vector search complete: %d candidates (top cosine similarity=%s, threshold=%.2f)",
            len(evidence),
            top,
            self.settings.relevance_threshold,
        )
        return evidence
