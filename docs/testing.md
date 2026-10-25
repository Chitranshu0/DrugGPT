# Testing

All commands run from the project root using the `ai` environment.

> In an interactive terminal run `conda activate ai` first. For one-off
> commands use `conda run -n ai python ...`.

## 1. Syntax check

```bash
python -m compileall backend scripts frontend test
```

## 2. Import check

```bash
python -c "import backend.main; print(backend.main.app.title)"
```

## 3. Health check

Against a running server:

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{ "status": "ok", "service": "DrugGPT", "version": "1.0" }
```

Without a server, use FastAPI's test client:

```bash
python -c "from fastapi.testclient import TestClient; from backend.main import app; print(TestClient(app).get('/health').json())"
```

## 4. LLM check

```bash
python -m scripts.smoke_test_llm
```

Expected: one short sentence from the model.

## 5. Retrieval check

```bash
python -m test.vector_db_test
```

Expected: a block of medical text from the books.

## 6. Full chat check

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"What is AIDS?\",\"thread_id\":\"test-1\"}"
```

Expected: `200` and a grounded answer.

## What is not covered yet

- Automated unit tests (`pytest`)
- Mocked Pinecone / LLM tests
- Frontend tests

These are good beginner-friendly contributions.
