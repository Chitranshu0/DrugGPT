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
* Text chunking
* Embedding generation
* Pinecone vector database
* Semantic search
* RAG pipeline
* LangGraph workflow
* FastAPI backend
* Streamlit frontend
* LangSmith tracing
* SQLite conversation persistence
* Multiple chat threads with resume
* Message history across restarts

---

## Tech Stack

### AI

* LangChain
* LangGraph
* Groq (Llama 3.1)
* Sentence Transformers

### Backend

* FastAPI

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
│   │   ├── schemas.py           # Request/response models
│   │   └── routes/
│   │       ├── chat.py          # POST /chat
│   │       ├── threads.py       # Chat list, history, rename, delete
│   │       └── health.py        # GET /health, /healthz
│   ├── core/
│   │   ├── config.py            # All environment settings
│   │   └── embeddings.py        # Shared HuggingFace embedding model
│   ├── memory/
│   │   ├── db.py                # SQLite setup and schema
│   │   └── conversations.py     # Thread metadata CRUD
│   ├── rag/
│   │   ├── state.py             # State shared between graph nodes
│   │   ├── retrieval.py         # Search Pinecone
│   │   ├── generation.py        # Context + history + LLM answer
│   │   └── graph.py             # LangGraph workflow
│   └── ingestion/
│       └── vector_db.py         # PDF -> Pinecone
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
    v
FastAPI /threads and /chat  (backend/api/routes/)
    |
    v
LangGraph workflow  (backend/rag/graph.py)
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

---

## Index the Medical Books (first time only)

Put your PDF files in the `Medical Books/` folder, then run:

```bash
python -m scripts.ingest
```

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
