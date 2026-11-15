# API reference

Base URL: `http://127.0.0.1:8000` (configured by `DRUGGPT_API_HOST` / `DRUGGPT_API_PORT`).

## `GET /health`

Returns API status.

```json
{"status": "running", "mode": "local-development-only"}
```

## `GET /vector-db/status`

Returns index readiness.

```json
{"ready": true, "chunks_indexed": 12, "documents_indexed": 2}
```

## `POST /vector-db/rebuild`

Builds the local Chroma collection from PDFs under `data/raw`. Returns counts, or `400` when no indexable PDFs are available.

```json
{"documents_indexed": 2, "chunks_indexed": 12, "message": "Index rebuilt."}
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

### `POST /conversations/{conversation_id}/messages`
Send a message. Returns a `ChatResponse` with answer, sources, tool activity, status, and optional review.

```json
{"message": "Explain aspirin pharmacology"}
```

## Clinician medication review

### `GET /reviews?status=pending`
List pending medication reviews.

### `GET /reviews/{review_id}`
Get a review with its context.

### `POST /reviews/{review_id}/decision`
Approve or reject a review.

```json
{"decision": "approved", "reviewer_name": "Dr. Smith", "approved_guidance": null, "reviewer_note": null}
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

Statuses are `answered`, `out_of_scope`, `safety_refusal`, `emergency_guidance`, `review_pending`, and `clinician_review`. A missing source index or model configuration returns `503`.

## ChatResponse schema

- `answer`: assistant text
- `sources`: list of `{id, title, path, page, excerpt, relevance_score}`
- `tool_activity`: `{tool_name, message, sources_found}`
- `status`: one of the statuses above
- `thread_id`, `review_id`, `review_status`
- `answer_mode`: `source_grounded`, `general_education`, `emergency`, `scope_notice`, `clinician_approved`, `clinician_review`
