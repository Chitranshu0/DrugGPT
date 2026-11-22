# RAG and source-data workflow

Only add PDFs that you are licensed or otherwise authorized to process. Keep them in `data/raw`; this directory is deliberately ignored by Git.

## Indexing

Call `POST /vector-db/rebuild` to:

1. Load every PDF under `data/raw` with `PyMuPDFLoader`.
2. Drop low-value pages: front matter (`DRUGGPT_SKIP_FRONT_MATTER_PAGES`), dedications, tables of contents, indexes, bibliographies, and numeric/index-style pages. Very short chunks (`DRUGGPT_MIN_CHUNK_CHARS`) are also discarded. This matters because the original corpus was dominated by a 5,000-page textbook whose index and dedication pages out-ranked real content.
3. Split the remaining text into 1,000-character chunks with 150-character overlap.
4. Evenly sample chunks per document to at most `DRUGGPT_MAX_CHUNKS_PER_DOCUMENT`, so one large textbook cannot dominate retrieval.
5. Normalize `source` and `file_path` metadata to **repo-relative POSIX paths**. Citations never expose an absolute local path such as `C:\Users\...`.
6. Embed chunks with `sentence-transformers/all-MiniLM-L6-v2`, L2-normalized via `encode_kwargs={"normalize_embeddings": True}`.
7. Write the Chroma collection `medical_rag` to `data/chroma` with `collection_metadata={"hnsw:space": "cosine", "schema_version": 2}`.

The rebuild response reports `documents_indexed`, `chunks_indexed`, `chunks_dropped`, and a per-document breakdown. The index can be deleted and rebuilt at any time. It is not a source of truth: retain the original PDFs and verify citations against them.

> **Rebuild required when upgrading from an older version.** Older indexes used Chroma's default L2 space and stored absolute paths. `MedicalRetriever.status()` reports `ready=false`, `needs_rebuild=true`, and a log message asking you to rebuild the index. Until you rebuild, chat still works but falls back to `general_education` with no citations.

## Retrieval and citations

RAG is invoked **only** for messages triaged as `general` or `symptom`. Clarifications, emergencies, scope notices, and personal clinical decisions (medicine, test, treatment, report) never trigger retrieval — those paths are handled by their own LangGraph nodes.

On the answer path, `MedicalRetriever` queries Chroma and converts each result into an `Evidence` record preserving source path, title, page (converted to one-based), and relevance score. `MedicalRAGService.citations_from_evidence` maps evidence to `SourceCitation` records returned in the API response.

### Score semantics

The embedder is normalized and the collection uses cosine distance, so retrieval computes:

```text
cosine_similarity = 1 - chroma_cosine_distance      # true similarity in [-1, 1]
evidence.score    = clamp(cosine_similarity, 0, 1)  # stored in [0, 1]
```

This replaces the old `similarity_search_with_relevance_scores` path, which depended on a LangChain version-specific conversion and emitted `UserWarning: Relevance scores must be between 0 and 1` with full document dumps. Negative scores meant the configured `0.35` threshold could never be met, so nearly every answer silently lost its citations.

`Embedding` objects, the Chroma client, and the Chroma store are cached per process. A rebuild calls `invalidate_caches()` so searches cannot keep reading the deleted collection. This is what took vector search from 11–21 s per query to well under a second after warmup.

Only chunks with `score >= DRUGGPT_RELEVANCE_THRESHOLD` are passed to the LLM; otherwise the service answers from general educational information and sets `answer_mode` to `general_education`. HTTP 200 is returned in both cases; a missing index or a below-threshold result is **not** an error. Only LLM/config failures return 503.

### Calibrating the threshold

`DRUGGPT_RELEVANCE_THRESHOLD` defaults to `0.35` on the cosine-similarity scale. Treat it as provisional until you evaluate it against your own corpus. Keep a small golden set of questions with known relevant documents and check that the expected source ranks first with a score above the threshold. Lower values increase citation coverage but can weaken grounding.

### Streaming

`POST /conversations/{conversation_id}/messages/stream` emits token events for the grounded/general answer path and a terminal response event containing the same `ChatResponse` as the non-stream endpoint. Guardrail and clinician-review routes emit only the terminal event; the `interrupt()`/review-gate flow is unchanged.

## Data directories

- `data/raw/` — licensed PDFs (untracked)
- `data/chroma/` — disposable Chroma index (untracked)
- `data/checkpoints/` — LangGraph conversation checkpoints (untracked); one thread per conversation (`conversation:{id}`) stores the accumulated `messages` state, so restarting the service restores earlier turns. Personal-decision reviews use a separate `conversation:{id}:review:{message_id}` thread.
- `data/druggpt.db` — SQLite store for patients/conversations/reviews (untracked)
