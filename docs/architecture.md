# Architecture

DrugGPT is a local-first, source-grounded research application.

## Layout

The project uses a flat `src` layout (the package root is `src`, imported as `src.*`):

```text
DrugGPT/
├── main.py                     # entrypoint: python main.py [api|ui|all|index|check|test]
├── .env                        # runtime secrets (untracked)
├── .env.example                # template for .env
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── cli.py                  # CLI commands (testable, no server start)
│   ├── api/app.py              # FastAPI application
│   ├── core/
│   │   ├── config.py           # Settings (env/.env, validation, directories)
│   │   ├── models.py           # typed request/response/domain models
│   │   └── persistence.py      # SQLite store (patients, conversations, reviews)
│   ├── rag/
│   │   ├── guardrails.py       # triage rules (emergency / medication / symptom / general / out-of-scope)
│   │   ├── indexing.py         # Chroma index rebuild from data/raw
│   │   ├── retrieval.py        # Chroma retrieval + provenance
│   │   └── service.py          # LangGraph medical agent + citations
│   └── ui/
│       ├── app.py              # Streamlit chat page
│       ├── api_client.py       # testable HTTP client
│       └── pages/              # Streamlit multipage UI
├── tests/
└── data/                       # raw PDFs, Chroma index, checkpoints, druggpt.db (ignored by Git)
```

## Components

| Module | Responsibility |
|--------|----------------|
| `src.api` | FastAPI backend and HTTP boundary |
| `src.core` | Settings and typed shared API/domain models |
| `src.rag` | Guardrails, PDF indexing, Chroma retrieval, LangGraph tool orchestration, citation mapping |
| `src.ui` | Streamlit application and testable HTTP client |
| `src.cli` | CLI entrypoint (`main.py`) wrapping API, UI, index, check, and test commands |

## Request flow

```mermaid
flowchart TD
    A[User opens Streamlit UI] --> B[UI sends message to FastAPI]
    B --> C[POST /conversations/{id}/messages or POST /chat]
    C --> D[MedicalRAGService.send_message]
    D --> E[LangGraph: triage_query]
    E -->|emergency| F[Emergency guidance node]
    E -->|out_of_scope| G[Out-of-scope notice node]
    E -->|general/symptom/medication_review| H[Load patient context]
    H --> I{medication_review?}
    I -->|yes| J[Medication review node: draft + interrupt]
    I -->|no| K[Answer node: search_medical_sources tool]
    J -->|interrupt: await clinician| L[Clinician approves/rejects]
    L -->|approved| M[Return clinician-approved guidance]
    L -->|rejected| N[Return safety refusal]
    K --> O[ChromaDB similarity search]
    O --> P[Filter by relevance threshold]
    P --> Q[Grounded LLM answer + citations]
    Q --> R[API returns ChatResponse with sources/tool activity]
    R --> S[Streamlit renders answer + source cards]

    style A fill:#e1f5e1,stroke:#333
    style S fill:#e1f5e1,stroke:#333
    style J fill:#fff9c4,stroke:#333
    style L fill:#fff9c4,stroke:#333
```

1. The UI posts `message` (and optional `thread_id`) to the FastAPI backend.
2. The deterministic guardrail (`triage_query`) classifies the intent: emergency, out-of-scope, general, symptom, or medication review.
3. LangGraph invokes the `search_medical_sources` tool for answerable questions.
4. Chroma returns chunks with PDF path, page metadata, and relevance score.
5. Only chunks meeting `DRUGGPT_RELEVANCE_THRESHOLD` are passed to the LLM.
6. Medication-related requests are drafted and paused with `interrupt()` for clinician approval via `/reviews/{id}/decision`.
7. The API returns the answer, tool activity, status, and citation records together.

## Persistence

`data/raw` holds local licensed PDFs; `data/chroma` holds the disposable Chroma index; `data/checkpoints` is reserved for LangGraph conversation checkpoints; `data/druggpt.db` is the SQLite store for patients, conversations, and reviews. None are committed to Git.

## Running the project

```bash
# 1. Create environment and install
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -e '.[dev]'

# 2. Configure
cp .env.example .env
# edit .env and set OPENROUTER_API_KEY
mkdir -p data/raw
# copy licensed medical PDFs into data/raw/

# 3. Terminal 1: FastAPI backend (:8000) with auto-reload
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 4. Terminal 2: Streamlit frontend (:8501)
streamlit run src/ui/app.py --server.port 8501
```

Or use the Python launchers and maintenance CLI:

```bash
python main.py   # FastAPI backend
python app.py    # Streamlit frontend
python -m src.cli index # rebuild Chroma index from data/raw
python -m src.cli check # print resolved config + API health
python -m src.cli test  # run the pytest suite
```

`uvicorn main:app` resolves the lazy ``app`` exported by ``main.py``; logging is configured
at import time so request logs appear immediately in that terminal.

The API is available at `http://127.0.0.1:8000` (Swagger UI at `/docs`, ReDoc at `/redoc`); the UI at `:8501`. Use the Streamlit sidebar **Rebuild local medical source index** after adding PDFs.

## Safety and scope

DrugGPT answers medical science and drug-study questions only. It declines unrelated questions, patient-specific diagnosis/dosing/treatment requests, and urgent-care situations. If no indexed source sufficiently supports a question, it provides general educational information rather than inventing an answer. Verify research conclusions against the original materials and qualified professionals.
