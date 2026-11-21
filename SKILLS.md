# SKILLS.md — DrugGPT context engineering

This file gives coding agents the project context needed to work on DrugGPT safely.
DrugGPT is a **local-first, source-grounded medical education RAG app** (FastAPI +
Streamlit + LangGraph + ChromaDB + OpenRouter). It is **not** a clinical tool.

## Purpose
Answer medical science / drug-study questions conversationally. LangGraph routes
each message: educational questions use RAG over locally indexed PDFs; vague
messages get one clarifying question; personal clinical decisions (medicine,
test, treatment, test report) pause for clinician review. Emergency and
out-of-scope messages never call the LLM. Patients chat with an AI; doctors can
intervene in the same Streamlit UI.

## How to run (the only supported commands)
Terminal 1 — FastAPI backend (:8000):
```
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```
Terminal 2 — Streamlit UI (:8501):
```
streamlit run src/ui/Patient_Chat.py --server.port 8501
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
- `src/api/app.py`: `create_app(service=None)`; FastAPI app with typed REST routes.
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
- `src/ui/Patient_Chat.py`: patient chat page.
- `src/ui/pages/2_Clinician_Chat.py`: clinician transcript + reply page.
- `src/ui/pages/1_Patient_Profile.py`, `3_Admin.py`: supporting pages.
- `src/ui/api_client.py`: shared `DrugGPTApiClient` + `get_client()` factory.

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

## New: human-in-the-loop clinician chat (POC)
- `Conversation.mode` is `"ai"` (default) or `"human"` (SQLite migration is idempotent).
- `POST /conversations/{id}/messages`: if mode is `"human"`, the patient message is
  queued and the API returns `answer_mode="human_hold"` (no LLM call).
- `POST /conversations/{id}/clinician-reply`: clinician writes a free-text message;
  any pending review is closed as approved, the clinician message is stored with
  `role="clinician"`, and mode returns to `"ai"`.
- `GET /conversations/{id}/transcript`: messages + open review + issue context.
- Same Streamlit app; patient and doctor open different sidebar pages/tabs against one
  backend + one SQLite DB.

## Data and safety
- Never commit `.env` or anything under `data/` (`raw/`, `chroma/`,
  `checkpoints/`, `druggpt.db`).
- `LocalStore` is unauthenticated, demo-only: no real patient data, no auth shortcuts.
- Preserve guardrail responses and the clinician-review gate; add tests for any change.

## Docs
- `docs/development.md` is the most accurate guide. Trust code over docs and update
  the relevant doc when behavior changes.
