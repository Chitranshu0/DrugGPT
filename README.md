# 💊 DrugGPT

A simple Medical RAG (Retrieval-Augmented Generation) chatbot built using LangGraph, LangChain, Pinecone, Groq, FastAPI, and Streamlit.

This project started as a way to learn how modern AI assistants actually work behind the scenes instead of just calling an LLM API and hoping for the best.

The idea is simple:

* Store medical books in a vector database
* Retrieve relevant information based on the user's question
* Feed that information to an LLM
* Generate grounded answers instead of hallucinating

---

## Why this project?

Most AI chatbots can answer medical questions, but they often rely only on their pre-trained knowledge.

DrugGPT tries to answer questions using information retrieved from medical books before generating a response.

This project is also a playground for learning:

* RAG Pipelines
* LangGraph
* Agentic AI
* Vector Databases
* LLM Engineering
* Open Source Collaboration

---

## Current Features

* PDF document ingestion
* Medical book processing
* Text cleaning and chunking
* Server-side NVIDIA embeddings (Pinecone)
* Pinecone document index with full-text search
* Hybrid retrieval (semantic + keyword)
* Reciprocal Rank Fusion (RRF)
* Cross-encoder reranking
* Medical-only scope guard
* Grounded answers with book/page citations
* LangGraph workflow
* FastAPI backend
* Streamlit frontend
* LangSmith tracing
* SQLite conversation persistence
* Multiple chat threads with resume
* Message history across restarts
* Multi-user accounts with Supabase Auth
* Private conversation history per user

---

## Tech Stack

### AI

* LangChain
* LangGraph
* Groq (`openai/gpt-oss-120b` by default)
* Pinecone integrated embedding: NVIDIA `llama-text-embed-v2` (1024 dim)
* Pinecone reranker: `bge-reranker-v2-m3`

### Backend

* FastAPI

### Authentication

* Supabase Auth (email + password)

### Frontend

* Streamlit

### Database

* Pinecone Vector Database (medical books)
* SQLite (conversation state and metadata)

### Observability

* LangSmith

### Document Processing

* PyMuPDF

---

## Project Structure

```bash
DrugGPT/
│
├── backend/                     # FastAPI app + RAG pipeline
│   ├── __init__.py
│   ├── main.py                  # Creates the app and includes routers
│   ├── api/
│   │   ├── dependencies.py      # Supabase token check for protected routes
│   │   ├── schemas.py           # Request/response models
│   │   └── routes/
│   │       ├── auth.py          # Signup, login, refresh, me
│   │       ├── chat.py          # POST /chat
│   │       ├── threads.py       # Per-user chat list, history, rename, delete
│   │       └── health.py        # GET /health, /healthz
│   ├── core/
│   │   ├── config.py            # All environment settings
│   │   ├── supabase_client.py   # Auth client and admin helpers
│   │   ├── pinecone_client.py   # Index connection + schema check
│   │   └── text.py              # PDF text cleanup
│   ├── memory/
│   │   ├── db.py                # SQLite setup, schema, migration
│   │   ├── users.py             # Local mirror of Supabase accounts
│   │   ├── bootstrap.py         # First-run admin + thread backfill
│   │   └── conversations.py     # Per-user thread metadata CRUD
│   ├── rag/
│   │   ├── state.py             # State shared between graph nodes
│   │   ├── scope.py             # Medical-only question classifier
│   │   ├── retrieval.py         # Hybrid search + RRF + rerank
│   │   ├── generation.py        # Context + history + LLM answer
│   │   └── graph.py             # LangGraph workflow
│   └── ingestion/
│       └── vector_db.py         # PDF -> Pinecone documents
│
├── frontend/
│   └── streamlit_app.py         # Streamlit chat UI
│
├── data/                        # SQLite files (created at runtime, gitignored)
│
├── scripts/
│   ├── ingest.py                # Run the PDF -> Pinecone ingestion
│   └── smoke_test_llm.py        # Quick LLM connection check
│
├── test/
│   └── vector_db_test.py        # Quick Pinecone retrieval check
│
├── docs/                        # Project docs (start at docs/README.md)
├── requirements.txt
├── .env.example
├── README.md
└── .gitignore
```

### How the pieces fit together

```
Streamlit UI
    |
    |  login/signup + Bearer token
    v
FastAPI /auth, /threads, /chat  (backend/api/routes/)
    |                    |
    v                    v
Supabase Auth      LangGraph workflow  (backend/rag/graph.py)
(token checks)           |
                    |-----------------------------|
                    v                             v
                RAG step                    SQLite checkpoint
                (Pinecone + Groq)          (data/checkpoints.sqlite)
```

---

## Documentation

Start at [`docs/README.md`](docs/README.md).

---

## Setup

Clone the repository:

```bash
git clone https://github.com/your-username/DrugGPT.git

cd DrugGPT
```

Create a virtual environment:

```bash
conda create -n ai python=3.11

conda activate ai
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your `.env` file:

```bash
cp .env.example .env
```

Add your API keys.

This project uses Supabase Auth for accounts. Set `SUPABASE_URL`,
`SUPABASE_PUBLISHABLE_KEY`, and `SUPABASE_SECRET_KEY` in `.env`, then either
sign up from the Streamlit login screen or configure
`BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD` for a first admin account.
See [docs/setup.md](docs/setup.md#3b-authentication-supabase).

---

## Index the Medical Books

Put your PDF files in the folder set by `MEDICAL_BOOKS_DIR` (by default
`Medical Books/`), then run:

```bash
# Check the PDFs and chunk counts without uploading
python -m scripts.ingest --dry-run

# Build the medical knowledge base
python -m scripts.ingest --reset

# Verify retrieval and the medical-only guard
python -m test.vector_db_test
```

Pinecone embeds the text with NVIDIA `llama-text-embed-v2` on the server.
No local model download is needed. See
[docs/vector-db-guide.md](docs/vector-db-guide.md) for the full visual guide.

## Run the Backend

```bash
uvicorn backend.main:app --reload
```

## Run the Frontend

```bash
streamlit run frontend/streamlit_app.py
```

---

## Roadmap

### Phase 1

* Basic Medical RAG
* Pinecone Retrieval
* FastAPI Backend
* Streamlit UI

### Phase 2

* Streaming Responses
* Human-in-the-loop approvals
* Long-term memory
* Conversation summarization

### Phase 3

* Multi-Agent System
* Drug Search Tool
* Symptom Analysis Tool
* Medical Calculator Tool
* Web Search Integration

### Phase 4

* Multi-modal Inputs
* Medical Reports
* Image-based Diagnosis Research

---

## Open Source Contributions

This project is student-friendly.

If you are:

* Learning LangGraph
* Learning RAG
* Learning LLM Engineering
* Looking for your first open-source contribution

you are welcome here.

Some beginner-friendly contribution ideas:

* Improve UI
* Better prompts
* Add citations
* Add memory
* Improve retrieval quality
* Add evaluation metrics
* Improve documentation

No contribution is too small.

---

## Disclaimer

This project is for educational and research purposes only.

It is NOT a replacement for professional medical advice, diagnosis, or treatment.

Always consult qualified healthcare professionals for medical decisions.

---

## Built By Students, For Students

If you're learning AI Engineering, Data Science, MLOps, or Generative AI and want to contribute, feel free to open an issue or submit a pull request.

Let's build cool stuff and learn together 🚀
