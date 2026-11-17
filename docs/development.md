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

Tests use fake retrievers, an in-memory store, and an LLM stub, so they do not need an OpenRouter key, a network connection, or the private PDF corpus. Add behavioral tests alongside changes to guardrails, response schemas, indexing, and UI client calls. Keep runtime data out of commits and use typed models at application boundaries.

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
2026-11-15 19:57:47 | INFO     | druggpt.rag.service | Triage result: general
```

`main.py` calls it at import time so `uvicorn main:app --reload` logs immediately.

## Adding a new command

1. Add a `cmd_<name>` function and a subparser in `src/cli.py`.
2. Wire it into `build_parser()`.
3. Add tests in `tests/test_cli.py` (no server start required).
4. Update `docs/setup.md` and `docs/architecture.md`.

## Conventions

- Imports use the `src.*` scheme (e.g. `from src.core.config import Settings`).
- `Settings` values are read at instantiation time via `default_factory`, so tests and the CLI can override `os.environ` after import.
- Never commit `.env` or anything under `data/`.
- Keep `ruff check .` and `pytest` green on every change.
