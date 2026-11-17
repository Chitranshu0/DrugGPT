# DrugGPT — Detailed Project Reference

> Repository reference for the `master` branch. This document describes the implementation currently present in source code; where older documentation or tests disagree with the implementation, the discrepancy is called out explicitly.

## 1. Project overview

DrugGPT is a local-development medical education and drug-study assistant. It combines a conversational interface, a FastAPI backend, local PDF retrieval, an LLM powered by Groq, patient/conversation persistence, and a clinician-review workflow for medication-related requests.

The intended use is educational research and clinician-supervised review. The repository explicitly labels the current patient and review workflows as development-only. It is not a diagnostic, prescribing, emergency-care, or production patient-record system.

## 2. Current repository and branch

- Repository: `Chitranshu0/DrugGPT`
- Branch inspected: `master`
- Repository default branch reported by GitHub: `main`
- Python requirement: 3.11+
- Package version in `pyproject.toml`: 2.0.0
- FastAPI application version declared in `create_app`: 3.0.0

The GitHub connector can inspect and modify repository content, but it does not change a developer's local working directory. To switch a local clone to this branch, use:

```bash
git fetch origin
git switch master
git pull --ff-only origin master
```

If `master` is not present in the local clone, verify the remote branch with `git branch -r` before switching.

## 3. High-level architecture

The current implementation is organised into four application layers:

- `druggpt.ui`: Streamlit chat, patient profile, clinician review, and source-index administration pages.
- `druggpt.api`: FastAPI HTTP endpoints and request/response validation.
- `druggpt.rag`: intent triage, PDF indexing, Chroma retrieval, LangGraph orchestration, answer generation, citations, and review interruption.
- `druggpt.core`: environment-backed settings, Pydantic domain/API models, and SQLite persistence.

### Request lifecycle

1. A user selects a local patient profile and conversation in Streamlit.
2. Streamlit sends the message to the FastAPI conversation endpoint.
3. The service persists the user message and starts a LangGraph execution with a conversation/message-specific thread ID.
4. The triage node classifies the request as general, symptom-related, medication-review, emergency, or out-of-scope.
5. Emergency and out-of-scope requests take direct response paths.
6. Other requests load approved patient facts, the latest approved summary, and recent conversation history.
7. General and symptom-related requests search the local medical index. If retrieved evidence meets the configured relevance threshold, the grounded prompt receives the excerpts; otherwise the current implementation falls back to a general educational prompt.
8. Medication-review requests generate an internal draft and pause the graph using a LangGraph interrupt.
9. A reviewer approves or rejects the draft in the clinician-review page. The API resumes the paused graph and stores the resulting assistant response.
10. The UI renders the answer, status, and any source citations.

## 4. Source tree

```text
.
├── .env.example
├── README.md
├── pyproject.toml
├── docs/
│   ├── adr/
│   ├── api.md
│   ├── architecture.md
│   ├── development.md
│   ├── rag-and-data.md
│   ├── safety-and-scope.md
│   └── setup.md
├── src/druggpt/
│   ├── api/app.py
│   ├── core/
│   │   ├── config.py
│   │   ├── models.py
│   │   └── persistence.py
│   ├── rag/
│   │   ├── guardrails.py
│   │   ├── indexing.py
│   │   ├── retrieval.py
│   │   └── service.py
│   └── ui/
│       ├── api_client.py
│       ├── app.py
│       └── pages/
│           ├── 1_Patient_Profile.py
│           ├── 2_Clinician_Review.py
│           └── 3_Admin.py
└── tests/
```

Runtime data is expected under the configured data directory and is intentionally excluded from Git:
- `raw/`: licensed/authorised source PDFs.
- `chroma/`: persistent ChromaDB index.
- `checkpoints/langgraph.db`: LangGraph SQLite checkpoints.
- `druggpt.db`: application records, messages, patient facts, and review records.

## 5. Main modules

### `core/config.py`

Loads `.env` and creates an immutable `Settings` object. Important settings:

| Setting | Default | Purpose |
|---|---|---|
| `DRUGGPT_DATA_DIR` | `data` | Root for local runtime data |
| `GROQ_API_KEY` | unset | Required for LLM generation |
| `DRUGGPT_MODEL` | `openai/gpt-oss-120b` | Groq model identifier |
| `DRUGGPT_RELEVANCE_THRESHOLD` | `0.35` | Minimum accepted retrieval score |
| `DRUGGPT_RETRIEVAL_K` | `5` | Number of retrieved chunks |

The API URL is consumed by the Streamlit client from `DRUGGPT_API_URL`, defaulting to `http://127.0.0.1:8000`.

### `core/models.py`

Defines Pydantic request/response models and shared domain objects:
- `Patient`, `PatientFact`, and `PatientSummary`
- `Conversation` and `ConversationMessage`
- `MedicationReview` and `ReviewDecisionRequest`
- `Evidence`, `SourceCitation`, and `ToolActivity`
- `ChatRequest`, `MessageRequest`, and `ChatResponse`

The current `ChatStatus` values are `answered`, `out_of_scope`, `safety_refusal`, `review_pending`, `emergency_guidance`, and `needs_more_information`.

### `core/persistence.py`

Implements `LocalStore` using SQLite. It stores patient profiles, patient facts, approved clinical summaries, conversations, messages, and medication-review records. It also stores the LangGraph thread identifier and review context needed to resume an interrupted review.

This store has no authentication or authorisation layer. Its own module documentation says it must not be used for real patient data.

### `rag/guardrails.py`

Implements deterministic, regex/keyword-based triage:
- Emergency patterns route to an emergency escalation message.
- Medication selection/dose/change patterns route to clinician review.
- Symptom terms route to the symptom/general educational path.
- Medical terms route to the general path.
- A small out-of-scope keyword set rejects clearly unrelated prompts.

This is a lightweight heuristic, not a clinically validated classifier. Its coverage and false-positive/false-negative behaviour require testing before any real-world use.

### `rag/indexing.py`

Builds the local source index:
1. Finds PDF files in `data/raw`.
2. Loads pages with `PyMuPDFLoader`.
3. Splits text into 1,000-character chunks with 150-character overlap.
4. Deletes and recreates the `medical_rag` Chroma collection.
5. Embeds chunks and persists them under `data/chroma`.

Only PDFs the operator is licensed or otherwise authorised to process should be added.

### `rag/retrieval.py`

Uses `sentence-transformers/all-MiniLM-L6-v2` through Hugging Face embeddings and the Chroma vector store. Retrieval uses similarity scores and returns an `Evidence` object containing text, source path, source title, one-based page number, and a bounded relevance score.

The configured `retrieval_k` controls the number of returned chunks. A missing collection raises `VectorDatabaseNotReadyError`.

### `rag/service.py`

The main application service:
- Creates the Groq chat model lazily through `llm_factory`.
- Registers `search_medical_sources` as a LangChain structured tool.
- Builds a LangGraph state machine with triage, context loading, educational answer, emergency, out-of-scope, and medication-review nodes.
- Uses a SQLite LangGraph checkpointer.
- Converts evidence into source citation records.
- Pauses medication-related guidance for human review and resumes after a decision.

There are three prompts: source-grounded educational answer, general educational fallback, and internal draft guidance for clinician review. The grounded prompt explicitly says not to diagnose or prescribe. The review prompt asks the model to flag details a clinician should verify, such as allergies, interactions, contraindications, age/pregnancy, and severity.

### `api/app.py`

Creates the FastAPI application and wires HTTP endpoints to `MedicalRAGService`, `LocalStore`, and index rebuilding. It exposes health, index status/rebuild, patient, conversation, message, review, and legacy chat routes.

### `ui/`

The Streamlit interface is split into:
- `app.py`: patient chat and conversation selection.
- `1_Patient_Profile.py`: patient profile, approved summary, and facts.
- `2_Clinician_Review.py`: pending medication-review queue and approve/reject form.
- `3_Admin.py`: local source-index status and rebuild action.
- `api_client.py`: reusable HTTP wrapper with request timeouts and status checking.

## 6. API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Health and local-development mode |
| GET | `/vector-db/status` | Index readiness and document/chunk counts |
| POST | `/vector-db/rebuild` | Rebuild Chroma from PDFs in `data/raw` |
| GET | `/patients` | List local patient profiles |
| POST | `/patients` | Create a patient profile |
| GET | `/patients/{patient_id}` | Fetch a patient |
| PATCH | `/patients/{patient_id}` | Update patient fields |
| GET | `/patients/{patient_id}/summary` | Fetch profile, latest summary, and facts |
| POST | `/patients/{patient_id}/facts` | Add a patient fact |
| GET | `/patients/{patient_id}/conversations` | List a patient's conversations |
| POST | `/conversations` | Create a conversation |
| GET | `/conversations/{conversation_id}/messages` | List conversation messages |
| POST | `/conversations/{conversation_id}/messages` | Send a message |
| GET | `/reviews` | List reviews; defaults to pending |
| GET | `/reviews/{review_id}` | Fetch review and stored context |
| POST | `/reviews/{review_id}/decision` | Approve/reject and resume the graph |
| POST | `/chat` | Legacy compatibility endpoint |

### Chat request and response

The current UI uses `POST /conversations/{conversation_id}/messages` with:

```json
{
  "message": "Explain the mechanism of action of aspirin"
}
```

The response is a `ChatResponse` containing:
- `answer`
- `status`
- `thread_id`
- `sources` (each with title, path, page, excerpt, and relevance score)
- `tool_activity`
- optional `review_id` and `review_status`
- `answer_mode`

For medication-review requests, the initial response uses `review_pending`; the final response is written after a reviewer decision.

## 7. Data and RAG workflow

1. Create the local virtual environment and install the package.
2. Put authorised PDFs in `data/raw`.
3. Configure `GROQ_API_KEY`.
4. Start the API and Streamlit UI.
5. Rebuild the source index from the Admin page.
6. Check `/vector-db/status` before testing source-grounded questions.
7. Inspect each citation against the original PDF.

Page metadata from PyMuPDF is zero-based; the retriever converts it to one-based page numbers for display. The index is disposable and can be rebuilt. Keep original PDFs separately because the vector index is not the authoritative source.

## 8. Local setup

### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
cp .env.example .env
mkdir -p data/raw
```

Add authorised PDFs to `data/raw`, then run the API:

```bash
uvicorn druggpt.api.app:app --reload
```

In a second terminal, activate the same environment and run:

```bash
streamlit run src/druggpt/ui/app.py
```

Open the Streamlit URL printed in the terminal. The API defaults to `http://127.0.0.1:8000`.

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
New-Item -ItemType Directory -Force data\raw
uvicorn druggpt.api.app:app --reload
```

Run Streamlit from another activated terminal:

```powershell
streamlit run src/druggpt/ui/app.py
```

## 9. Testing and code quality

Development dependencies include pytest, pytest-cov, httpx, and Ruff. The documented checks are:

```bash
pytest
ruff check .
```

Tests use fake retrievers and an LLM stub so the core suite can run without the private PDF corpus or a Groq key. Add tests for triage edge cases, relevance-threshold behaviour, citation provenance, review interruption/resumption, API validation, and UI-client requests whenever those paths change.

**Important verification note:** the current branch contains apparent stale test/documentation contracts. For example, `tests/test_service.py` refers to `ChatStatus.REPHRASE_REQUIRED`, which is not present in the current `ChatStatus` enum; `tests/test_api.py` expects the old health response shape; and the old RAG documentation describes a rephrase-only low-evidence path, while the current service falls back to a general educational answer. Run the test suite and reconcile these mismatches before treating the branch as verified.

## 10. Security, privacy, and clinical safety

The current code is a local-development prototype:
- Patient and conversation endpoints do not implement authentication or role-based access control.
- The SQLite store is explicitly documented as unsuitable for real patient data.
- The clinician-review UI is a development-only workflow, not a verified clinical governance system.
- The deterministic triage rules are not a substitute for clinical assessment and can miss or misclassify requests.
- Source citations improve traceability but do not prove that a generated answer is correct or clinically safe.
- Do not commit PDFs, patient records, API keys, database files, or vector-store data.
- Use only source material you are authorised to process.

Before production use, implement authentication, authorisation, audit logging, encryption and secrets management, data-retention/deletion controls, tenant isolation, robust input validation, rate limiting, secure deployment, clinical governance, and documented evaluation. Validate retrieval quality and answer safety with a representative test set and qualified reviewers. Do not expose the current unauthenticated endpoints to the public internet.

## 11. Recommended engineering priorities

1. **Reconcile tests and contracts:** align `ChatStatus`, API health response expectations, low-evidence behaviour, and API documentation.
2. **Strengthen triage:** add a comprehensive, reviewed test corpus and consider a safer layered policy approach rather than relying only on keyword matching.
3. **Add evaluation:** measure retrieval precision/recall, citation correctness, groundedness, refusal behaviour, and reviewer agreement.
4. **Secure the application:** add authentication, role-based access for patient and clinician actions, audit events, and safe handling of sensitive data.
5. **Improve persistence:** add schema migrations, explicit transaction boundaries, concurrency handling, and backup/restore procedures.
6. **Operationalise:** add structured logs, metrics, health/readiness checks, containerised deployment, CI, dependency pinning, and environment-specific configuration.
7. **Improve RAG quality:** evaluate chunking, metadata filters, hybrid retrieval/reranking, source versioning, and document ingestion errors before tuning thresholds.

## 12. Key files to read first

For a new contributor, read in this order:

1. `src/druggpt/api/app.py` — HTTP surface and dependency wiring.
2. `src/druggpt/rag/service.py` — central LangGraph and business logic.
3. `src/druggpt/rag/guardrails.py` — routing and safety heuristics.
4. `src/druggpt/rag/indexing.py` and `retrieval.py` — PDF ingestion and search.
5. `src/druggpt/core/models.py` and `persistence.py` — data contracts and storage.
6. `src/druggpt/ui/app.py` and `ui/pages/` — user-facing workflows.
7. `tests/` — expected behaviours and current contract drift.

---

This reference is based on the files present on the inspected `master` branch. It is an implementation guide, not a security assessment, clinical validation, or claim that the project is production-ready.
