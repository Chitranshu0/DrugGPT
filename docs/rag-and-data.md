# RAG and data

Only index PDFs you are licensed to process. Keep them in `data/raw` (untracked).

## Indexing

`POST /vector-db/rebuild` builds the local Chroma collection:

```mermaid
flowchart LR
    P[PDFs in data/raw] --> F[Drop low-value pages<br/>front matter, TOC, index,<br/>bibliography, short chunks]
    F --> C[Chunk 1000 chars<br/>150 overlap]
    C --> L[Cap chunks per document]
    L --> N[Repo-relative paths<br/>+ one-based pages]
    N --> E[Embed + normalize<br/>all-MiniLM-L6-v2]
    E --> V[(Chroma<br/>cosine · schema v2)]
```

- The index is disposable; keep the original PDFs and rebuild anytime.
- One large book cannot dominate results (per-document cap).
- Old L2 indexes report `needs_rebuild=true`; answers then have no citations until rebuilt.

## Retrieval

```mermaid
flowchart TD
    Q[general / symptom question] --> EMB[Embed question]
    EMB --> CH[Chroma cosine search]
    CH --> SC[score = clamp of<br/>1 minus cosine distance]
    SC --> T{score >= threshold?}
    T -->|yes| G[Source-grounded answer<br/>+ page citations]
    T -->|no| N[General education<br/>still HTTP 200]
```

- RAG runs **only** for `general` / `symptom` questions.
- Score = `clamp(1 - cosine_distance, 0, 1)`; default threshold `0.35`.
- No index or low score is **not** an error — only LLM/config failures return 503.
- Cached embedder/client/store are cleared after a rebuild (`invalidate_caches()`).
- Streaming sends token events, then the same stored `ChatResponse`.

## Data directories

- `data/raw/` — licensed PDFs · `data/chroma/` — index
- `data/checkpoints/` — chat state (one thread per conversation; reviews use a separate thread)
- `data/druggpt.db` — patients, conversations, reviews
