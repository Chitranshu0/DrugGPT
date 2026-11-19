# Development guide

## Install development tools

```bash
pip install -e '.[dev]'
```

## Test and lint

```bash
pytest
ruff check .
```

Tests use fake retrievers, an in-memory store, and an LLM stub, so they do not need an OpenRouter key, a network connection, or the private PDF corpus. Add behavioral tests alongside changes to guardrails, response schemas, indexing, retrieval scoring, and UI client calls. Keep runtime data out of commits and use typed models at application boundaries.

Useful targeted suites:

```bash
pytest tests/test_retrieval.py tests/test_indexing.py   # scoring, schema detection, index filters
pytest tests/test_service.py tests/test_api.py          # streaming, guardrails, clinician review
```

`src.core.runtime.configure_runtime()` is called first in every entrypoint (uvicorn target and Streamlit pages). It disables TensorFlow before heavy imports and suppresses the Python-EOL warning from `google.api_core`. Add the same call to any new entrypoint.

## DeepEval build loop

`tests/evals/` holds the ground-truth suite used during development, not just a final gate:

```bash
# On Windows, rich's Unicode progress output needs UTF-8:
$env:PYTHONIOENCODING = "utf-8"
# The free OpenRouter tier is slow: allow long judge calls.
$env:DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE = "900"
deepeval test run tests/evals/test_druggpt.py   # run the eval suite
python -m tests.evals.generate_goldens          # synthesize RAG goldens from data/raw/*.pdf
```

By default both the app LLM and the judge use the OpenRouter key with the free
`DRUGGPT_EVAL_MODEL` (default `inclusionai/ling-3.2-flash:free`). If a second key is
configured as `OPENROUTER_FALLBACK_API_KEY`, it is attached as a LangChain
fallback and is only used when the primary call fails (429, 5xx, timeout) or
returns empty content — the primary key is never overwritten. Override the
fallback model with `DRUGGPT_EVAL_FALLBACK_MODEL`. The OpenRouter free tier has
a daily request cap; the fallback key keeps the eval loop running past it.

The suite injects a `CallbackHandler` from DeepEval's LangGraph integration (via
`MedicalRAGService.send_message(..., callbacks=...)`), so every graph/node/LLM/tool span is
evaluable without hand-rolled `@observe`. `tests/evals/judge.py` adapts the app's OpenRouter
model to `DeepEvalBaseLLM`; no OpenAI key or Confident AI account is needed. Goldens live in
`tests/evals/goldens.json`: fixed safety routes are asserted deterministically, RAG answers are
scored by relevancy, faithfulness, a no-diagnosis GEval, and trajectory metrics. Generated goldens
are written to gitignored `data/evals/` before being curated into that file.

When a metric fails, fix the app (prompt, retrieval scoping, guardrail, tool wiring) — never the
metric, threshold, or golden — then re-run the suite to confirm improvement without regressions.

## Project layout

```text
src/             # importable as src.* (package root)
tests/           # pytest suite
data/            # runtime data (ignored by Git)
docs/            # this documentation
main.py          # FastAPI backend entrypoint (`uvicorn main:app`)
pyproject.toml   # packaging, pytest, ruff, coverage configuration
.env             # runtime secrets (untracked)
src/ui/
  Patient_Chat.py          # patient chat page
  pages/
    1_Patient_Profile.py
    2_Clinician_Chat.py    # clinician transcript + reply page
    3_Admin.py
  api_client.py            # shared HTTP client + get_client()
```

## Logging

`src/core/config.py` exposes `setup_logging()`, which configures one consistent format:

```text
2026-11-15 19:57:47 | INFO     | druggpt.rag.service | Triage: general -> local evidence lookup, then an educational answer
```

`main.py` calls it at import time so `uvicorn main:app --reload` logs immediately.

### Log message convention

Write messages as **what happened + identifiers + outcome**, in plain language that explains
the flow to a developer reading the console after the fact:

- Good: `Conversation <id> created for patient <id> — mode=ai (awaiting messages)`
- Avoid: terse codes or raw state dumps like `chars=2`, `mode=clarification`, or `Triage result: general`.
- Errors go in the headline with the exception type and message — the global handler in
  `src/api/app.py` logs `Request failed: <METHOD> <path> raised <Type>: <message>` and keeps the
  full traceback via `logger.exception`.

`setup_logging()` demotes chatty third-party libraries (`httpx`, `httpcore`, `chromadb`,
`sentence_transformers`, `posthog`) to `WARNING` so their per-request HTTP/telemetry chatter does not
bury the application's own narrative. `uvicorn.access` is left at its default (INFO) so request logs
remain visible; to quiet it, set its level to `WARNING` in `setup_logging()`.

## Adding a new command

1. Add a `cmd_<name>` function and a subparser in `src/cli.py`.
2. Wire it into `build_parser()`.
3. Add tests in `tests/test_cli.py` (no server start required).
4. Update `docs/setup.md` and `docs/architecture.md`.

## Retrieval and streaming internals

- `src/rag/retrieval.py` caches the embedder, Chroma client and store with `functools.lru_cache`. Call `invalidate_caches()` after any index rebuild; otherwise searches keep hitting the deleted collection. The embedding model is intentionally kept warm.
- Scores are `clamp(1 - cosine_distance, 0, 1)`. Never switch back to `similarity_search_with_relevance_scores` without fixing score semantics first — it produced negative values and a warning that dumped entire documents into the log.
- `MedicalRAGService._prepare_general_answer()` is shared by the graph and the streaming endpoint. Keep guardrail branches and the `interrupt()` review gate untouched when changing the answer path.
- `GET /v1/models` is a compatibility shim for external OpenAI-compatible probes; nothing in this repo calls it.

## Conventions

- Imports use the `src.*` scheme (e.g. `from src.core.config import Settings`).
- `Settings` values are read at instantiation time via `default_factory`, so tests and the CLI can override `os.environ` after import.
- Never commit `.env` or anything under `data/`.
- Keep `ruff check .` and `pytest` green on every change.
