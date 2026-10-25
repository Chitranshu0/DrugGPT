# Backend Map

The backend has four packages under `backend/`.

```
backend/
├── __init__.py              # package doc + __version__
├── main.py                  # creates the FastAPI app, includes routers
│
├── api/                     # HTTP layer
│   ├── __init__.py
│   ├── schemas.py           # Request/response models
│   └── routes/
│       ├── __init__.py
│       ├── chat.py          # POST /chat
│       ├── threads.py       # GET/POST/PATCH/DELETE /threads
│       └── health.py        # GET /health, GET /healthz
│
├── core/                    # shared setup
│   ├── __init__.py
│   ├── config.py            # all environment settings
│   └── embeddings.py        # HuggingFace embedding model
│
├── memory/                  # SQLite persistence
│   ├── __init__.py
│   ├── db.py                # data folder, connections, schema
│   └── conversations.py     # thread metadata CRUD
│
├── rag/                     # the RAG pipeline
│   ├── __init__.py
│   ├── state.py             # MedicalState with messages
│   ├── retrieval.py         # Pinecone search
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
| `backend/main.py` | Builds the app, opens SQLite in the lifespan, compiles the graph. Also serves `GET /`. |
| `backend/api/schemas.py` | Request and response models (Pydantic). |
| `backend/api/routes/chat.py` | `POST /chat`: runs the graph asynchronously and streams the answer. |
| `backend/api/routes/threads.py` | Lists, creates, loads, renames, and deletes conversations. |
| `backend/api/routes/health.py` | `GET /health` and `GET /healthz`: simple status checks. |
| `backend/core/config.py` | Reads `.env` and exposes every setting once. |
| `backend/core/embeddings.py` | One shared way to create the embedding model. |
| `backend/memory/db.py` | Creates `data/`, opens the app DB, applies the schema. |
| `backend/memory/conversations.py` | Thread metadata CRUD and automatic titles. |
| `backend/rag/state.py` | The `MedicalState` dictionary, including persisted messages. |
| `backend/rag/retrieval.py` | Connects to Pinecone and returns matching text. |
| `backend/rag/generation.py` | Builds the prompt (history + context) and calls the Groq LLM. |
| `backend/rag/graph.py` | Defines the graph and accepts a checkpointer from the app. |
| `backend/ingestion/vector_db.py` | Loads PDFs, splits them, uploads to Pinecone. |

## Import rules

- Always import with the full package path: `from backend.rag.retrieval import retrieve_context`.
- Never use bare imports like `from retrieval import ...`.
- Run commands from the project root.
- Do not compile the graph at import time; the app lifespan builds it with a checkpointer.

## Related docs

- API details: [api.md](api.md)
- RAG details: [rag-pipeline.md](rag-pipeline.md)
