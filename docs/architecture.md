# Architecture

DrugGPT is a **local-first, source-grounded medical education application**. Everything runs on your machine: the FastAPI backend, the Streamlit frontend, the Chroma vector index, and the SQLite store. This keeps sensitive PDFs and conversation data off managed cloud services while still letting an external language model (via OpenRouter) generate answers.

## What the architecture looks like

The system has four layers:

1. **User interfaces** — Streamlit pages for patients and clinicians.
2. **API boundary** — FastAPI routes, request/response models, and health endpoints.
3. **Core engine** — LangGraph agent, guardrails, retriever, and LLM caller.
4. **Local stores** — SQLite for application data and ChromaDB for the searchable PDF index.

```mermaid
flowchart TD
    subgraph UI["User Interfaces"]
        P[Patient Chat page]
        D[Clinician Chat page]
        A[Admin page]
    end

    subgraph API["FastAPI Backend"]
        R["/conversations/{id}/messages"]
        REV["/reviews/{id}/decision"]
        CR["/conversations/{id}/clinician-reply"]
        VDB["/vector-db/*"]
        H[/health, /docs]
    end

    subgraph CORE["Core RAG Engine"]
        GS[MedicalRAGService]
        G[guardrails.py<br/>triage_query]
        LG[LangGraph flow]
        RET[retrieval.py<br/>Chroma search]
        IDX[indexing.py<br/>PDF → chunks]
        LLM[OpenRouter LLM]
    end

    subgraph STORE["Local Stores"]
        RAW[data/raw<br/>licensed PDFs]
        CHROMA[data/chroma<br/>vector index]
        DB[(data/druggpt.db<br/>SQLite)]
        CKPT[data/checkpoints<br/>conversation state]
    end

    P -->|POST message| R
    D -->|POST decision| REV
    D -->|POST clinician-reply| CR
    A -->|rebuild index| VDB

    R --> GS
    REV --> GS
    CR --> GS
    GS --> G
    G -->|emergency| EM[Return emergency guidance]
    G -->|out_of_scope| OO[Return scope notice]
    G -->|general / symptom| LG
    G -->|medication_review| LG
    G -->|human mode| HH[Queue for clinician]

    LG -->|load context| DB
    LG -->|search_medical_sources| RET
    RET --> CHROMA
    CHROMA --> RAW
    RET -->|Evidence chunks| LG
    LG -->|below threshold| GE[General-education answer]
    LG -->|grounded| LLM
    LLM -->|source-grounded answer| RES[Return ChatResponse]
    LG -->|medication_review| MR[Draft + interrupt]
    MR -->|await clinician| REV
    REV -->|approved| RES
    REV -->|rejected| SR[Return safety refusal]
    HH --> CR
    CR --> RES

    VDB --> IDX
    IDX --> RAW
    IDX --> CHROMA
    GS -->|persist| DB

    style EM fill:#ffcccb,stroke:#333
    style OO fill:#ffcccb,stroke:#333
    style SR fill:#ffcccb,stroke:#333
    style GE fill:#fff9c4,stroke:#333
    style MR fill:#fff9c4,stroke:#333
    style HH fill:#fff9c4,stroke:#333
    style RES fill:#e1f5e1,stroke:#333
```

## How a message flows through the system

When a patient types a message in the Streamlit UI, the following happens:

1. **Patient sends a message** — `Patient_Chat.py` posts to `POST /conversations/{id}/messages`.
2. **API receives the message** — FastAPI validates the request, loads the conversation from SQLite, and calls `MedicalRAGService.send_message`.
3. **Safety triage runs first** — `guardrails.py` uses deterministic regex rules (`triage_query`) to classify the intent as **emergency**, **out-of-scope**, **general**, **symptom**, or **medication review**.
4. **Human mode short-circuits the LLM** — if the conversation is in `human` mode, the message is queued and the API returns `answer_mode="human_hold"`. No LLM call is made until a clinician replies.
5. **The LangGraph agent executes the right path**:
   - **Emergency / out-of-scope** → return an immediate, fixed response.
   - **General or symptom question** → load patient context, search Chroma, and ask the LLM to answer from the retrieved sources.
   - **Medication-related request** → draft guidance, save a pending review row, and pause with `interrupt()` until a clinician decides.
6. **Retrieval decides grounding quality** — `retrieval.py` fetches the top-k chunks from Chroma. Only chunks with `relevance_score >= DRUGGPT_RELEVANCE_THRESHOLD` are passed to the LLM. If no chunk qualifies, the service returns a **general-education** answer (`answer_mode="general_education"`) instead of inventing a source.
7. **Response returns to the UI** — the API sends back a `ChatResponse` with the answer, citations, tool activity, status, and (when relevant) a `review_id`.
8. **Clinician review resolves medication requests** — the clinician uses the Clinician Chat page to approve or reject the pending review via `POST /reviews/{id}/decision`, or to send a free-text reply via `POST /conversations/{id}/clinician-reply`.

## Project layout

The project uses a flat `src` layout (the package root is `src`, imported as `src.*`):

```text
DrugGPT/
├── main.py                     # lazy app export for `uvicorn main:app`
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
│       ├── Patient_Chat.py     # patient chat page
│       ├── api_client.py       # testable HTTP client
│       └── pages/              # Streamlit multipage UI
│           ├── 1_Patient_Profile.py
│           ├── 2_Clinician_Chat.py
│           └── 3_Admin.py
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

## Two kinds of human-in-the-loop behavior

DrugGPT has two related but separate ways a clinician can be involved:

| Mechanism | Trigger | Endpoint | Purpose |
|-----------|---------|----------|---------|
| **Medication review gate** | `triage_query` classifies the message as `medication_review` | `POST /reviews/{id}/decision` | Approve or reject AI-drafted guidance before the patient sees it |
| **Human clinician chat mode** | `Conversation.mode == "human"` | `POST /conversations/{id}/clinician-reply` | Queue patient messages so a clinician writes a free-text reply; any pending review is closed as approved and mode returns to `"ai"` |

Both paths store the result in SQLite and resume the same `graph_thread_id` that was saved before the interrupt.

## Persistence

`data/raw` holds local licensed PDFs; `data/chroma` holds the disposable Chroma index; `data/checkpoints` is reserved for LangGraph conversation checkpoints; `data/druggpt.db` is the SQLite store for patients, conversations, and reviews. None are committed to Git.

## Running the project

See [`setup.md`](setup.md) for full installation instructions. The short version is:

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
streamlit run src/ui/Patient_Chat.py --server.port 8501
```

Or use the maintenance CLI:

```bash
python -m src.cli index # rebuild Chroma index from data/raw
python -m src.cli check # print resolved config + API health
python -m src.cli test  # run the pytest suite
```

`uvicorn main:app` resolves the lazy ``app`` exported by ``main.py``; logging is configured at import time so request logs appear immediately in that terminal.

The API is available at `http://127.0.0.1:8000` (Swagger UI at `/docs`, ReDoc at `/redoc`); the UI at `:8501`. Use the Streamlit sidebar **Rebuild local medical source index** after adding PDFs.

## Safety and scope

DrugGPT answers medical science and drug-study questions for educational use. It declines unrelated questions, patient-specific diagnosis/dosing/treatment requests, and urgent-care situations. When no indexed source sufficiently supports a question, it provides general educational information rather than inventing an answer. Medication-related requests are held for clinician review. See [`safety-and-scope.md`](safety-and-scope.md) for details.

## Related docs

- [`setup.md`](setup.md) — installation, configuration, and startup commands
- [`api.md`](api.md) — endpoint reference and response schemas
- [`rag-and-data.md`](rag-and-data.md) — indexing workflow, retrieval, and citation rules
- [`safety-and-scope.md`](safety-and-scope.md) — guardrails, scope, and verification policy
- [`adr/0001-local-chroma-source-grounded-rag.md`](adr/0001-local-chroma-source-grounded-rag.md) — original ADR for local ChromaDB
