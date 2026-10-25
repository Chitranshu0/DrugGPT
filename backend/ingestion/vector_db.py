"""Build the Pinecone medical knowledge base from the medical book PDFs.

This file only handles ingestion:

    PDFs -> documents -> chunks -> Pinecone documents

Pinecone embeds each chunk with ``llama-text-embed-v2`` (1024 dimensions,
cosine) on the server. This project never loads a local embedding model.

Nothing runs automatically on import. Use ``python -m scripts.ingest``.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import warnings
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.core.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    MEDICAL_BOOKS_DIR,
    MEDICAL_DOMAIN,
    MIN_CHUNK_CHARS,
    PINECONE_NAMESPACE,
    UPSERT_BATCH_SIZE,
)
from backend.core.pinecone_client import (
    get_pinecone_index,
    validate_index,
)
from backend.core.text import display_title, normalize_text

warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger(__name__)

_DUPLICATE_SUFFIX_RE = re.compile(r"\(\d+\)")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_SPACES_RE = re.compile(r"[ \t]+")


def load_pdf_documents(pdf_directory: str | Path):
    """Load every PDF page in a folder as a LangChain document."""
    path = Path(pdf_directory)
    if not path.exists():
        raise FileNotFoundError(
            f"Medical books folder not found: {path}. "
            "Set MEDICAL_BOOKS_DIR in .env."
        )

    pdf_files = sorted(path.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in: {path}")

    logger.info("Found %d PDF file(s) in %s", len(pdf_files), path)
    documents: list[Document] = []

    for pdf_file in pdf_files:
        logger.info("Reading %s", pdf_file.name)
        with fitz.open(pdf_file) as pdf:
            total_pages = pdf.page_count
            for page_number, page in enumerate(pdf):
                text = page.get_text("text")
                if not text.strip():
                    continue
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": str(pdf_file),
                            "page": page_number,
                            "total_pages": total_pages,
                        },
                    )
                )

    if not documents:
        raise RuntimeError(f"No text was extracted from the PDFs in: {path}")
    return documents


def _clean_title(source_name: str) -> str:
    """Turn a PDF filename into a readable book title."""
    title = Path(source_name).stem
    title = _DUPLICATE_SUFFIX_RE.sub("", title)
    title = title.replace("_", " ").replace("-", " ")
    title = _SPACES_RE.sub(" ", title).strip()
    return display_title(title) or Path(source_name).stem


def _book_slug(source_name: str) -> str:
    """Create a short, stable prefix for document IDs."""
    slug = _SLUG_RE.sub("-", Path(source_name).stem.lower()).strip("-")
    return (slug[:60] or "book").strip("-")


def split_documents(documents):
    """Split long documents into overlapping, readable chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        add_start_index=True,
        separators=["\n\n", "\n", ". ", "; ", " ", ""],
    )
    return splitter.split_documents(documents)


def build_records(chunks) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convert LangChain chunks into Pinecone document records.

    IDs are deterministic, so running ingestion twice overwrites the same
    documents instead of creating duplicates.
    """
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    per_book: dict[str, int] = {}
    per_book_index: dict[str, int] = {}
    skipped = 0

    for chunk in chunks:
        text = normalize_text(chunk.page_content)
        if len(text) < MIN_CHUNK_CHARS:
            skipped += 1
            continue

        metadata = chunk.metadata or {}
        source = str(metadata.get("source") or metadata.get("file_path") or "unknown.pdf")
        source_name = Path(source).name
        page = int(metadata.get("page") or 0) + 1  # PyMuPDF pages are 0-based.
        title = _clean_title(source_name)

        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
        document_id = f"{_book_slug(source_name)}-p{page}-{digest}"
        if document_id in seen_ids:
            skipped += 1
            continue
        seen_ids.add(document_id)

        chunk_index = per_book_index.get(source_name, 0)
        per_book_index[source_name] = chunk_index + 1

        records.append(
            {
                "_id": document_id,
                "chunk_text": text,
                "title": title,
                "source": source_name,
                "page": page,
                "chunk_index": chunk_index,
                "domain": MEDICAL_DOMAIN,
            }
        )
        per_book[source_name] = per_book.get(source_name, 0) + 1

    stats = {
        "books": per_book,
        "records": len(records),
        "skipped": skipped,
    }
    return records, stats


def reset_namespace() -> None:
    """Delete every document in the configured namespace."""
    index = get_pinecone_index()
    stats = index.describe_index_stats()
    namespaces = getattr(stats, "namespaces", {}) or {}

    # A brand-new index has no namespaces at all. Deleting from one would
    # return a 404, so treat "already empty" as success.
    if isinstance(namespaces, dict) and PINECONE_NAMESPACE not in namespaces:
        logger.info("Namespace %r is already empty.", PINECONE_NAMESPACE)
        return

    index.documents.delete(namespace=PINECONE_NAMESPACE, delete_all=True)
    logger.info("Cleared namespace %r.", PINECONE_NAMESPACE)


def _upsert_batch(index, batch: list[dict[str, Any]], attempts: int = 3) -> tuple[int, int]:
    """Upsert one batch, retrying a few times on temporary failures."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = index.documents.upsert(
                namespace=PINECONE_NAMESPACE,
                documents=batch,
            )
            tokens = getattr(getattr(response, "usage", None), "embed_total_tokens", 0)
            return int(response.upserted_count), int(tokens or 0)
        except Exception as error:  # noqa: BLE001 - retried below
            last_error = error
            if attempt == attempts:
                break
            wait = attempt * 2
            logger.warning(
                "Batch upsert failed (attempt %d/%d): %s. Retrying in %ss.",
                attempt,
                attempts,
                error,
                wait,
            )
            time.sleep(wait)

    raise RuntimeError(f"Pinecone upsert failed after {attempts} attempts") from last_error


def ingest_medical_books(
    pdf_directory: str | Path = MEDICAL_BOOKS_DIR,
    *,
    reset: bool = False,
    dry_run: bool = False,
    max_chunks: int | None = None,
) -> dict[str, Any]:
    """Load PDFs, split them, and upload the chunks to Pinecone.

    Args:
        pdf_directory: Folder containing the medical book PDFs.
        reset: Delete the namespace contents before uploading.
        dry_run: Parse and chunk only; do not touch Pinecone.
        max_chunks: Optional cap, useful for a small test build.
    """
    logger.info("Loading PDFs from %s", pdf_directory)
    documents = load_pdf_documents(pdf_directory)

    logger.info("Splitting documents into chunks...")
    chunks = split_documents(documents)
    records, stats = build_records(chunks)

    if max_chunks is not None:
        records = records[: max(0, max_chunks)]
        stats["records"] = len(records)
        stats["capped_at"] = max_chunks

    logger.info(
        "Prepared %d chunks -> %d documents (skipped %d empty/duplicate chunks).",
        len(chunks),
        len(records),
        stats["skipped"],
    )
    for book, count in stats["books"].items():
        logger.info("  %-55s %5d chunks", book, count)

    if dry_run:
        logger.info("Dry run: nothing was sent to Pinecone.")
        return stats

    if not records:
        raise RuntimeError("No usable text chunks were produced.")

    validate_index(verbose=True)
    index = get_pinecone_index()

    if reset:
        reset_namespace()

    total_upserted = 0
    total_tokens = 0
    batch_size = max(1, min(UPSERT_BATCH_SIZE, 96))
    total_batches = (len(records) + batch_size - 1) // batch_size

    for number, start in enumerate(range(0, len(records), batch_size), start=1):
        batch = records[start : start + batch_size]
        upserted, tokens = _upsert_batch(index, batch)
        total_upserted += upserted
        total_tokens += tokens
        logger.info(
            "Batch %d/%d: %d documents (total %d, %d embedding tokens).",
            number,
            total_batches,
            upserted,
            total_upserted,
            total_tokens,
        )

    stats.update(
        {
            "upserted": total_upserted,
            "embedding_tokens": total_tokens,
            "namespace": PINECONE_NAMESPACE,
        }
    )
    logger.info(
        "Done. %d documents are in namespace %r. Pinecone may need up to a "
        "minute before every document is searchable.",
        total_upserted,
        PINECONE_NAMESPACE,
    )
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ingest_medical_books()
