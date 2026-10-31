# API

Base URL while developing: `http://127.0.0.1:8000`

Interactive docs: `http://127.0.0.1:8000/docs`

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Tiny "is it running" response |
| `GET` | `/health` | Health check for monitors and scripts |
| `GET` | `/healthz` | Alias for `/health` |
| `GET` | `/v1/models` | OpenAI-compatible model list |
| `POST` | `/auth/signup` | Create an account (and sign in) |
| `POST` | `/auth/login` | Sign in with email and password |
| `POST` | `/auth/refresh` | Exchange a refresh token for a new session |
| `GET` | `/auth/me` | Return the signed-in account |
| `GET` | `/threads` | List the signed-in user's conversations |
| `POST` | `/threads` | Create an empty conversation |
| `GET` | `/threads/{thread_id}` | Conversation metadata plus messages |
| `PATCH` | `/threads/{thread_id}` | Rename a conversation |
| `DELETE` | `/threads/{thread_id}` | Delete a conversation and its state |
| `POST` | `/chat` | Ask a medical question (RAG) |

## Authentication

All `/threads` and `/chat` routes require a Supabase access token:

```http
Authorization: Bearer <access_token>
```

Supabase is the identity provider. The frontend sends credentials to this
backend (never to Supabase directly), and the backend validates the token on
every protected request. A missing or expired token returns `401`.

### `POST /auth/signup`

```json
{ "email": "student@example.com", "password": "secret123" }
```

Returns `201`. If Supabase auto-confirmed the account, the response contains a
ready-to-use session:

```json
{
  "requires_confirmation": false,
  "user": { "id": "6f2c...", "email": "student@example.com", "is_admin": false },
  "session": {
    "access_token": "eyJ...",
    "refresh_token": "v1...",
    "expires_at": 1767225600,
    "expires_in": 3600,
    "token_type": "bearer",
    "user": { "id": "6f2c...", "email": "student@example.com", "is_admin": false }
  }
}
```

If email confirmation is required, `session` is `null` and
`requires_confirmation` is `true`; the user must click the link in their email
before logging in. With `SUPABASE_SECRET_KEY` configured, signups are
auto-confirmed by the admin API.

### `POST /auth/login`

```json
{ "email": "student@example.com", "password": "secret123" }
```

Returns `200` with the same session shape shown above. Invalid credentials
return `401` with `{"detail": "Invalid email or password"}`.

### `POST /auth/refresh`

```json
{ "refresh_token": "v1..." }
```

Returns a fresh session. An expired or revoked refresh token returns `401`.

### `GET /auth/me`

Requires the bearer token and returns the account:

```json
{ "id": "6f2c...", "email": "student@example.com", "is_admin": false }
```

## `GET /health`

Returns `200` when the API is alive.

```json
{
  "status": "ok",
  "service": "DrugGPT",
  "version": "1.0"
}
```

Example:

```bash
curl http://127.0.0.1:8000/health
```

## `GET /`

```json
{ "status": "running" }
```

## `GET /v1/models`

OpenAI-compatible list containing the model from `LLM_MODEL`.

```json
{
  "object": "list",
  "data": [
    {
      "id": "llama-3.1-8b-instant",
      "object": "model",
      "created": 0,
      "owned_by": "groq"
    }
  ]
}
```

## Threads

Conversations are stored in SQLite and survive a backend restart. Every
chat is identified by a `thread_id` and is owned by the account that created
it. Listing, opening, renaming, and deleting are always scoped to the
signed-in user; another user's thread is reported as `404`.

### `GET /threads`

```json
[
  {
    "thread_id": "demo-thread-1",
    "title": "What is AIDS?",
    "created_at": "2026-10-25T10:00:00+00:00",
    "updated_at": "2026-10-25T10:05:00+00:00",
    "message_count": 4
  }
]
```

Newest conversations are returned first.

### `POST /threads`

Creates an empty conversation and returns its metadata with `201`.

```json
{
  "thread_id": "8f3c...",
  "title": "New chat",
  "created_at": "2026-10-25T10:00:00+00:00",
  "updated_at": "2026-10-25T10:00:00+00:00",
  "message_count": 0
}
```

### `GET /threads/{thread_id}`

Returns the conversation metadata plus its messages from the LangGraph
checkpoint:

```json
{
  "thread_id": "demo-thread-1",
  "title": "What is AIDS?",
  "created_at": "2026-10-25T10:00:00+00:00",
  "updated_at": "2026-10-25T10:05:00+00:00",
  "message_count": 4,
  "messages": [
    { "role": "user", "content": "What is AIDS?", "sources": [], "tool_calls": [] },
    {
      "role": "assistant",
      "content": "AIDS is ...",
      "sources": [
        { "title": "Current Essentials of Medicine", "source": "cem.pdf", "page": 214, "score": 0.42, "signals": ["dense", "text"] }
      ],
      "tool_calls": [
        { "name": "rag_tool", "title": "Searching medical references", "input": { "question": "What is AIDS?" }, "status": "completed", "summary": "Found 1 relevant passage" }
      ]
    }
  ],
  "pending_interrupt": null
}
```

`pending_interrupt` is reserved for human-in-the-loop approvals.

### `PATCH /threads/{thread_id}`

```json
{ "title": "HIV and AIDS questions" }
```

Returns the updated thread metadata.

### `DELETE /threads/{thread_id}`

Deletes the metadata row and all checkpoints for the thread. Returns `204`.
A missing thread returns `404`.

## `POST /chat`

Request body:

```json
{
  "message": "What is AIDS?",
  "thread_id": "demo-thread-1"
}
```

- `message`: the user's question.
- `thread_id`: optional. Reuse the same id for the same chat. If omitted,
  the backend generates one and returns it in the `X-Thread-ID` response
  header.

Response: `200` with `application/x-ndjson` — newline-delimited JSON events.
The UI uses these events to render Claude-style tool cards while the answer
is generated.

```json
{"type": "thinking", "label": "Thinking about your question..."}
{"type": "tool_call", "tool": {"name": "rag_tool", "title": "Searching medical references", "input": {"question": "What is AIDS?"}, "status": "running"}}
{"type": "tool_result", "tool": {"name": "rag_tool", "title": "Searching medical references", "input": {"question": "What is AIDS?"}, "status": "completed", "summary": "Found 3 relevant passages"}, "sources": [{"title": "Current Essentials of Medicine", "page": 214}]}
{"type": "answer", "content": "AIDS is ..."}
{"type": "done"}
```

On failure the stream emits `{"type": "error", "message": "..."}` and ends.

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer %ACCESS_TOKEN%" ^
  -d "{\"message\":\"What is AIDS?\",\"thread_id\":\"demo-thread-1\"}"
```

PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/chat" `
  -Headers @{ Authorization = "Bearer $env:ACCESS_TOKEN" } `
  -ContentType "application/json" `
  -Body '{"message":"What is AIDS?","thread_id":"demo-thread-1"}'
```

## Notes

- The answer is generated by the LLM from Pinecone context plus recent
  conversation history, so the first request can be slower.
- `POST /chat` needs `GROQ_API_KEY` and `PINECONE_API_KEY` in `.env`.
- Authenticated routes need a valid Supabase session; see
  [Authentication](#authentication).
- The first chat message becomes the automatic thread title.
- See [rag-pipeline.md](rag-pipeline.md) for how the answer is produced.
