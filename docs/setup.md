# Setup and configuration

## Requirements

Python 3.11+, a Groq API key, and medical PDFs that you are authorized to index.

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
# Terminal 1: FastAPI backend (:8000)
python main.py

# Terminal 2: Streamlit frontend (:8501)
python app.py
```

## Running individual services

| Command | What it does |
|---------|--------------|
| `python main.py` | FastAPI backend only (:8000) |
| `python main.py --reload` | Backend with auto-reload |
| `python app.py` | Streamlit frontend only (:8501) |
| `druggpt index` | rebuild the Chroma index from `data/raw` |
| `druggpt check` | print resolved config + API health |
| `druggpt test` | run the pytest suite |

## Configuration

Configuration lives in `.env` (untracked) with `.env.example` as the template. Precedence for every value:

**CLI flag > environment variable > `.env` > default**

```ini
GROQ_API_KEY=your_groq_api_key

# Local, untracked runtime directory. Place licensed PDFs in data/raw by default.
DRUGGPT_DATA_DIR=data
DRUGGPT_API_URL=http://127.0.0.1:8000
DRUGGPT_API_HOST=127.0.0.1
DRUGGPT_API_PORT=8000
DRUGGPT_UI_PORT=8501
DRUGGPT_MODEL=openai/gpt-oss-120b
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
| `GROQ_API_KEY` | (required) | Groq API key for answer generation |
| `DRUGGPT_DATA_DIR` | `data` | directory holding `raw/`, `chroma/`, `checkpoints/`, `druggpt.db` |
| `DRUGGPT_API_HOST` | `127.0.0.1` | API bind host |
| `DRUGGPT_API_PORT` | `8000` | API bind port |
| `DRUGGPT_UI_PORT` | `8501` | Streamlit UI port |
| `DRUGGPT_MODEL` | `openai/gpt-oss-120b` | Groq model name |
| `DRUGGPT_RELEVANCE_THRESHOLD` | `0.35` | minimum relevance score for grounded answers (`[0, 1]`) |
| `DRUGGPT_RETRIEVAL_K` | `5` | number of chunks retrieved (`>= 1`) |

`GROQ_API_KEY` is required for generated answers. `DRUGGPT_DATA_DIR` is resolved relative to the repository root. If the index is unavailable, confirm PDFs are in `data/raw` and rebuild it. If chat generation fails, verify `GROQ_API_KEY` and network access to Groq.

## Verification

```bash
python main.py check      # resolved config + API health (needs the API running)
pytest                    # test suite
ruff check .              # linting
```
