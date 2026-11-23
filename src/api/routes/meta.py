"""Liveness, discovery and OpenAI-compatible model endpoints."""

import logging

from fastapi import APIRouter

from src.api.metadata import API_VERSION
from src.rag.service import MedicalRAGService

logger = logging.getLogger("druggpt.api")


def make_router(service: MedicalRAGService) -> APIRouter:
    router = APIRouter(tags=["Meta"])

    @router.get("/", tags=["Meta"], summary="Service landing page")
    def root() -> dict[str, object]:
        """Human-friendly entry point that points at the useful URLs."""
        return {
            "service": "DrugGPT API",
            "version": API_VERSION,
            "status": "running",
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/health",
            "chat": "POST /conversations/{conversation_id}/messages",
        }

    @router.get("/health", tags=["Meta"], summary="Liveness probe")
    def health() -> dict[str, str]:
        """Return a constant payload while the process is accepting requests."""
        return {"status": "running", "mode": "local-development-only"}

    @router.get(
        "/v1/models",
        tags=["Meta"],
        include_in_schema=False,
        summary="OpenAI-compatible model discovery",
    )
    def models() -> dict[str, object]:
        """Minimal shim for external OpenAI-compatible probes (no code in this repo calls it)."""
        logger.debug("Model discovery probe answered for %s", service.settings.llm_model)
        return {
            "object": "list",
            "data": [{"id": service.settings.llm_model, "object": "model", "owned_by": "openrouter"}],
        }

    return router
