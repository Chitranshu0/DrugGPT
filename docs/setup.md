# Setup and configuration

## Requirements

Python 3.11+ (3.12 or newer is recommended: `google.api_core` has announced 3.11 end-of-support for a future release), an OpenRouter API key, and medical PDFs that you are authorized to index.

TensorFlow is **not** used. Every entrypoint calls `src.core.runtime.configure_runtime()` before importing ML libraries, which sets `USE_TF=0`, `TRANSFORMERS_NO_TF=1`, and `TF_CPP_MIN_LOG_LEVEL=3`. This avoids a ~25 s startup penalty and the oneDNN/tf_keras warnings. Explicit values in `.env` or the shell take precedence.

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
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Next.js frontend (:3000) — see Frontend/README.md
cd Frontend
npm install
npm run dev
```

The frontend uses seeded mock data until `NEXT_PUBLIC_API_BASE_URL` is set in
`Frontend/.env.local`.

Open:

| URL | Purpose |
|-----|---------|
| `http://127.0.0.1:8000/` | API landing page with links |
| `http://127.0.0.1:8000/docs` | interactive Swagger UI |
| `http://127.0.0.1:8000/redoc` | ReDoc reference |
| `http://127.0.0.1:8000/health` | liveness probe |
| `http://127.0.0.1:8000/v1/models` | OpenAI-compatible model discovery shim (for external probes) |
| `http://127.0.0.1:8000/docs` | interactive Swagger UI, including the streaming chat endpoint |
| `http://127.0.0.1:3000` | Next.js chat UI |

Every request is logged to the backend terminal with a timestamp, level, and logger name
(`druggpt.api` / `druggpt.rag.service`), so you can follow triage, retrieval, LLM calls, and
clinician reviews as they happen.

## Running individual services

| Command | What it does |
|---------|--------------|
| `uvicorn src.main:app --reload` | FastAPI backend only (:8000) |
| `cd Frontend && npm run dev` | Next.js frontend only (:3000) |

## Configuration

Configuration lives in `.env` (untracked) with `.env.example` as the template. Precedence for every value:

**environment variable > `.env` > default**

```ini
OPENROUTER_API_KEY=your_openrouter_api_key

# Local, untracked runtime directory. Place licensed PDFs in data/raw by default.
DRUGGPT_DATA_DIR=data
DRUGGPT_API_URL=http://127.0.0.1:8000
DRUGGPT_API_HOST=127.0.0.1
DRUGGPT_API_PORT=8000
DRUGGPT_UI_PORT=8501
# Comma-separated browser origins allowed by CORS (add your Vercel URL when deployed)
DRUGGPT_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
# Regex fallback: any local port (incl. IPv6 localhost) and any *.vercel.app origin
DRUGGPT_CORS_ORIGIN_REGEX=^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$|^https://.*\.vercel\.app$
DRUGGPT_MODEL=nvidia/nemotron-3.5-lightning:free
DRUGGPT_RELEVANCE_THRESHOLD=0.35
DRUGGPT_RETRIEVAL_K=5

# Deterministic clarifications (recommended). Set to 1 for LLM-generated follow-ups.
DRUGGPT_LLM_CLARIFY=0

# Index quality filters
DRUGGPT_MIN_CHUNK_CHARS=120
DRUGGPT_SKIP_FRONT_MATTER_PAGES=5
DRUGGPT_MAX_CHUNKS_PER_DOCUMENT=600

# LocalStore has no auth. Never expose publicly.
DRUGGPT_ALLOW_REMOTE=0

# TensorFlow shims (also set automatically by src/core/runtime.py)
USE_TF=0
TRANSFORMERS_NO_TF=1
TF_CPP_MIN_LOG_LEVEL=3

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
| `DRUGGPT_UI_PORT` | `8501` | Legacy setting, unused (frontend is on :3000) |
| `DRUGGPT_CORS_ORIGINS` | local ports 3000/3001 | Comma-separated browser origins allowed to call the API; add the deployed Vercel URL here |
| `DRUGGPT_CORS_ORIGIN_REGEX` | local hosts (any port) and `*.vercel.app` | Regex fallback for origins not in the explicit list |
| `DRUGGPT_MODEL` | `nvidia/nemotron-3.5-lightning:free` | OpenRouter model name |
| `DRUGGPT_RELEVANCE_THRESHOLD` | `0.35` | minimum **cosine similarity** for grounded answers (`[0, 1]`) |
| `DRUGGPT_RETRIEVAL_K` | `5` | number of chunks retrieved (`>= 1`) |
| `DRUGGPT_LLM_CLARIFY` | `0` | use an LLM for vague-message follow-ups instead of the fixed reviewed message |
| `DRUGGPT_MIN_CHUNK_CHARS` | `120` | drop index chunks shorter than this |
| `DRUGGPT_SKIP_FRONT_MATTER_PAGES` | `5` | drop the first N pages of every PDF |
| `DRUGGPT_MAX_CHUNKS_PER_DOCUMENT` | `600` | evenly sampled chunk cap per PDF |
| `DRUGGPT_ALLOW_REMOTE` | `0` | allow binding to a non-loopback host (no auth — trusted demo networks only) |

`OPENROUTER_API_KEY` is required for generated answers. `DRUGGPT_DATA_DIR` is resolved relative to the repository root. If the index is unavailable, confirm PDFs are in `data/raw` and rebuild it. If chat generation fails, verify `OPENROUTER_API_KEY` and network access to OpenRouter.

**After upgrading an existing installation, always rebuild the index once** (with `POST /vector-db/rebuild`). Older indexes use L2 distance and absolute source paths; the app marks them as needing a rebuild and answers without citations until they are recreated in cosine space. See [`rag-and-data.md`](rag-and-data.md) for score semantics.

`Settings.validate()` refuses a non-loopback `DRUGGPT_API_HOST` unless `DRUGGPT_ALLOW_REMOTE=1`. `LocalStore` has no authentication, so keep the service bound to `127.0.0.1` unless you are deliberately demoing on a trusted local network.

## Verification

```bash
pytest                    # test suite
ruff check .              # linting
```
