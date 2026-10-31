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

Expected: the index schema, 4,223 documents, three medical answers with book
titles and page numbers, and four passing medical-scope checks.

## 6. Auth isolation check

```bash
python -m test.auth_isolation_test
```

Expected: `auth isolation ok`. This uses a temporary database and fake graph,
so it does not touch real chats or call Supabase.

## 7. Full chat check

Get an access token first by logging in through the UI, or call the endpoint
directly:

```bash
curl -X POST http://127.0.0.1:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"you@example.com\",\"password\":\"secret123\"}"
```

Use the returned `access_token` in the `Authorization` header:

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer %ACCESS_TOKEN%" ^
  -d "{\"message\":\"What is the first-line treatment for hypertension?\",\"thread_id\":\"test-1\"}"
```

Expected: `200` and a grounded answer with citations.

Try a non-medical message too:

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer %ACCESS_TOKEN%" ^
  -d "{\"message\":\"Write a Python function to sort a list.\",\"thread_id\":\"test-2\"}"
```

Expected: a polite medical-only refusal.

## 8. Persistence check

Create a chat, list it, then restart the backend:

```bash
curl -H "Authorization: Bearer %ACCESS_TOKEN%" http://127.0.0.1:8000/threads

curl -H "Authorization: Bearer %ACCESS_TOKEN%" ^
  http://127.0.0.1:8000/threads/test-1
```

Expected: after restarting uvicorn, `test-1` is still listed and its messages
are still returned. The SQLite files are in `data/`.

Delete it when finished:

```bash
curl -X DELETE -H "Authorization: Bearer %ACCESS_TOKEN%" ^
  http://127.0.0.1:8000/threads/test-1
```

## What is not covered yet

- Automated unit tests (`pytest`)
- Mocked Pinecone / LLM tests
- Frontend tests
- Automated SQLite persistence and restart tests
- A live Supabase signup/login test

These are good beginner-friendly contributions.
