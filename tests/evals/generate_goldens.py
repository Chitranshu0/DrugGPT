"""Synthesize RAG goldens from the local medical PDFs with OpenRouter models.

Run from the repo root::

    python -m tests.evals.generate_goldens

Raw results are written to the gitignored ``data/evals/`` directory; curate a
small subset into ``tests/evals/goldens.json`` so the committed suite stays
fast and its expected outputs are reviewed.
"""

from __future__ import annotations

import json
import sys

from src.core.config import PROJECT_ROOT

# DeepEval's rich progress output contains Unicode glyphs that cp1252 cannot encode.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from src.core.runtime import configure_runtime

configure_runtime()

from deepeval.models import DeepEvalBaseEmbeddingModel  # noqa: E402
from deepeval.synthesizer import Synthesizer  # noqa: E402
from deepeval.synthesizer.config import ContextConstructionConfig  # noqa: E402
from langchain_core.embeddings import Embeddings  # noqa: E402

from src.rag.retrieval import EMBEDDING_MODEL, get_embeddings  # noqa: E402
from tests.evals.judge import get_judge  # noqa: E402

# Keep the first generation cheap: skip the 120 MB anatomy book.
DOCUMENTS = (
    "data/raw/Current Essentials of Medicine(1)(1).pdf",
    "data/raw/standard-treatment-guidelines.pdf",
    "data/raw/40mbs_medicalbooksstore_2017_essentials.pdf",
)


class LocalEmbedder(DeepEvalBaseEmbeddingModel):
    """Reuse DrugGPT's own MiniLM embedder for synthesis context grouping."""

    def __init__(self) -> None:
        self._model: Embeddings = get_embeddings()
        super().__init__()

    def load_model(self) -> Embeddings:
        return self._model

    def embed_text(self, text: str) -> list[float]:
        return self._model.embed_query(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    async def a_embed_text(self, text: str) -> list[float]:
        return self.embed_text(text)

    async def a_embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.embed_texts(texts)

    def get_model_name(self) -> str:
        return EMBEDDING_MODEL


def main() -> None:
    judge = get_judge()
    # Free-tier OpenRouter: keep generation sequential to avoid rate limits.
    synthesizer = Synthesizer(model=judge, async_mode=False, max_concurrent=4)
    config = ContextConstructionConfig(
        embedder=LocalEmbedder(),
        critic_model=judge,
        max_contexts_per_document=3,
        min_contexts_per_document=1,
        max_context_length=2,
        min_context_length=1,
        # The free OpenRouter critic returns unreliable quality scores; accept
        # all contexts so synthesis actually produces goldens from the corpus.
        context_quality_threshold=0.0,
        context_similarity_threshold=0.0,
        max_retries=1,
    )
    goldens = synthesizer.generate_goldens_from_docs(
        document_paths=[str(PROJECT_ROOT / path) for path in DOCUMENTS],
        max_goldens_per_context=1,
        include_expected_output=True,
        context_construction_config=config,
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
