# API reference

Base URL: `http://127.0.0.1:8000` (configured by `DRUGGPT_API_HOST` / `DRUGGPT_API_PORT`).

Interactive docs: **`/docs`** (Swagger UI) and **`/redoc`** (ReDoc). Endpoints are grouped by tag:
**Meta**, **Index**, **Patients**, **Chat**, **Reviews**, **Clinician**.

All chat behavior comes from a **LangGraph state graph** in `src.rag.service`. FastAPI only validates the request and returns the graph's result as a typed `ChatResponse`. A message is routed to an educational answer (with RAG), one clarification question, emergency/scope guidance, or a clinician-review hold.

## `GET /`

Landing page with links to the docs and key endpoints.

```json
{"service": "DrugGPT API", "version": "3.0.0", "status": "running", "docs": "/docs", "health": "/health"}
```

## Error handling

| Status | Meaning |
|--------|---------|
| `404` | Patient, conversation, or review id not found |
| `409` | Invalid review decision (e.g. approval without guidance) |
| `503` | The language model or index is unavailable |
| `500` | Unexpected server error; a traceback is written to the backend log |

Unexpected failures never leak a raw traceback to the client — the response is
`{"detail": "..."}` and the full traceback is logged under `druggpt.api`.

## `GET /health`

Returns API status.

```json
{"status": "running", "mode": "local-development-only"}
```

## `GET /v1/models`

Minimal OpenAI-compatible discovery shim for external probes (not used by the Streamlit client).

```json
{"object": "list", "data": [{"id": "nvidia/nemotron-3.5-lightning:free", "object": "model", "owned_by": "openrouter"}]}
```

## `GET /vector-db/status`

Returns index readiness. An outdated L2 index reports `ready: false` with `needs_rebuild: true` and a `message` telling you to rebuild.

```json
{
  "ready": true,
  "chunks_indexed": 12,
  "documents_indexed": 2,
  "schema_version": 2,
  "distance_metric": "cosine",
  "needs_rebuild": false,
  "message": null
}
```

## `POST /vector-db/rebuild`

Builds the local Chroma collection from PDFs under `data/raw`. Low-value pages, short chunks, and surplus chunks are dropped; source paths are stored repo-relative. Returns counts, or `400` when no indexable PDFs are available.

```json
{
  "documents_indexed": 2,
  "chunks_indexed": 12,
  "chunks_dropped": 34,
  "per_document": {"data/raw/book.pdf": 12},
  "message": "Index rebuilt."
}
```

## Patients

### `GET /patients`
List patients. `404` if none exist.

### `POST /patients`
Create a patient.

```json
{"name": "Guest patient", "date_of_birth": null, "sex": null}
```

### `GET /patients/{patient_id}`
Get a patient. `404` if not found.

### `PATCH /patients/{patient_id}`
Update a patient.

### `GET /patients/{patient_id}/summary`
Get patient summary with approved facts.

## Conversations and messages

### `GET /patients/{patient_id}/conversations`
List conversations for a patient.

### `POST /conversations`
Create a conversation.

```json
{"patient_id": "...", "title": "New medical chat"}
```

### `GET /conversations/{conversation_id}/messages`
List messages in a conversation.

### `GET /conversations/{conversation_id}/messages/since`
Cheap polling payload used by the Streamlit transcript fragment. With `after=<message_id>`, returns only messages added after that id plus the current `version` (total message count). Omitting `after` returns the full history.

```json
{"messages": [], "version": 2}
```

### `POST /conversations/{conversation_id}/messages`
Send a message. LangGraph routes it and returns a `ChatResponse` with answer, sources, tool activity, status, and optional review.

```json
{"message": "Explain aspirin pharmacology"}
```

Possible outcomes:

| Outcome | `status` | `answer_mode` |
|---------|----------|---------------|
| Source-grounded answer | `answered` | `source_grounded` |
| General education (no relevant source) | `answered` | `general_education` |
| Vague message → follow-up question | `needs_more_information` | `clarification` |
| Emergency | `emergency_guidance` | `emergency` |
| Out of scope | `out_of_scope` | `scope_notice` |
| Personal decision held for clinician | `review_pending` | `clinician_review` |
| Conversation in human mode | `review_pending` | `human_hold` |

### `POST /conversations/{conversation_id}/messages/stream`

Server-sent events (SSE) variant of the chat endpoint. Streaming is used only for the general/symptom answer path; emergency, scope, clarification, and clinician-review routes emit a single terminal event. The terminal response contains the same `ChatResponse` as the non-stream endpoint and is persisted to SQLite identically.

```text
data: {"type": "token", "token": "Aspirin "}

data: {"type": "token", "token": "inhibits platelets."}

data: {"type": "response", "response": {"answer": "Aspirin inhibits platelets.", "answer_mode": "source_grounded", ...}}
```

Error events use `{"type": "error", "detail": "...", "status": 503?}`. The review gate and its `graph_thread_id` pairing are unchanged.

## Clinician review

A review is created for personal decisions about a **medicine, test, treatment, or test report**. The AI-generated draft stays internal until a clinician decides.

### `GET /reviews?status=pending`
List pending clinician reviews.

### `GET /reviews/{review_id}`
Get a review with its context.

### `POST /reviews/{review_id}/decision`
Approve or reject a review. On approval, `approved_guidance` becomes the user's answer; on rejection the user receives a safety refusal.

```json
{"decision": "approved", "reviewer_name": "Dr. Smith", "approved_guidance": null, "reviewer_note": null}
```

### `GET /conversations/{id}/transcript`
Return all messages plus any open review and its issue context (for the clinician UI).

### `POST /conversations/{id}/clinician-reply`
Write a free-text clinician reply. Closes any pending review as approved and returns the conversation to AI mode.

```json
{"message": "Discuss this with your doctor before starting it.", "reviewer_name": "Dr. Smith"}
```

## Legacy `POST /chat`

Request: `{"message": "Explain aspirin pharmacology", "thread_id": "research-session-1"}`

Response:

```json
{
  "answer": "...",
  "status": "answered",
  "thread_id": "research-session-1",
  "tool_activity": {"tool_name": "search_medical_sources", "message": "...", "sources_found": 2},
  "sources": [{"id": 1, "title": "Pharmacology", "path": "data/raw/book.pdf", "page": 42, "excerpt": "...", "relevance_score": 0.91}]
}
```

`status` values are `answered`, `out_of_scope`, `safety_refusal`, `emergency_guidance`, `review_pending`, and `needs_more_information`. A missing source index or model configuration is handled in-band (general education); model/config failures return `503`.

## ChatResponse schema

- `answer`: assistant text
- `sources`: list of `{id, title, path, page, excerpt, relevance_score}`. `path` is repo-relative; `relevance_score` is `clamp(1 - cosine_distance, 0, 1)`.
- `tool_activity`: `{tool_name, message, sources_found}`
- `status`: one of the `status` values above
- `thread_id`, `review_id`, `review_status`
- `answer_mode`: `source_grounded`, `general_education`, `clarification`, `emergency`, `scope_notice`, `clinician_approved`, `clinician_review`, `clinician_reply`, `human_hold`
