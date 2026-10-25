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

Open:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/health`
- Interactive docs: `http://127.0.0.1:8000/docs`

## 7. Run the frontend

In a second terminal:

```bash
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
