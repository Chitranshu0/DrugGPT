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
history = format_history(previous_messages)
answer = (PROMPT | llm).invoke({
    "context": context,
    "history": history,
    "question": question,
})
```

The prompt is defined once as `PROMPT`. The LLM is a Groq chat model
configured by `LLM_MODEL` and `LLM_TEMPERATURE`.

`format_history` keeps the last `MEMORY_WINDOW_MESSAGES` messages (default
12). The current question is excluded from the history block so it is not
shown twice.

## Step 4: Graph

File: `backend/rag/graph.py`

```
START -> medical_rag -> END
```

- `rag_node(state)` reads `state["question"]` and the persisted `messages`,
  calls `rag_tool`, then writes `context`, `answer`, and the new `AIMessage`
  back into the state.
- `messages` uses LangGraph's `add_messages` reducer, so every turn is
  appended instead of replacing the conversation.
- The graph is compiled at application startup with `AsyncSqliteSaver`, so
  state is kept per `thread_id` in `data/checkpoints.sqlite` and survives a
  server restart.
- `create_graph(checkpointer=...)` takes the checkpointer as an argument.
  There is no module-level graph and no import-time database work.

## Persistence and history

The checkpointer is **short-term memory**. It stores each thread's full
state, including every message. `GET /threads/{thread_id}` reads that state
with `graph.aget_state(...)` and returns the messages to the UI.

Long-term memory will use `AsyncSqliteStore` later. It is a separate concern
from the per-thread checkpoint.

## Where to tune things

| Want to change | File |
| --- | --- |
| Chunk size or overlap | `backend/core/config.py` |
| Embedding model | `backend/core/config.py` |
| LLM model or temperature | `backend/core/config.py` |
| Prompt text | `backend/rag/generation.py` |
| How many chunks are retrieved | `retrieve_context(..., k=5)` |
| Graph steps | `backend/rag/graph.py` |
| History window | `MEMORY_WINDOW_MESSAGES` in `.env` |
| SQLite locations | `backend/core/config.py` |
