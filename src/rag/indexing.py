"""Source document ingestion and Chroma index lifecycle."""

from __future__ import annotations

import logging
import re

import chromadb
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.config import Settings, settings
from src.core.runtime import configure_runtime
from src.rag.retrieval import (
    COLLECTION_METADATA,
    COLLECTION_NAME,
    get_embeddings,
    invalidate_caches,
    normalize_source_path,
)

configure_runtime()

logger = logging.getLogger("druggpt.rag.indexing")

# Front matter and reference pages carry almost no retrievable medical content,
# yet the original corpus was dominated by them (dedications, indexes, TOCs).
_LOW_VALUE_PATTERN = re.compile(
    r"^\s*(dedicat|in memory of|table of contents|contents\b|index\b|bibliography|"
    r"acknowledg|list of (tables|figures)|abbreviations|foreword|preface)",
    re.IGNORECASE,
)
_INDEX_LINE = re.compile(r"\b\d{2,4}\b")


def is_low_value_chunk(document: Document, app_settings: Settings) -> bool:
    """Return True for pages that pollute retrieval rather than help it."""
    page = document.metadata.get("page")
    if page is not None and int(page) < app_settings.skip_front_matter_pages:
        return True
    text = document.page_content.strip()
    if len(text) < app_settings.min_chunk_chars:
        return True
    if _LOW_VALUE_PATTERN.match(text):
        return True
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        index_lines = sum(1 for line in lines if len(line) < 90 and _INDEX_LINE.search(line))
        if index_lines / len(lines) > 0.4:
            return True
    words = re.findall(r"\w+", text)
    if words and sum(1 for word in words if any(char.isdigit() for char in word)) / len(words) > 0.45:
        return True
    return False


def _cap_per_document(chunks: list[Document], maximum: int) -> tuple[list[Document], int]:
    """Sample large documents evenly so one textbook cannot dominate results."""
    grouped: dict[str, list[int]] = {}
    for position, chunk in enumerate(chunks):
        grouped.setdefault(str(chunk.metadata.get("source", "")), []).append(position)
    keep: set[int] = set()
    for positions in grouped.values():
        if len(positions) <= maximum:
            keep.update(positions)
            continue
        if maximum == 1:
            keep.add(positions[0])
            continue
        last = len(positions) - 1
        keep.update(positions[round(index * last / (maximum - 1))] for index in range(maximum))
    return [chunk for position, chunk in enumerate(chunks) if position in keep], len(chunks) - len(keep)


def rebuild_index(app_settings: Settings = settings) -> dict[str, object]:
    pdf_paths = sorted(app_settings.raw_documents_dir.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in {app_settings.raw_documents_dir}")
    documents = DirectoryLoader(
        path=str(app_settings.raw_documents_dir), glob="*.pdf", loader_cls=PyMuPDFLoader
    ).load()
    if not documents:
        raise ValueError("No document pages could be loaded from the supplied PDFs.")

    kept_pages = [document for document in documents if not is_low_value_chunk(document, app_settings)]
    dropped_pages = len(documents) - len(kept_pages)
    if not kept_pages:
        raise ValueError("Every page was filtered out as low-value content; check the index quality settings.")

    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150).split_documents(kept_pages)
    if not chunks:
        raise ValueError("The PDF files did not produce any indexable text chunks.")

    chunks, dropped_cap = _cap_per_document(chunks, app_settings.max_chunks_per_document)
    for chunk in chunks:
        source = str(chunk.metadata.get("source", ""))
        relative = normalize_source_path(source, app_settings)
        chunk.metadata["source"] = relative
        chunk.metadata["file_path"] = relative

    per_document: dict[str, int] = {}
    for chunk in chunks:
        source = str(chunk.metadata.get("source", ""))
        per_document[source] = per_document.get(source, 0) + 1

    app_settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(app_settings.chroma_dir))
    try:
        client.delete_collection(COLLECTION_NAME)
    except chromadb.errors.NotFoundError:
        pass
    invalidate_caches()

    Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        collection_name=COLLECTION_NAME,
        persist_directory=str(app_settings.chroma_dir),
        collection_metadata=COLLECTION_METADATA,
    )
    invalidate_caches()

    logger.info(
        "Index rebuilt: %d chunks from %d documents (%d low-value pages and %d surplus chunks dropped)",
        len(chunks),
        len(pdf_paths),
        dropped_pages,
        dropped_cap,
    )
    return {
        "documents_indexed": len(pdf_paths),
        "chunks_indexed": len(chunks),
        "chunks_dropped": dropped_pages + dropped_cap,
        "per_document": per_document,
        "message": "Index rebuilt.",
    }
