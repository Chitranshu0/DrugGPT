"""Index the medical book PDFs into the Pinecone medical knowledge base.

Run from the project root:

    python -m scripts.ingest                  # full build
    python -m scripts.ingest --dry-run        # parse + chunk only
    python -m scripts.ingest --max-chunks 50  # small test build
    python -m scripts.ingest --reset          # clear namespace, then build

Pinecone embeds the text with NVIDIA llama-text-embed-v2 on the server.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# Keep optional ML libraries quiet during PDF ingestion.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

from backend.core.config import MEDICAL_BOOKS_DIR, PINECONE_NAMESPACE
from backend.ingestion.vector_db import ingest_medical_books

logger = logging.getLogger("drugppt.ingest")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the DrugGPT medical vector database in Pinecone.",
    )
    parser.add_argument(
        "--books-dir",
        default=MEDICAL_BOOKS_DIR,
        help=f"Folder containing the medical PDFs (default: {MEDICAL_BOOKS_DIR})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=f"Delete all documents in the {PINECONE_NAMESPACE!r} namespace first",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk the PDFs without sending anything to Pinecone",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=None,
        help="Only upload the first N documents (useful for a smoke test)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    logger.info("DrugGPT medical vector database build")
    logger.info("Books folder : %s", args.books_dir)
    logger.info("Namespace    : %s", PINECONE_NAMESPACE)
    if args.max_chunks is not None:
        logger.info("Chunk limit  : %s", args.max_chunks)
    if args.reset:
        logger.warning("Reset mode   : the namespace will be cleared first")

    try:
        stats = ingest_medical_books(
            pdf_directory=args.books_dir,
            reset=args.reset,
            dry_run=args.dry_run,
            max_chunks=args.max_chunks,
        )
    except Exception as error:  # noqa: BLE001 - shown as a friendly CLI error
        logger.error("Build failed: %s", error)
        return 1

    logger.info("Summary: %s", stats)
    if args.dry_run:
        logger.info("Dry run complete. Run again without --dry-run to upload.")
    else:
        logger.info("Build complete. Test it with: python -m test.vector_db_test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
