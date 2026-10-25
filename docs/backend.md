# Backend Map

The backend has four packages under `backend/`.

```
backend/
├── __init__.py              # package doc + __version__
├── main.py                  # creates the FastAPI app, includes routers
│
├── api/                     # HTTP layer
│   ├── __init__.py
│   ├── schemas.py           # ChatRequest, HealthResponse
│   └── routes/
│       ├── __init__.py
│       ├── chat.py          # POST /chat
│       └── health.py        # GET /health, GET /healthz
│
├── core/                    # shared setup
│   ├── __init__.py
│   ├── config.py            # all environment settings
│   └── embeddings.py        # HuggingFace embedding model
│
├── rag/                     # the RAG pipeline
│   ├── __init__.py
│   ├── state.py             # MedicalState
│   ├── retrieval.py         # Pinecone search
│   ├── generation.py        # prompt + LLM answer
│   └── graph.py             # LangGraph workflow
│
└── ingestion/               # offline indexing
    ├── __init__.py
    └── vector_db.py         # PDF -> chunks -> Pinecone
```

## What each file does

| File | Responsibility |
| --- | --- |
| `backend/main.py` | Builds the FastAPI app and wires in the routers. Also serves `GET /`. |
| `backend/api/schemas.py` | Request and response models (Pydantic). |
| `backend/api/routes/chat.py` | `POST /chat`: runs the graph and streams the answer. |
| `backend/api/routes/health.py` | `GET /health` and `GET /healthz`: simple status checks. |
| `backend/core/config.py` | Reads `.env` and exposes every setting once. |
| `backend/core/embeddings.py` | One shared way to create the embedding model. |
| `backend/rag/state.py` | The `MedicalState` dictionary passed between graph nodes. |
| `backend/rag/retrieval.py` | Connects to Pinecone and returns matching text. |
| `backend/rag/generation.py` | Builds the prompt and calls the Groq LLM. |
| `backend/rag/graph.py` | Defines the graph: START -> medical_rag -> END. |
| `backend/ingestion/vector_db.py` | Loads PDFs, splits them, uploads to Pinecone. |

## Import rules

- Always import with the full package path: `from backend.rag.retrieval import retrieve_context`.
- Never use bare imports like `from retrieval import ...`.
- Run commands from the project root.

## Related docs

- API details: [api.md](api.md)
- RAG details: [rag-pipeline.md](rag-pipeline.md)
