# Development guide

Install development tools with `pip install -e '.[dev]'`.

```bash
pytest
ruff check .
```

Tests use fake retrievers and an in-memory response stub, so they do not need a Groq key, a network connection, or the private PDF corpus. Add behavioral tests alongside changes to guardrails, response schemas, indexing, and UI client calls. Keep runtime data out of commits and use typed models at application boundaries.
