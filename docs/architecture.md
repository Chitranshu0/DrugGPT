# Architecture

DrugGPT is a medical RAG (Retrieval-Augmented Generation) chatbot.
The backend is split into four layers, so each part has one clear job.

| Layer | Folder | Job |
| --- | --- | --- |
| HTTP | `backend/api/` | Receive requests, validate input, return responses |
| Core | `backend/core/` | Settings, Pinecone client, text cleanup |
| Memory | `backend/memory/` | Manage conversation metadata in SQLite |
| RAG | `backend/rag/` | Search Pinecone, ask the LLM, run the graph |
| Ingestion | `backend/ingestion/` | Load PDFs and upload chunks to Pinecone |

## Chat request flow

```text
Streamlit UI  (frontend/streamlit_app.py)
        |
        |  GET/POST /threads, POST /chat { message, thread_id }
        v
FastAPI routes  (backend/api/routes/)
        |
        v
Compiled LangGraph graph  (app.state.graph)
        |
        v
rag_tool  (backend/rag/generation.py)
        |
        +----------------------+----------------------+
        |                      |                      |
        v                      v                      v
Medical scope check      Pinecone hybrid search   Groq LLM
(backend/rag/scope.py)   (backend/rag/retrieval.py) (grounded answer)
                         dense + BM25 + RRF + rerank

Every step is checkpointed to
data/checkpoints.sqlite by AsyncSqliteSaver.
```

## Startup and shutdown

`backend/main.py` uses a FastAPI lifespan:

```
startup
  -> create data/ and app.sqlite tables
  -> open AsyncSqliteSaver on data/checkpoints.sqlite
  -> compile the graph once and store it on app.state

shutdown
  -> close the SQLite connection
```

The graph is no longer compiled at import time. Routes read it from
`request.app.state.graph`.

## Persistence

Two SQLite files, each with one owner:

| File | Owner | Contents |
| --- | --- | --- |
| `data/checkpoints.sqlite` | LangGraph | Per-thread graph state, including messages |
| `data/app.sqlite` | Our code | Thread titles, timestamps, message counts |

The checkpointer is short-term memory: it keeps each conversation separate
by `thread_id` and survives server restarts. A future `AsyncSqliteStore` can
add long-term memory without changing these files.

## Ingestion flow

```text
PDFs (Medical Books/)
   -> PyMuPDF page text
   -> text cleanup (control chars, bullets, hyphen breaks)
   -> RecursiveCharacterTextSplitter (1,200 chars / 200 overlap)
   -> Pinecone documents (server-side llama-text-embed-v2, 1024 dim)
   -> namespace medical-books in index medicalchatbot
```

Run it with `python -m scripts.ingest`. See
[vector-db-guide.md](vector-db-guide.md) for the full build guide.

## Design rules

1. **One job per file.** API, retrieval, generation, and ingestion stay separate.
2. **No work at import time.** No network calls or model downloads on import.
3. **Settings come from `backend/core/config.py`.** No hardcoded keys, paths, or model names.
4. **Run commands from the project root.** That keeps `backend.*` imports working.
5. **The database is opened at startup, not import time.** `main.py` owns the checkpointer lifecycle.
6. **`thread_id` is the conversation boundary.** Never reuse an id for a different chat.
