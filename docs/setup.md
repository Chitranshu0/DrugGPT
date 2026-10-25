# Setup

## Requirements

- Python 3.11+
- A conda environment named `ai` (already used by this project)
- A Groq API key
- A Pinecone API key and index

## 1. Create the environment

```bash
conda create -n ai python=3.11
conda activate ai
```

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

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
| `PINECONE_API_KEY` | Pinecone API key |
| `PINECONE_INDEX_NAME` | Index name (default `medical-rag`) |
| `EMBEDDING_MODEL_NAME` | HuggingFace embedding model |
| `MEDICAL_BOOKS_DIR` | Folder containing the PDFs |
| `CHUNK_SIZE`, `CHUNK_OVERLAP` | Text split settings |
| `DATA_DIR` | Folder for SQLite files (default `data`) |
| `SQLITE_CHECKPOINT_DB` | LangGraph state database |
| `SQLITE_APP_DB` | Conversation metadata database |
| `SQLITE_BUSY_TIMEOUT_MS` | How long SQLite waits for a lock |
| `MEMORY_WINDOW_MESSAGES` | Recent messages sent to the LLM |

The SQLite files are created automatically on first startup. You do not need
to create the `data/` folder or run any migration command.

## 4. Add the PDFs

Put the medical book PDFs in:

```
Medical Books/
```

## 5. Index the books (first time only)

```bash
python -m scripts.ingest
```

## 6. Run the backend

```bash
uvicorn backend.main:app --reload
```

On startup the app creates `data/checkpoints.sqlite` and `data/app.sqlite`.
Existing conversations are restored from those files.

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
# LLM connection
python -m scripts.smoke_test_llm

# Pinecone retrieval
python -m test.vector_db_test
```

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `/health` returns 404 | Restart the server so it loads the latest code |
| `ModuleNotFoundError: fastapi` | Wrong Python. Activate `ai` first |
| `PINECONE_API_KEY` missing | Add it to `.env` and restart |
| Slow first request | The embedding model is loading for the first time |
| Conversations disappeared | Check that `data/` is present and the app can write to it |
| `database is locked` | Use one uvicorn worker and avoid opening the app DB in another program |
