# DrugGPT

**Local-first, source-grounded medical education RAG app.** DrugGPT searches a local index of licensed medical PDFs, answers with page citations when evidence is found, and clearly labels general educational answers otherwise.

> **Not a clinical tool.** Built for students and researchers. It does not diagnose, prescribe, or handle emergencies.

**Stack:** Python 3.11+ · FastAPI · LangGraph · ChromaDB · SQLite · Next.js · Pytest · Ruff · DeepEval

## What it does

- FastAPI backend with typed JSON chat responses and an SSE streaming endpoint
- Next.js frontend (Vercel-ready) with patient chat and a drug-professional review console
- Local ChromaDB index over licensed medical PDFs; every grounded answer shows source and page
- LangGraph state graph routes each message: triage → context → answer / clarification / emergency / clinician review
- Deterministic safety guardrails; personal clinical decisions pause for a human clinician
- Educational-only scope — no diagnosis, prescribing, or emergency care

## Architecture

```mermaid
flowchart LR
    U[User] --> FE[Next.js UI<br/>patient chat + review console]
    FE --> API[FastAPI<br/>validate + typed response]
    API --> G[LangGraph<br/>conversation graph]
    G <--> DB[(SQLite<br/>patients, chats, reviews)]
    G <--> V[(Chroma<br/>PDF index)]
    G -. phrasing only .-> LLM[OpenRouter]
    G --> R[ChatResponse]
│   │       └── health.py        # GET /health, /healthz
│   ├── core/
│   │   ├── config.py            # All environment settings
│   │   └── embeddings.py        # Shared HuggingFace embedding model
│   ├── rag/
│   │   ├── state.py             # State shared between graph nodes
│   │   ├── retrieval.py         # Search Pinecone
│   │   ├── generation.py        # Context + LLM answer
│   │   └── graph.py             # LangGraph workflow
│   └── ingestion/
│       └── vector_db.py         # PDF -> Pinecone
│
├── frontend/
│   └── streamlit_app.py         # Streamlit chat UI
│
├── scripts/
│   ├── ingest.py                # Run the PDF -> Pinecone ingestion
│   └── smoke_test_llm.py        # Quick LLM connection check
│
├── test/
│   └── vector_db_test.py        # Quick Pinecone retrieval check
│
├── docs/                        # Project docs (start at docs/README.md)
├── requirements.txt
├── .env.example
├── README.md
└── .gitignore
```

### How the pieces fit together

```
Streamlit UI
    |
    v
FastAPI /chat  (backend/api/routes/chat.py)
    |
    v
LangGraph workflow  (backend/rag/graph.py)
    |
    v
RAG step  (backend/rag/generation.py)
    |------------------|
    v                  v
Pinecone search    Groq LLM
(backend/rag/retrieval.py)
```

---

## Documentation

Start at [`docs/README.md`](docs/README.md).

---

## Setup

Clone the repository:

```bash
git clone https://github.com/your-username/DrugGPT.git

cd DrugGPT
```

- **LangGraph** owns the conversation; **FastAPI** owns the HTTP boundary.
- **OpenRouter** only phrases responses — it never decides what the app is allowed to do.
- RAG runs only on the educational/symptom path; all other paths use dedicated nodes.

Full flow, triage routes, and review sequence: [architecture doc](docs/architecture.md). Code lives in `src/` (imported as `src.*`); runtime data lives in untracked `data/`.

## Engineering highlights

- **State graph:** `triage → load_context → answer | clarify | emergency | scope | clinician_review`
- **Deterministic triage:** regex guardrails run first; emergency always wins; clarifications are fixed and reviewed (no LLM call by default)
- **Human-in-the-loop:** `interrupt()` pauses personal decisions; the review row is saved first and resumed with `Command(resume=...)` on a separate thread so later turns never block
- **Cosine v2 index:** normalized embeddings, `hnsw:space=cosine`, `schema_version=2`; score = `clamp(1 - cosine_distance, 0, 1)`; cached embedder/client/store with `invalidate_caches()` on rebuild
- **Memory:** one checkpoint thread per conversation (`conversation:{id}`) restores earlier turns from SQLite
- **Streaming:** `/messages/stream` emits SSE tokens then the same stored `ChatResponse`
- **Citations:** repo-relative source paths and one-based page numbers — no absolute local paths

## Quick start

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate    # macOS/Linux
pip install -e '.[dev]'
cp .env.example .env            # set OPENROUTER_API_KEY
mkdir -p data/raw               # add licensed medical PDFs here

# Terminal 1: FastAPI backend (:8000)
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Next.js frontend (:3000)
cd Frontend && npm install && npm run dev
```

- No `python main.py` — run uvicorn directly. Interactive API docs at `/docs`.
- Frontend uses mock data until `NEXT_PUBLIC_API_BASE_URL` is set in `Frontend/.env.local`.
- Upgrades: rebuild once with `POST /vector-db/rebuild`; old L2 indexes have no citations.

Full configuration: [setup doc](docs/setup.md) and `.env.example`.
## Index the Medical Books (first time only)

Put your PDF files in the `Medical Books/` folder, then run:

```bash
python -m scripts.ingest
```

## Run the Backend

```bash
uvicorn backend.main:app --reload
```

## Testing & evaluation

```bash
pytest
ruff check .
deepeval test run tests/evals/test_druggpt.py
```

- Tests are offline: fake retrievers, an in-memory store, and an LLM stub — no API key, network, or PDFs needed.
- DeepEval uses fixed safety goldens plus RAG metrics (relevancy, faithfulness, no-diagnosis, trajectory).
- `OPENROUTER_FALLBACK_API_KEY` is a fallback only; the primary key is never overwritten.
- When a metric fails, fix the app — never the metric, threshold, or golden.

Details: [development doc](docs/development.md).

## Safety & scope

- Declines unrelated questions, patient-specific diagnosis/dosing/treatment requests, and urgent care.
- No source above threshold → general education (HTTP 200), never an invented answer.
- Local-only: no authentication, bound to `127.0.0.1` by default. Never enter real patient data.

See [safety and scope](docs/safety-and-scope.md).

## Documentation

- [Architecture](docs/architecture.md) — system, message flow, clinician-review gate
- [Setup](docs/setup.md) — installation and configuration
- [API](docs/api.md) — endpoints and response modes
- [RAG and data](docs/rag-and-data.md) — indexing and retrieval
- [Safety and scope](docs/safety-and-scope.md) — guardrails and limits
- [Development](docs/development.md) — tests, lint, DeepEval loop
- [ADR 0001](docs/adr/0001-local-chroma-source-grounded-rag.md) — why local ChromaDB

Agent context: [`docs/AGENTS.md`](docs/AGENTS.md) · [`docs/SKILLS.md`](docs/SKILLS.md).
