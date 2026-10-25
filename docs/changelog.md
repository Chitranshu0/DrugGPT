# DrugGPT Changelog

A short, plain-English record of changes.

> Note: older entries mention flat paths like `backend/retriever.py`.
> Those files have since moved into subpackages. See
> [backend.md](backend.md) for the current layout.

---

## SQLite persistence + multiple chats (latest)

- Conversations now survive backend restarts. LangGraph state is stored in
  `data/checkpoints.sqlite` with `AsyncSqliteSaver`.
- Conversation titles and timestamps live in `data/app.sqlite`, managed by
  the new `backend/memory/` package.
- `MedicalState` now includes a persisted `messages` list. The prompt uses
  the most recent messages (`MEMORY_WINDOW_MESSAGES`, default 12).
- New thread endpoints: `GET/POST /threads`,
  `GET/PATCH/DELETE /threads/{thread_id}`.
- `POST /chat` is now async, accepts an optional `thread_id`, and returns the
  generated id in `X-Thread-ID`.
- The graph is compiled once in the FastAPI lifespan instead of at import
  time. `InMemorySaver` has been removed.
- The Streamlit UI has a multi-chat sidebar with new chat, open, rename, and
  delete actions. History is reloaded from the backend, so a browser refresh
  no longer loses it.
- New settings: `DATA_DIR`, `SQLITE_CHECKPOINT_DB`, `SQLITE_APP_DB`,
  `SQLITE_BUSY_TIMEOUT_MS`, `MEMORY_WINDOW_MESSAGES`, and
  `THREAD_TITLE_MAX_LEN`.
- Docs updated across architecture, backend, API, RAG, setup, and development.

The checkpointer is short-term memory. HITL interrupts and `AsyncSqliteStore`
long-term memory build on this foundation in later phases.

---

## Backend split + `/health`

- Backend is now grouped by layer: `api/`, `core/`, `rag/`, `ingestion/`.
- New health endpoint `GET /health` (plus a `/healthz` alias). This fixes
  the `404 Not Found` errors for `/health`.
- `backend/main.py` now only builds the app and includes routers.
- `POST /chat` moved to `backend/api/routes/chat.py`.
- Settings moved to `backend/core/config.py`.
- Retrieval moved to `backend/rag/retrieval.py`.
- Generation moved to `backend/rag/generation.py`.
- Graph moved to `backend/rag/graph.py`.
- Ingestion moved to `backend/ingestion/vector_db.py`.
- Docs are now split into several files (start at [README.md](README.md)).

---

## Earlier restructuring

A short, plain-English summary of the earlier restructuring.

---

## Why we changed it

Before, all files were flat inside `RAG_pipeline/` and imports only worked
if you were inside that folder. Beginner developers had to guess:

- Which `main.py` to run (there were two).
- Why simply importing a file connected to Pinecone.
- Which file did what.

After the change, every file has one clear job, and the folder layout tells
you where to look.

---

## New folder layout

| Folder | What lives there |
| --- | --- |
| `backend/` | FastAPI app and the RAG pipeline |
| `frontend/` | Streamlit chat UI |
| `scripts/` | One-off commands (ingest PDFs, test the LLM) |
| `test/` | Manual check scripts |
| `docs/` | Notes like this one |

---

## What changed file by file

| File | Change |
| --- | --- |
| `RAG_pipeline/` | Renamed to `backend/` |
| `main.py` (root) | Moved to `scripts/smoke_test_llm.py` (it was a debug script) |
| `backend/frontend.py` | Moved to `frontend/streamlit_app.py` |
| `backend/requirements.txt` | Moved to the project root `requirements.txt` |
| `backend/config.py` | **New.** All environment settings in one place |
| `backend/embeddings.py` | **New.** The embedding model is created in one shared place |
| `backend/vector_db.py` | Now only has functions; PDF loading no longer runs on import |
| `backend/retriever.py` | Pinecone connection is created only when needed; debug `print` removed |
| `backend/rag.py` | Clearer prompt variable and model settings from `config.py` |
| `backend/graph.py` | Graph building is inside `create_graph()` |
| `backend/main.py` | Imports now use `backend.` package paths |
| `frontend/streamlit_app.py` | Split into small functions (`init_session`, `show_history`, `ask_backend`, `main`) |
| `scripts/ingest.py` | **New.** Run PDF -> Pinecone indexing from the command line |

---

## How to run now

```bash
# 1. Activate the environment
conda activate ai

# 2. Install what the project needs (once)
pip install -r requirements.txt

# 3. Index the books (first time only)
python -m scripts.ingest

# 4. Start the backend
uvicorn backend.main:app --reload

# 5. In a second terminal, start the frontend
streamlit run frontend/streamlit_app.py
```

---

## Environment check (conda env `ai`)

Checked on 25 Oct 2026 with Python 3.11.14.

Everything the app needs is already installed in `ai`:

- FastAPI + uvicorn (API)
- LangChain 1.x, LangGraph 1.x, `langchain-groq`, `langchain-pinecone`
- `sentence-transformers` + `langchain-huggingface` (embeddings)
- Pinecone, Streamlit, PyMuPDF, python-dotenv

Checks that were run:

| Check | Result |
| --- | --- |
| `python -m compileall backend scripts frontend` | OK |
| Import `backend.main` | OK (app title: DrugGPT) |
| `GET /` with FastAPI TestClient | `200 {"status": "running"}` |
| `POST /chat` (retrieval + LLM) | `200` + generated answer |
| `retrieve_context("What is AIDS?")` | OK (Pinecone + embeddings) |
| `python -m scripts.smoke_test_llm` | OK (`hello from DrugGPT.`) |

> `conda activate ai` works in an interactive terminal. For one-off commands
> or scripts, use `conda run -n ai python ...` instead.

---

## Latest update: Pinecone key

- The Pinecone key is read from `PINECONE_API_KEY` in `.env`.
- `backend/retriever.py` now passes it explicitly:
  `PineconeVectorStore(..., pinecone_api_key=PINECONE_API_KEY)`.
- `backend/vector_db.py` does the same when uploading documents.
- No more reliance on the library silently reading the environment variable.
- `test/vector_db_test.py` is a quick manual check:

```bash
python -m test.vector_db_test
```

Verified: the new key connects to Pinecone and returns real AIDS text from
the medical books.

---

## Rules we follow from now on

1. **One job per file.** Ingestion, retrieval, generation, and API stay separate.
2. **No work at import time.** Network calls and model loads happen inside functions.
3. **Settings come from `config.py`.** Never hardcode keys, paths, or model names.
4. **Run everything from the project root.** That keeps `backend.` imports working.
