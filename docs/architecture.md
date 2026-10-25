# Architecture

DrugGPT is a medical RAG (Retrieval-Augmented Generation) chatbot.
The backend is split into four layers, so each part has one clear job.

| Layer | Folder | Job |
| --- | --- | --- |
| HTTP | `backend/api/` | Receive requests, validate input, return responses |
| Core | `backend/core/` | Settings and the shared embedding model |
| RAG | `backend/rag/` | Search Pinecone, ask the LLM, run the graph |
| Ingestion | `backend/ingestion/` | Load PDFs and upload chunks to Pinecone |

## Chat request flow

```
Streamlit UI  (frontend/streamlit_app.py)
        |
        |  POST /chat { message, thread_id }
        v
FastAPI route  (backend/api/routes/chat.py)
        |
        v
LangGraph workflow  (backend/rag/graph.py)
        |
        v
rag_tool  (backend/rag/generation.py)
        |
        +----------------------+
        |                      |
        v                      v
Pinecone search            Groq LLM
(backend/rag/retrieval.py)
```

## Ingestion flow

```
PDFs (Medical Books/)
   -> DirectoryLoader
   -> RecursiveCharacterTextSplitter
   -> HuggingFace embeddings
   -> Pinecone index
```

Run it with `python -m scripts.ingest`. See [setup.md](setup.md).

## Design rules

1. **One job per file.** API, retrieval, generation, and ingestion stay separate.
2. **No work at import time.** No network calls or model downloads on import.
3. **Settings come from `backend/core/config.py`.** No hardcoded keys, paths, or model names.
4. **Run commands from the project root.** That keeps `backend.*` imports working.
