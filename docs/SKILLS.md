# SKILLS.md — DrugGPT context engineering

This file gives coding agents the project context needed to work on DrugGPT safely.
DrugGPT is a **local-first, source-grounded medical education RAG app** (FastAPI +
Next.js frontend in `Frontend/` + LangGraph + ChromaDB + OpenRouter). It is **not** a clinical tool.

## Purpose
Answer medical science / drug-study questions conversationally. LangGraph routes
each message: educational questions use RAG over locally indexed PDFs; vague
messages get one clarifying question; personal clinical decisions (medicine,
test, treatment, test report) pause for clinician review. Emergency and
out-of-scope messages never call the LLM. Patients chat with an AI; drug professionals
review and reply in the Next.js professional workspace.

## How to run (the only supported commands)
Terminal 1 — FastAPI backend (:8000):
```
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```
Terminal 2 — Next.js UI (:3000), see `Frontend/README.md`:
```
cd Frontend && npm install && npm run dev
```
There is no `python main.py` and no `python app.py`. `src/main.py` exposes a lazy
`app` via PEP 562 `__getattr__` for uvicorn.

Checks (from repo root):
```
pytest
pytest tests/test_service.py::test_citations_preserve_page_and_source
ruff check .
```

## Architecture
- `src/main.py`: FastAPI composition root; `create_app(service=None)` includes the
  `make_router(service)` factories from `src/api/routes/{meta,index,patients,chat,reviews,clinician}.py`.
  Shared API infra lives in `src/api/{metadata,errors,deps}.py`.
- `src/rag/service.py`: `MedicalRAGService`; LangGraph flow
  `triage -> load_context -> answer (RAG) | clarify | medication_review | emergency | out_of_scope`.
  RAG runs only for `general`/`symptom`. `guardrails.py` is deterministic regex
  triage; its `CLINICIAN_REVIEW_TRIAGE` set (medication, test, treatment, report)
  routes to the review node.
- `src/rag/indexing.py`: rebuilds Chroma collection `medical_rag` from non-recursive
  `data/raw/*.pdf` (1000/150 chunks, `all-MiniLM-L6-v2`).
- `src/rag/retrieval.py`: returns `Evidence` with source/path/page/score.
- `src/core/persistence.py`: SQLite `LocalStore`; unauthenticated, demo-only.
- `src/core/models.py`: Pydantic API models (`ChatResponse`, `Conversation`, ...).
- `Frontend/src/app/`: Next.js App Router entrypoint.
- `Frontend/src/components/role-gate.tsx`: patient vs drug-professional toggle (no auth).
- `Frontend/src/components/chat/`: patient/professional chat with streaming and sources.
- `Frontend/src/components/professional/`: request review console.
- `Frontend/src/lib/api/`: typed `DrugGPTApi`, HTTP client (SSE), mock adapter, env selector.

## Non-obvious behavior (do not break)
- No index / no chunk >= `DRUGGPT_RELEVANCE_THRESHOLD` still returns HTTP 200 with
  `answer_mode="general_education"`. Only LLM/config failures return 503.
- Personal clinical decisions use LangGraph `interrupt()`; the review row is saved
  before the interrupt and resumed with `Command(resume=...)` keyed by
  `graph_thread_id`. `issue_type` is stored in the review context.
- Vague messages ("help", "hi there") return `status="needs_more_information"`,
  `answer_mode="clarification"` from the `clarify` node with no RAG call.
- `Settings` is a frozen dataclass re-reading env on each instantiation.
- Tests use `dataclasses.replace(Settings(), ...)` and inject fakes.

## Clinician review
- Personal clinical decisions pause with LangGraph `interrupt()`; the review row stores
  the `graph_thread_id` used to resume the graph.
- `POST /reviews/{id}/decision` approves or rejects the draft and resumes the graph.
- `POST /conversations/{id}/clinician-reply` records a free-text clinician message and
  closes the open review as approved.
- `GET /conversations/{id}/transcript`: messages + open review + issue context.
- Same backend and SQLite DB; the Next.js professional workspace reviews pending
  requests in its Requests tab.

## Data and safety
- Never commit `.env` or anything under `data/` (`raw/`, `chroma/`,
  `checkpoints/`, `druggpt.db`).
- `LocalStore` is unauthenticated, demo-only: no real patient data, no auth shortcuts.
- Preserve guardrail responses and the clinician-review gate; add tests for any change.

## Docs
- `docs/development.md` is the most accurate guide. Trust code over docs and update
  the relevant doc when behavior changes.
