# ADR 0001: Local ChromaDB with source-grounded answers

## Decision

DrugGPT uses a persistent local ChromaDB collection for its initial deployment and prefers source-grounded answers when retrieved chunks meet a relevance threshold; otherwise it falls back to general educational information.

## Rationale

This keeps the prototype easy to run for students, avoids sending the document corpus to a managed vector service, and enables a citation record with local source/page metadata. Requiring evidence reduces unsupported model-only answers in an educational medical context.

## Consequences

Users must maintain their own licensed source corpus and rebuild the index after changes. The local design is not a multi-user production vector-store deployment; replacing it later requires a retriever implementation that preserves the same evidence contract.

## Amendment 2026-11-18: cosine scoring and index schema v2

The original collection used Chroma's default L2 distance, so LangChain's `1 - distance` "relevance" conversion produced negative scores. With a `0.35` threshold, almost every answer silently lost its citations, defeating the ADR's goal. The collection now uses `hnsw:space=cosine` with L2-normalized embeddings and an explicit `schema_version=2`; evidence score is `clamp(1 - cosine_distance, 0, 1)`, computed in our own code rather than delegating to a version-dependent library helper. Legacy indexes are detected and rejected as needing a rebuild. Chunk filtering, per-document caps and repo-relative source paths were added at the same time. The evidence contract (content, source path/title, one-based page, score) is unchanged.
