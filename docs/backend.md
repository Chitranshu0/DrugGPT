# Backend Map

The backend has four packages under `backend/`.

```
backend/
├── __init__.py              # package doc + __version__
├── main.py                  # creates the FastAPI app, includes routers
│
├── api/                     # HTTP layer
│   ├── __init__.py
│   ├── dependencies.py      # get_current_user (Supabase token check)
│   ├── schemas.py           # Request/response models
│   └── routes/
│       ├── __init__.py
│       ├── auth.py          # POST /auth/signup, /login, /refresh, GET /me
│       ├── chat.py          # POST /chat
│       ├── threads.py       # GET/POST/PATCH/DELETE /threads
│       └── health.py        # GET /health, GET /healthz
│
├── core/                    # shared setup
│   ├── __init__.py
│   ├── config.py            # all environment settings
│   ├── supabase_client.py   # auth client, token checks, admin helpers
│   ├── pinecone_client.py   # index connection + schema check
│   └── text.py              # PDF text cleanup
│
├── memory/                  # SQLite persistence
│   ├── __init__.py
│   ├── db.py                # data folder, connections, schema + migration
│   ├── users.py             # local mirror of Supabase accounts
│   ├── bootstrap.py         # first-run admin + unowned-thread backfill
│   └── conversations.py     # per-user thread metadata CRUD
│
├── rag/                     # the RAG pipeline
│   ├── __init__.py
│   ├── state.py             # MedicalState with messages
│   ├── scope.py             # medical-only question classifier
│   ├── retrieval.py         # hybrid search + RRF + rerank
│   ├── generation.py        # history + context + LLM answer
│   └── graph.py             # LangGraph workflow
│
└── ingestion/               # offline indexing
    ├── __init__.py
    └── vector_db.py         # PDF -> chunks -> Pinecone
```

## What each file does

| File | Responsibility |
| --- | --- |
| `backend/main.py` | Builds the app, opens SQLite in the lifespan, bootstraps auth, compiles the graph. Also serves `GET /`. |
| `backend/api/dependencies.py` | `get_current_user`: verifies the Supabase bearer token and syncs the local user row. |
| `backend/api/schemas.py` | Request and response models (Pydantic). |
| `backend/api/routes/auth.py` | Sign up, log in, refresh a session, and return the current account. |
| `backend/api/routes/chat.py` | `POST /chat`: checks thread ownership, runs the graph asynchronously, and streams the answer. |
| `backend/api/routes/threads.py` | Lists, creates, loads, renames, and deletes the signed-in user's conversations. |
| `backend/api/routes/health.py` | `GET /health` and `GET /healthz`: simple status checks. |
| `backend/core/config.py` | Reads `.env` and exposes every setting once. |
| `backend/core/supabase_client.py` | Shared Supabase clients, token verification, sign-in/sign-up, admin helpers. |
| `backend/core/pinecone_client.py` | Shared Pinecone client, index host, schema validation, stats. |
| `backend/core/text.py` | Cleans PDF text and formats book titles. |
| `backend/memory/db.py` | Creates `data/`, applies the schema, and migrates older databases. |
| `backend/memory/users.py` | Local `users` table that mirrors Supabase accounts. |
| `backend/memory/bootstrap.py` | Creates the first-run admin and assigns ownerless conversations. |
| `backend/memory/conversations.py` | Per-user thread metadata CRUD and automatic titles. |
| `backend/rag/state.py` | The `MedicalState` dictionary, including persisted messages. |
| `backend/rag/scope.py` | Classifies a question as medical or off-topic. |
| `backend/rag/retrieval.py` | Hybrid Pinecone search, RRF, reranking, context formatting. |
| `backend/rag/generation.py` | Builds the prompt (history + context) and calls the Groq LLM. |
| `backend/rag/graph.py` | Defines the graph and accepts a checkpointer from the app. |
| `backend/ingestion/vector_db.py` | Loads PDFs, splits them, uploads documents to Pinecone. |

## Import rules

- Always import with the full package path: `from backend.rag.retrieval import retrieve_context`.
- Never use bare imports like `from retrieval import ...`.
- Run commands from the project root.
- Do not compile the graph at import time; the app lifespan builds it with a checkpointer.

## Related docs

- API details: [api.md](api.md)
- RAG details: [rag-pipeline.md](rag-pipeline.md)
