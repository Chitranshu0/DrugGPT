"""One shared connection to the Pinecone medical index.

The index is a Pinecone *document index*. Pinecone stores ``chunk_text`` and
generates the 1024-dimensional NVIDIA embedding on the server, so this app
only sends and receives plain text.

Nothing connects to Pinecone at import time. The client and index are created
on first use.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from pinecone import Pinecone

from backend.core.config import (
    PINECONE_API_KEY,
    PINECONE_EMBED_DIMENSION,
    PINECONE_EMBED_METRIC,
    PINECONE_EMBED_MODEL,
    PINECONE_INDEX_HOST,
    PINECONE_INDEX_NAME,
)

logger = logging.getLogger(__name__)


class PineconeConfigurationError(RuntimeError):
    """Raised when the Pinecone index is missing or has the wrong schema."""


@lru_cache(maxsize=1)
def get_pinecone_client() -> Pinecone:
    """Create the Pinecone client once, on first use."""
    if not PINECONE_API_KEY:
        raise PineconeConfigurationError(
            "PINECONE_API_KEY is missing. Add it to .env and restart."
        )
    return Pinecone(api_key=PINECONE_API_KEY)


def get_index_host() -> str:
    """Return the index host, looking it up only when it is not configured."""
    if PINECONE_INDEX_HOST:
        return PINECONE_INDEX_HOST
    description = get_pinecone_client().describe_index(PINECONE_INDEX_NAME)
    return str(description.host).removeprefix("https://").rstrip("/")


@lru_cache(maxsize=1)
def get_pinecone_index():
    """Return a data-plane handle for the medical index."""
    return get_pinecone_client().Index(host=get_index_host())


def describe_medical_index() -> dict[str, Any]:
    """Return the control-plane description of the medical index."""
    return get_pinecone_client().describe_index(PINECONE_INDEX_NAME).to_dict()


def validate_index(verbose: bool = False) -> dict[str, Any]:
    """Check that the live index matches the schema this app expects.

    The schema is fixed when a Pinecone document index is created. Catching a
    mismatch here is much clearer than a 400 error halfway through ingestion.
    """
    info = describe_medical_index()
    fields = (info.get("schema") or {}).get("fields") or {}

    chunk_field = fields.get("chunk_text") or {}
    title_field = fields.get("title") or {}
    embed = chunk_field.get("embed") or {}

    problems: list[str] = []

    if not chunk_field:
        problems.append("missing the 'chunk_text' field")
    if not title_field:
        problems.append("missing the 'title' field")

    if embed.get("model") != PINECONE_EMBED_MODEL:
        problems.append(
            f"chunk_text.embed.model is {embed.get('model')!r}, "
            f"expected {PINECONE_EMBED_MODEL!r}"
        )
    if int(embed.get("dimension") or 0) != PINECONE_EMBED_DIMENSION:
        problems.append(
            f"chunk_text.embed.dimension is {embed.get('dimension')!r}, "
            f"expected {PINECONE_EMBED_DIMENSION}"
        )
    if embed.get("metric") != PINECONE_EMBED_METRIC:
        problems.append(
            f"chunk_text.embed.metric is {embed.get('metric')!r}, "
            f"expected {PINECONE_EMBED_METRIC!r}"
        )
    if not chunk_field.get("full_text_search"):
        problems.append("chunk_text full-text search is not enabled")
    if not title_field.get("full_text_search"):
        problems.append("title full-text search is not enabled")

    if problems:
        raise PineconeConfigurationError(
            "Pinecone index "
            f"{PINECONE_INDEX_NAME!r} does not match this project: "
            + "; ".join(problems)
        )

    if verbose:
        logger.info(
            "Index %s is ready: %s-dim %s embeddings + full-text search.",
            info.get("name"),
            embed.get("dimension"),
            embed.get("model"),
        )

    return info


def get_index_stats() -> dict[str, Any]:
    """Return vector/document counts for the medical index."""
    stats = get_pinecone_index().describe_index_stats()
    return stats.to_dict() if hasattr(stats, "to_dict") else dict(stats)
