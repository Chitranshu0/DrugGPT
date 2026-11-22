# AGENTS.md

## What this is
Local-first, source-grounded medical education RAG app (FastAPI + Streamlit +
LangGraph + ChromaDB + OpenRouter). Not a clinical tool. Python 3.11+.
`src/` is the package root (`from src...`); run all commands from the repo root.

## Commands (PowerShell on this machine)
- Install: `python -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, `pip install -e ".[dev]"`
- Backend :8000: `uvicorn src.main:app --reload`
- Frontend :8501: `streamlit run src/ui/Patient_Chat.py --server.port 8501`
- Tests: `pytest` (offline); single test:
  `pytest tests/test_service.py::test_citations_preserve_page_and_source`
- DeepEval build loop: `deepeval test run tests/evals/test_druggpt.py` (real index + OpenRouter;
  see "DeepEval build loop" in `docs/development.md`). Goldens: `tests/evals/goldens.json`.
  Primary model `DRUGGPT_EVAL_MODEL` (default `inclusionai/ling-3.2-flash:free`); secondary OpenRouter
  key `OPENROUTER_FALLBACK_API_KEY` is used only on primary failure. Never overwrite `OPENROUTER_API_KEY`.
- Lint: `ruff check .` (line length 128, py311, rules E/F/I/UP). No CI or pre-commit;
  run lint + tests manually.
- Docs use bash (`cp`, `mkdir -p`); on Windows use `Copy-Item` / `New-Item -ItemType Directory -Force`.

## Architecture
- `src/main.py`: FastAPI composition root — `create_app(service=None)` builds the app, registers the global error handler, and includes each `make_router(service)` factory from `src/api/routes/{meta,index,patients,chat,reviews,clinician}.py`. Inject a service in tests; `uvicorn src.main:app` uses the module-level `app`. Configure runtime shims and logging before importing the service/route modules.
- `src/api/`: `metadata.py` (OpenAPI version/tags/description), `errors.py` (global JSON-500 handler), `deps.py` (`get_or_404`). There is no `src/api/app.py`.
- `src/rag/service.py`: LangGraph flow `triage -> load_context -> answer |
  medication_review | emergency | out_of_scope`; `guardrails.py` is deterministic regex triage.
- `src/rag/indexing.py`: rebuilds Chroma collection `medical_rag` from non-recursive
  `data/raw/*.pdf` (1000/150 chunks, `all-MiniLM-L6-v2`); `retrieval.py` returns `Evidence`.
- `src/core/persistence.py`: SQLite `LocalStore`; `src/core/models.py`: Pydantic API models.
- `src/core/runtime.py`: `configure_runtime()` disables TensorFlow before heavy imports; call it first in every entrypoint.
- Streamlit pages read `DRUGGPT_API_URL` at import; each page uses `get_client()` from
  `src.ui.api_client`. Each entrypoint also adds the repo root to `sys.path`, so direct
  `streamlit run` works without an editable install.

## Non-obvious behavior
- No index, or no chunk >= `DRUGGPT_RELEVANCE_THRESHOLD`, still returns HTTP 200 with
  `answer_mode="general_education"`. It does not refuse or 503. Only LLM/config failures
  return 503.
- Chroma uses **cosine space** with normalized embeddings and `schema_version=2`. Scores are
  `clamp(1 - cosine_distance, 0, 1)`. Older L2 indexes report `needs_rebuild=true` and must be
  recreated; until then answers have no citations.
- `MedicalRetriever` caches the embedder, Chroma client and store; `rebuild_index()` calls
  `invalidate_caches()`. Keep that pairing intact or rebuilt indexes will be shadowed.
- Clarifications are deterministic (no LLM call) unless `DRUGGPT_LLM_CLARIFY=1`.
- `/v1/models` is an OpenAI-compatible shim for external probes; nothing in this repo calls it.
- `Settings.validate()` blocks non-loopback binds unless `DRUGGPT_ALLOW_REMOTE=1` (no auth).
- Medication requests use LangGraph `interrupt()`; the review row is saved before the
  interrupt and resumed with `Command(resume=...)` keyed by the stored `graph_thread_id`.
  Keep that pairing intact.
- `Settings` is a frozen dataclass re-reading env on each instantiation, but
  `MedicalRAGService(app_settings=settings)` binds the default at import. Tests use
  `dataclasses.replace(Settings(), ...)` and inject `FakeRetriever`/`FakeLLM`/`FakeStore`.
- The embedding model downloads on first index/retrieval; `index` deletes and recreates
  the collection.

## Clinician review
- Personal clinical decisions pause with LangGraph `interrupt()`; the review row is
  saved before the interrupt and resumed via `POST /reviews/{id}/decision` using the
  stored `graph_thread_id`.
- `POST /conversations/{id}/clinician-reply` records a free-text clinician message and
  closes the open review as approved.
- `GET /conversations/{id}/transcript` returns messages + open review + issue context.
- Same Streamlit app; the clinician page reviews pending requests against one backend
  and one SQLite DB.

## Data and safety
- Never commit `.env` or anything under `data/` (`raw/`, `chroma/`, `checkpoints/`, `druggpt.db`).
- `LocalStore` is unauthenticated, demo-only: do not add real patient data or auth shortcuts.
- Preserve guardrail responses and the clinician-review gate; add tests for any change.

## Docs
- `docs/development.md` is the most accurate guide. Trust code over docs and update
  the relevant doc when behavior changes.
