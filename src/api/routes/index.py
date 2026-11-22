"""Vector index inspection and rebuild endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from src.core.models import DatabaseStatus
from src.rag.indexing import rebuild_index
from src.rag.service import MedicalRAGService

logger = logging.getLogger("druggpt.api")


def make_router(service: MedicalRAGService) -> APIRouter:
    router = APIRouter(prefix="/vector-db", tags=["Index"])

    @router.get(
        "/status",
        response_model=DatabaseStatus,
        tags=["Index"],
        summary="Inspect the local vector index",
    )
    def vector_database_status() -> DatabaseStatus:
        """Report whether the index is ready and how many documents/chunks it holds."""
        return service.retriever.status()

    @router.post(
        "/rebuild",
        tags=["Index"],
        summary="Rebuild the vector index from data/raw",
        description="Re-ingests every PDF in `data/raw` and replaces the local Chroma index.",
    )
    def rebuild_vector_database() -> dict[str, object]:
        logger.info(
            "Rebuilding vector index from PDFs in %s (this replaces the existing collection)",
            service.settings.raw_documents_dir,
        )
        try:
            result = rebuild_index(service.settings)
        except (FileNotFoundError, ValueError) as error:
            logger.warning("Vector index rebuild rejected (%s): %s", type(error).__name__, error)
            raise HTTPException(status_code=400, detail=str(error)) from error
        logger.info(
            "Vector index rebuilt successfully: %s chunks from %s documents",
            result.get("chunks_indexed"),
            result.get("documents_indexed"),
        )
        return result

    return router
