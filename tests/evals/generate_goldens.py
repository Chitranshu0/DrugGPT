"""Synthesize RAG goldens from local PDFs with the OpenRouter fallback chain.

Run from the repo root::

    python -m tests.evals.generate_goldens

Contexts are extracted directly from the PDFs with PyMuPDF and passed to
DeepEval's ``generate_goldens_from_contexts``. This avoids the expensive
1317-chunk scoring pass in ``generate_goldens_from_docs`` and fits the free-tier
request budget. Raw results go to gitignored ``data/evals/``; curate a small
subset into ``tests/evals/goldens.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.core.config import PROJECT_ROOT
from src.core.runtime import configure_runtime

configure_runtime()

# DeepEval's rich progress output contains glyphs cp1252 cannot encode.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pymupdf  # noqa: E402
from deepeval.synthesizer import Synthesizer  # noqa: E402
from deepeval.synthesizer.config import EvolutionConfig  # noqa: E402

from tests.evals.judge import get_judge  # noqa: E402

# Skip the 120 MB anatomy book; these are small enough to parse quickly.
DOCUMENTS = (
    "data/raw/Current Essentials of Medicine(1)(1).pdf",
    "data/raw/standard-treatment-guidelines.pdf",
    "data/raw/40mbs_medicalbooksstore_2017_essentials.pdf",
)


def _contexts_from_pdf(path: Path, max_chunks: int = 2, chunk_chars: int = 2000) -> list[str]:
    """Pull a few readable text blocks from the front of a PDF."""
    chunks: list[str] = []
    with pymupdf.open(path) as document:
        for page in document:
            text = " ".join(page.get_text().split())
            if len(text) < 300:
                continue
            chunks.extend(text[index : index + chunk_chars] for index in range(0, len(text), chunk_chars))
            if len(chunks) >= max_chunks:
                break
    return chunks[:max_chunks]


def main() -> None:
    judge = get_judge()
    synthesizer = Synthesizer(
        model=judge,
        async_mode=False,
        max_concurrent=4,
        evolution_config=EvolutionConfig(num_evolutions=0),
    )
    contexts: list[list[str]] = []
    source_files: list[str] = []
    for relative in DOCUMENTS:
        path = PROJECT_ROOT / relative
        chunks = _contexts_from_pdf(path)
        if chunks:
            contexts.append(chunks)
            source_files.append(relative)

    goldens = synthesizer.generate_goldens_from_contexts(
        contexts=contexts,
        source_files=source_files,
        max_goldens_per_context=1,
        include_expected_output=True,
    )
    output = PROJECT_ROOT / "data" / "evals" / "synthetic_goldens.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "input": golden.input,
            "expected_output": golden.expected_output,
            "context": list(golden.context or []),
        }
        for golden in goldens
    ]
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(payload)} synthetic goldens to {output}")


if __name__ == "__main__":
    main()
