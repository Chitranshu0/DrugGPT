# API reference

## `GET /health`

Returns `{"status":"running"}`.

## `GET /vector-db/status`

Returns `ready`, `chunks_indexed`, and `documents_indexed`.

## `POST /vector-db/rebuild`

Builds the local Chroma collection from PDFs under `data/raw`. It returns counts, or `400` when no indexable PDFs are available.

## `POST /chat`

Request:

```json
{"message":"Explain aspirin pharmacology", "thread_id":"research-session-1"}
```

Response:

```json
{
  "answer":"...",
  "status":"answered",
  "thread_id":"research-session-1",
  "tool_activity":{"tool_name":"search_medical_sources","message":"Searched approved medical sources.","sources_found":2},
  "sources":[{"id":1,"title":"Pharmacology","path":"data/raw/book.pdf","page":42,"excerpt":"...","relevance_score":0.91}]
}
```

Statuses are `answered`, `rephrase_required`, `out_of_scope`, and `safety_refusal`. A missing source index or model configuration returns `503`.
