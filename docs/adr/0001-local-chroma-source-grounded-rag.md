# ADR 0001: Local ChromaDB with source-required answers

## Decision

DrugGPT uses a persistent local ChromaDB collection for its initial deployment and generates answers only when retrieved source chunks meet a relevance threshold.

## Rationale

This keeps the prototype easy to run for students, avoids sending the document corpus to a managed vector service, and enables a citation record with local source/page metadata. Requiring evidence reduces unsupported model-only answers in an educational medical context.

## Consequences

Users must maintain their own licensed source corpus and rebuild the index after changes. The local design is not a multi-user production vector-store deployment; replacing it later requires a retriever implementation that preserves the same evidence contract.
