# Setup and configuration

## Requirements

Python 3.11+, an OpenRouter API key, and medical PDFs that you are authorized to index.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -e '.[dev]'
cp .env.example .env
mkdir -p data/raw
```

Put PDFs you are licensed to index in `data/raw`, then start the two services in separate terminals:

```bash
# Terminal 1: FastAPI backend (:8000) with auto-reload
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Streamlit frontend (:8501)
streamlit run src/ui/Patient_Chat.py --server.port 8501
```

The Streamlit entrypoints add the repository root to `sys.path`, so direct
`streamlit run` also works without an editable install.

Open:

| URL | Purpose |
|-----|---------|
| `http://127.0.0.1:8000/` | API landing page with links |
| `http://127.0.0.1:8000/docs` | interactive Swagger UI |
| `http://127.0.0.1:8000/redoc` | ReDoc reference |
| `http://127.0.0.1:8000/health` | liveness probe |
| `http://127.0.0.1:8501` | Streamlit chat UI |

Every request is logged to the backend terminal with a timestamp, level, and logger name
(`druggpt.api` / `druggpt.rag.service`), so you can follow triage, retrieval, LLM calls, and
clinician reviews as they happen.

## Running individual services

| Command | What it does |
|---------|--------------|
| `uvicorn main:app --reload` | FastAPI backend only (:8000) |
| `streamlit run src/ui/Patient_Chat.py --server.port 8501` | Streamlit frontend only (:8501) |
| `python -m src.cli index` | rebuild the Chroma index from `data/raw` |
| `python -m src.cli check` | print resolved config + API health |
| `python -m src.cli test` | run the pytest suite |

`src/cli.py` is a maintenance helper only; it is not required to run the app.

## Configuration

Configuration lives in `.env` (untracked) with `.env.example` as the template. Precedence for every value:

**CLI flag > environment variable > `.env` > default**

```ini
OPENROUTER_API_KEY=your_openrouter_api_key

# Local, untracked runtime directory. Place licensed PDFs in data/raw by default.
DRUGGPT_DATA_DIR=data
DRUGGPT_API_URL=http://127.0.0.1:8000
DRUGGPT_API_HOST=127.0.0.1
DRUGGPT_API_PORT=8000
DRUGGPT_UI_PORT=8501
DRUGGPT_MODEL=nvidia/nemotron-3.5-lightning:free
DRUGGPT_RELEVANCE_THRESHOLD=0.35
DRUGGPT_RETRIEVAL_K=5

# LangSmith tracing (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=DrugGPT-chatbot
```

| Setting | Default | Meaning |
|---------|---------|---------|
| `OPENROUTER_API_KEY` | (required) | OpenRouter API key for answer generation |
| `DRUGGPT_DATA_DIR` | `data` | directory holding `raw/`, `chroma/`, `checkpoints/`, `druggpt.db` |
| `DRUGGPT_API_HOST` | `127.0.0.1` | API bind host |
| `DRUGGPT_API_PORT` | `8000` | API bind port |
| `DRUGGPT_UI_PORT` | `8501` | Streamlit UI port |
| `DRUGGPT_MODEL` | `nvidia/nemotron-3.5-lightning:free` | OpenRouter model name |
| `DRUGGPT_RELEVANCE_THRESHOLD` | `0.35` | minimum relevance score for grounded answers (`[0, 1]`) |
| `DRUGGPT_RETRIEVAL_K` | `5` | number of chunks retrieved (`>= 1`) |

`OPENROUTER_API_KEY` is required for generated answers. `DRUGGPT_DATA_DIR` is resolved relative to the repository root. If the index is unavailable, confirm PDFs are in `data/raw` and rebuild it. If chat generation fails, verify `OPENROUTER_API_KEY` and network access to OpenRouter.

## Verification

```bash
python -m src.cli check      # resolved config + API health (needs the API running)
pytest                    # test suite
ruff check .              # linting
```
