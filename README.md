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
* Conversation memory

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

* Pinecone Vector Database

### Observability

* LangSmith

### Document Processing

* PyMuPDF

---

## Project Structure

```bash
DrugGPT/
│
├── RAG_pipeline/
│   ├── graph.py
│   ├── rag.py
│   ├── retriever.py
│   ├── vector_db.py
│   ├── state.py
│   ├── main.py
│   ├── frontend.py
│   └── requirements.txt
│
├── .env.example
├── README.md
└── .gitignore
```

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
pip install -r RAG_pipeline/requirements.txt
```

Create your `.env` file:

```bash
cp .env.example .env
```

Add your API keys.

---

## Run the Backend

```bash
cd RAG_pipeline

python -m uvicorn main:app --reload
```

---

## Run the Frontend

```bash
streamlit run frontend.py
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
* SQLite/Postgres Memory
* Resume Conversations

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
