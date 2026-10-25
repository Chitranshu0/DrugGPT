# RAG Pipeline

RAG means **Retrieval-Augmented Generation**: we look up real text first,
then ask the LLM to answer using that text.

## Step 1: Ingestion (offline)

Files: `backend/ingestion/vector_db.py`, run by `scripts/ingest.py`

```
PDFs in Medical Books/
   -> load_pdf_documents()        # DirectoryLoader + PyMuPDF
   -> split_documents()           # chunks of 1000 chars, 150 overlap
   -> get_embedding()             # all-MiniLM-L6-v2
   -> PineconeVectorStore.from_documents()
```

Settings come from `backend/core/config.py` (`CHUNK_SIZE`, `CHUNK_OVERLAP`,
`MEDICAL_BOOKS_DIR`, `PINECONE_INDEX_NAME`).

## Step 2: Retrieval

File: `backend/rag/retrieval.py`

- `get_vectorstore()` connects to Pinecone only when called.
- `retrieve_context(query, k=5)` returns the top `k` chunks joined by blank lines.

## Step 3: Generation

File: `backend/rag/generation.py`

```python
context = retrieve_context(question)
answer = (PROMPT | llm).invoke({"context": context, "question": question})
```

The prompt is defined once as `PROMPT`. The LLM is a Groq chat model
configured by `LLM_MODEL` and `LLM_TEMPERATURE`.

## Step 4: Graph

File: `backend/rag/graph.py`

```
START -> medical_rag -> END
```

- `rag_node(state)` reads `state["question"]`, calls `rag_tool`, and writes
  `context` and `answer` back into the state.
- The graph is compiled with `InMemorySaver`, so state is kept per
  `thread_id`. It is **in memory only** and is lost when the server restarts.

## Where to tune things

| Want to change | File |
| --- | --- |
| Chunk size or overlap | `backend/core/config.py` |
| Embedding model | `backend/core/config.py` |
| LLM model or temperature | `backend/core/config.py` |
| Prompt text | `backend/rag/generation.py` |
| How many chunks are retrieved | `retrieve_context(..., k=5)` |
| Graph steps | `backend/rag/graph.py` |
