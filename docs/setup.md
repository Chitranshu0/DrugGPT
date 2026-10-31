# Setup

## Requirements

- Python 3.11+
- A conda environment named `ai` (already used by this project)
- A Groq API key
- A Pinecone API key
- The **medicalchatbot** document index (already created) with:
  - `chunk_text`: NVIDIA `llama-text-embed-v2`, 1024 dim, cosine, full-text search `en`
  - `title`: full-text search `en`

No local embedding model and no GPU are needed. Pinecone creates the
embeddings on the server.

> For a visual walkthrough, see
> [vector-db-guide.md](vector-db-guide.md).

## 1. Create the environment

```bash
conda create -n ai python=3.11
conda activate ai
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

The project uses `pinecone>=10.1` because the Pinecone Documents API requires
it. `langchain-pinecone` is intentionally not used.

## 3. Create `.env`

```bash
cp .env.example .env
```

Fill in the values:

| Variable | Meaning |
| --- | --- |
| `GROQ_API_KEY` | Groq API key for the LLM |
| `LLM_MODEL` | Groq model name |
| `LLM_TEMPERATURE` | 0 = focused, 1 = creative |
| `MEDICAL_SCOPE_GUARD` | Keep the chatbot medical-only (`true`/`false`) |
| `SCOPE_MODEL` | Optional cheaper model for the one-word scope check |
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | Index name (default `medicalchatbot`) |
| `PINECONE_INDEX_HOST` | Index host from the Pinecone console |
| `PINECONE_NAMESPACE` | Namespace for the books (**must be set**; default `medical-books`) |
| `RETRIEVAL_MODE` | `hybrid` (recommended) or `dense` |
| `RETRIEVAL_TOP_K` | Chunks sent to the LLM (default 5) |
| `RETRIEVAL_FETCH_K` | Candidates before reranking (default 20) |
| `RETRIEVAL_RERANK` | Turn cross-encoder reranking on/off |
| `RERANK_MODEL` | Reranking model (default `bge-reranker-v2-m3`) |
| `MEDICAL_BOOKS_DIR` | Folder containing the PDFs |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | Text split settings |
| `UPSERT_BATCH_SIZE` | Documents per Pinecone request (max 96) |
| `DATA_DIR` | Folder for SQLite files (default `data`) |
| `SQLITE_CHECKPOINT_DB` | LangGraph state database |
| `SQLITE_APP_DB` | Conversation metadata database |
| `SQLITE_BUSY_TIMEOUT_MS` | How long SQLite waits for a lock |
| `MEMORY_WINDOW_MESSAGES` | Recent messages sent to the LLM |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Publishable key used for sign-in and token checks |
| `SUPABASE_SECRET_KEY` | Secret key for admin work (server only) |
| `AUTH_REQUIRED` | Set `false` only for local development without Supabase |
| `BOOTSTRAP_ADMIN_EMAIL` | Optional first admin account, created at startup |
| `BOOTSTRAP_ADMIN_PASSWORD` | Password for the bootstrap admin |

The SQLite files are created automatically on first startup. You do not need
to create the `data/` folder or run any migration command.

## 3b. Authentication (Supabase)

1. Create a project at [supabase.com](https://supabase.com).
2. Copy the project URL, the **publishable** key, and the **secret** key from
   Project Settings → API Keys into `.env`.
3. Keep the secret key on the backend only. It is used to auto-confirm
   signups and to create the bootstrap admin.
4. Optional: set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`. On
   startup the app creates/confirms that account and assigns any chats that
   existed before multi-user support to it.
5. To create an account from the command line instead, run:

   ```bash
   python -m scripts.create_user you@example.com --admin --claim-unowned
   ```

6. If you leave `SUPABASE_SECRET_KEY` as the example placeholder, signup falls
   back to Supabase's email-confirmation setting and the bootstrap admin step
   is skipped.

Startup upgrades `data/app.sqlite` automatically: it adds a `user_id` column
and a `users` table. No manual SQL is needed.

Use `AUTH_REQUIRED=false` only while developing locally without Supabase; it
creates a single `dev-user` account.

The Streamlit session keeps the tokens in memory. Reloading the browser page
clears them, so you will be asked to log in again.

## 4. Add the PDFs

Put the medical book PDFs in the folder set by `MEDICAL_BOOKS_DIR`, for
example:

```text
C:/Users/sinha/Downloads/Medical Books
```

Only `.pdf` files are read. Image-only/scanned pages produce no text; run OCR
on those files first if you need them.

## 5. Index the books

```bash
# Check the PDFs and chunk counts without uploading
python -m scripts.ingest --dry-run

# Build the full medical knowledge base
python -m scripts.ingest --reset

# Check retrieval and the medical-only guard
python -m test.vector_db_test
```

`--reset` clears only the `medical-books` namespace, not the whole index.
Re-running the build is safe because document IDs are deterministic.

Pinecone may take up to one minute to make every new document searchable.

## 6. Run the backend

```bash
uvicorn backend.main:app --reload
```

On startup the app creates `data/checkpoints.sqlite` and `data/app.sqlite`.
Existing conversations are restored from those files. If a bootstrap admin is
configured, it is created and receives any chats that predate multi-user
support.

All `/threads` and `/chat` requests require a Supabase access token. Sign up
or log in from the Streamlit UI; it stores the token for the session.

Use a **single uvicorn worker** while the project uses SQLite. Postgres is
the upgrade path for multi-worker deployments.

Open:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/health`
- Interactive docs: `http://127.0.0.1:8000/docs`
- Chat list: `http://127.0.0.1:8000/threads`

## 7. Run the frontend

In a second terminal:

```bash
streamlit run frontend/streamlit_app.py
```

Set `API_BASE_URL` if the backend is not running on
`http://127.0.0.1:8000`, for example:

```bash
set API_BASE_URL=http://127.0.0.1:9000
streamlit run frontend/streamlit_app.py
```

## Quick sanity checks

```bash
# Index schema and document count
python -c "from backend.core.pinecone_client import validate_index, get_index_stats; validate_index(verbose=True); print(get_index_stats())"

# LLM connection
python -m scripts.smoke_test_llm

# Retrieval + medical scope
python -m test.vector_db_test

# Per-user thread isolation (uses a temporary database)
python -m test.auth_isolation_test
```

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `/health` returns 404 | Restart the server so it loads the latest code |
| `ModuleNotFoundError: fastapi` | Wrong Python. Activate `ai` first |
| `PINECONE_API_KEY missing` | Add it to `.env` and restart |
| `404 Namespace not found` | The namespace is empty; set `PINECONE_NAMESPACE=medical-books` in `.env` and restart |
| `429 RESOURCE_EXHAUSTED` | Pinecone embedding rate limit; the script retries automatically |
| Empty retrieval | Wait up to one minute after ingestion, then retry |
| `dimension mismatch` | You are using the old index or old code; use `medicalchatbot` and the Documents API |
| Slow first request | Scope check + reranker + LLM cold start |
| Conversations disappeared | Check that `data/` is present and the app can write to it |
| `database is locked` | Use one uvicorn worker and avoid opening the app DB in another program |
| `401 Not authenticated` | Log in from the Streamlit UI; the access token is missing or expired |
| Signup asks to confirm email | Set a real `SUPABASE_SECRET_KEY` to auto-confirm, or click the email link |
| Bootstrap admin not created | The secret key is missing or still a placeholder in `.env` |
| Scanned PDF has no text | OCR the PDF first; the loader only reads embedded text |
