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

Tests use fake retrievers, an in-memory store, and an LLM stub, so they do not need a Groq key, a network connection, or the private PDF corpus. Add behavioral tests alongside changes to guardrails, response schemas, indexing, and UI client calls. Keep runtime data out of commits and use typed models at application boundaries.

## Project layout

```text
src/             # importable as src.* (package root)
tests/           # pytest suite
data/            # runtime data (ignored by Git)
docs/            # this documentation
main.py          # FastAPI backend entrypoint (`python main.py`)
app.py           # Streamlit frontend entrypoint (`python app.py`)
pyproject.toml   # packaging, pytest, ruff, coverage configuration
.env             # runtime secrets (untracked)
```

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
