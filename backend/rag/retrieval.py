"""Turn a user question into relevant text from the medical books.

Pinecone stores the text and its 1024-dimensional NVIDIA embedding, so this
module only sends query text. No local embedding model is used.

Retrieval is hybrid by default:

1. Dense (semantic) search on ``chunk_text``.
2. BM25 full-text search on ``chunk_text`` + ``title``.
3. Reciprocal Rank Fusion (RRF) combines both rankings.

Hybrid search helps with both paraphrased questions and exact drug names.
Set ``RETRIEVAL_MODE=dense`` in ``.env`` to use semantic search only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Any, Iterable

from backend.core.config import (
    MEDICAL_DOMAIN,
    PINECONE_NAMESPACE,
    RERANK_MODEL,
    RETRIEVAL_FETCH_K,
    RETRIEVAL_MODE,
    RETRIEVAL_RERANK,
    RETRIEVAL_RRF_K,
    RETRIEVAL_TOP_K,
)
from backend.core.pinecone_client import get_pinecone_client, get_pinecone_index
from backend.core.text import display_title, normalize_text

logger = logging.getLogger(__name__)

INCLUDE_FIELDS = ["chunk_text", "title", "source", "page"]


@dataclass(frozen=True)
class RetrievedChunk:
    """One piece of medical text returned by Pinecone."""

    id: str
    text: str
    title: str
    source: str
    page: int | None
    score: float
    signals: tuple[str, ...] = ()


def _field(match: Any, name: str, default: Any = None) -> Any:
    """Read a field from a Pinecone search hit across SDK versions."""
    value = getattr(match, name, None)
    if value is not None:
        return value
    if hasattr(match, "to_dict"):
        return match.to_dict().get(name, default)
    return default


def _matches(response: Any) -> list[Any]:
    """Return search hits, tolerating an empty response from the SDK."""
    matches = getattr(response, "matches", None)
    return list(matches) if isinstance(matches, (list, tuple)) else []


def _search(index, query: str, top_k: int, score_by: list[dict[str, Any]]):
    """Run one Pinecone document search, always limited to medical content."""
    return index.documents.search(
        namespace=PINECONE_NAMESPACE,
        top_k=top_k,
        score_by=score_by,
        include_fields=INCLUDE_FIELDS,
        filter={"domain": {"$eq": MEDICAL_DOMAIN}},
    )


def _dense_search(index, query: str, top_k: int):
    """Semantic search using Pinecone's server-side embedding model."""
    return _search(
        index,
        query,
        top_k,
        [{"type": "embed", "fields": ["chunk_text"], "query": query}],
    )


def _text_search(index, query: str, top_k: int):
    """BM25 keyword search over the chunk text and book title."""
    return _search(
        index,
        query,
        top_k,
        [{"type": "text", "fields": ["chunk_text", "title"], "query": query}],
    )


def _reciprocal_rank_fusion(
    rankings: Iterable[list[str]],
    k: int = RETRIEVAL_RRF_K,
) -> dict[str, float]:
    """Fuse ranked document IDs using the standard RRF formula."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, document_id in enumerate(ranking, start=1):
            scores[document_id] = scores.get(document_id, 0.0) + 1.0 / (k + rank)
    return scores


def _to_chunk(match: Any, score: float, signals: tuple[str, ...]) -> RetrievedChunk:
    """Convert a Pinecone hit into a plain, typed object."""
    raw_page = _field(match, "page")
    try:
        page = int(raw_page) if raw_page is not None else None
    except (TypeError, ValueError):
        page = None

    return RetrievedChunk(
        id=str(_field(match, "_id", "")),
        text=normalize_text(str(_field(match, "chunk_text", "") or "")),
        title=display_title(str(_field(match, "title", "") or "")),
        source=str(_field(match, "source", "") or "").strip(),
        page=page,
        score=float(score),
        signals=signals,
    )


def _hybrid_search(index, query: str, top_k: int) -> list[RetrievedChunk]:
    """Run dense + keyword search and fuse the rankings."""
    fetch_k = max(top_k, RETRIEVAL_FETCH_K)
    responses: dict[str, Any] = {}
    errors: list[Exception] = []

    for name, search in (("dense", _dense_search), ("text", _text_search)):
        try:
            responses[name] = search(index, query, fetch_k)
        except Exception as error:  # noqa: BLE001 - use whichever signal works
            errors.append(error)
            logger.warning("%s search failed: %s", name, error)

    if not responses:
        raise RuntimeError("Both Pinecone searches failed") from errors[-1]

    rankings: list[list[str]] = []
    by_id: dict[str, Any] = {}
    signals: dict[str, list[str]] = {}

    for name, response in responses.items():
        ids: list[str] = []
        for match in _matches(response):
            document_id = str(_field(match, "_id", ""))
            if not document_id:
                continue
            ids.append(document_id)
            by_id.setdefault(document_id, match)
            signals.setdefault(document_id, []).append(name)
        rankings.append(ids)

    fused = _reciprocal_rank_fusion(rankings)
    ordered_ids = sorted(fused, key=fused.get, reverse=True)[:top_k]
    return [
        _to_chunk(by_id[document_id], fused[document_id], tuple(signals[document_id]))
        for document_id in ordered_ids
    ]


def _dense_only_search(index, query: str, top_k: int) -> list[RetrievedChunk]:
    """Semantic-only retrieval, kept as a fallback/debug option."""
    response = _dense_search(index, query, top_k)
    return [
        _to_chunk(match, float(_field(match, "_score", 0.0)), ("dense",))
        for match in _matches(response)
    ]


def _rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int,
) -> list[RetrievedChunk]:
    """Reorder candidate chunks with a cross-encoder reranker.

    Fused rankings are good at recall; a reranker is better at precision.
    The reranker sees the full question and each chunk together, which fixes
    cases where a keyword like a book title pulls in a weak chunk.
    """
    if not chunks:
        return []
    if not RETRIEVAL_RERANK or len(chunks) <= top_k:
        return chunks[:top_k]

    try:
        result = get_pinecone_client().inference.rerank(
            model=RERANK_MODEL,
            query=query,
            documents=[chunk.text for chunk in chunks],
            rank_fields=["text"],
            top_n=min(top_k, len(chunks)),
            return_documents=False,
        )
    except Exception as error:  # noqa: BLE001 - retrieval must still work
        logger.warning("Reranking failed; keeping fused order: %s", error)
        return chunks[:top_k]

    reranked: list[RetrievedChunk] = []
    for item in getattr(result, "data", None) or []:
        index = int(getattr(item, "index", -1))
        if 0 <= index < len(chunks):
            reranked.append(
                replace(chunks[index], score=float(getattr(item, "score", 0.0)))
            )

    return reranked or chunks[:top_k]


def retrieve_documents(
    query: str,
    k: int | None = None,
) -> list[RetrievedChunk]:
    """Return the most relevant medical chunks for a question."""
    query = (query or "").strip()
    if not query:
        return []

    top_k = max(1, k or RETRIEVAL_TOP_K)
    candidates = max(top_k, RETRIEVAL_FETCH_K)
    index = get_pinecone_index()

    mode = RETRIEVAL_MODE if RETRIEVAL_MODE in {"hybrid", "dense"} else "hybrid"
    if mode == "dense":
        chunks = _dense_only_search(index, query, candidates)
    else:
        chunks = _hybrid_search(index, query, candidates)

    chunks = _rerank(query, chunks, top_k)
    return [chunk for chunk in chunks if chunk.text]


def format_context(chunks: Iterable[RetrievedChunk]) -> str:
    """Format retrieved chunks with a source header for the LLM prompt."""
    blocks: list[str] = []
    for chunk in chunks:
        header = f"[Source: {chunk.title or 'Medical reference'}"
        if chunk.page:
            header += f", page {chunk.page}"
        header += "]"
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n".join(blocks)


def retrieve_context(query: str, k: int | None = None) -> str:
    """Return the top chunks joined into one context string.

    Kept as the small public helper used by older code and tests.
    """
    return format_context(retrieve_documents(query, k))
