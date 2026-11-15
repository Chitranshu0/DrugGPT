# RAG and source-data workflow

Only add PDFs that you are licensed or otherwise authorized to process. Keep them in `data/raw`; this directory is deliberately ignored by Git.

## Indexing

Run `python main.py index` (or the **Rebuild local medical source index** button in the Admin page) to:

1. Load every PDF under `data/raw` with `PyMuPDFLoader`.
2. Split text into 1,000-character chunks with 150-character overlap.
3. Embed chunks with `sentence-transformers/all-MiniLM-L6-v2`.
4. Write the Chroma collection `medical_rag` to `data/chroma`.

The index can be deleted and rebuilt at any time. It is not a source of truth: retain the original PDFs and verify citations against them.

## Retrieval and citations

At response time, `MedicalRetriever` queries Chroma and converts each result into an `Evidence` record preserving source path, title, page (converted to one-based), and relevance score. `MedicalRAGService.citations_from_evidence` maps evidence to `SourceCitation` records returned in the API response.

Only chunks with `score >= DRUGGPT_RELEVANCE_THRESHOLD` are passed to the LLM; otherwise the service answers from general educational information and sets `answer_mode` to `general_education`.

Adjust `DRUGGPT_RELEVANCE_THRESHOLD` only with evaluation data; lower values can make responses less well grounded.

## Data directories

- `data/raw/` — licensed PDFs (untracked)
- `data/chroma/` — disposable Chroma index (untracked)
- `data/checkpoints/` — LangGraph conversation checkpoints (untracked)
- `data/druggpt.db` — SQLite store for patients/conversations/reviews (untracked)
