# API

Base URL: `http://127.0.0.1:8000`. Interactive docs: `/docs` (Swagger), `/redoc`.

## Endpoints by tag

```mermaid
flowchart LR
    C[Client] --> F[FastAPI<br/>validate + route]
    F --> G[LangGraph]
    G --> F
    F --> R[ChatResponse]

    F --> META[Meta<br/>GET / · /health · /v1/models]
    F --> IDX[Index<br/>GET /vector-db/status<br/>POST /vector-db/rebuild]
    F --> PAT[Patients<br/>list · create · get · patch · delete · summary]
    F --> CHAT[Chat<br/>conversations · messages · /messages/stream]
    F --> REV[Reviews<br/>list · get · POST /reviews/id/decision]
    F --> CLIN[Clinician<br/>transcript · clinician-reply]
```

- Tags: **Meta, Index, Patients, Chat, Reviews, Clinician**.
- `/v1/models` is an OpenAI-compatible shim for external probes; the UI never calls it.
- Details and request/response shapes: see `/docs`.

## Chat outcomes

```mermaid
flowchart TD
    S[POST /conversations/id/messages] --> O{route}
    O -->|grounded| A[answered · source_grounded]
    O -->|no source| B[answered · general_education]
    O -->|vague| C[needs_more_information · clarification]
    O -->|emergency| D[emergency_guidance · emergency]
    O -->|off topic| E[out_of_scope · scope_notice]
    O -->|personal| F[review_pending · clinician_review]
```

- Stream endpoint emits `token` events then one terminal `response` event; guardrails and review are unchanged.
- `ChatResponse`: `answer`, `sources`, `tool_activity`, `status`, `answer_mode`, `thread_id`, `review_id`, `review_status`.
- `sources`: `{id, title, path, page, excerpt, relevance_score}` — repo-relative path, one-based page.
- Errors: `404` not found · `409` invalid decision · `503` LLM/index unavailable · `500` unexpected (traceback logged, never returned).
