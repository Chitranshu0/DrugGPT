# DrugGPT

DrugGPT is a source-grounded assistant for **medical science and drug-study research**. It automatically searches locally indexed medical PDFs, answers only when relevant evidence is found, and displays the supporting source and page for every answer.

It is designed for students and researchers. It is not a diagnostic, prescribing, or emergency-care service.

## What it does

- FastAPI backend with typed JSON chat responses
- Streamlit research chat interface with visible RAG tool activity and source cards
- Local ChromaDB vector index for licensed medical PDFs
- LangGraph-orchestrated `search_medical_sources` tool
- Educational-only scope and safety guardrails
- Clinician medication-review workflow with approval/rejection
- Pytest and Ruff configuration for repeatable development
- Single-command entrypoint via `main.py`

## Architecture

`Streamlit UI → FastAPI → scope/safety gate → search_medical_sources → ChromaDB → grounded LLM answer + citations`

The project code lives in `src` (imported as `src.*`); local PDFs, the Chroma index, and chat checkpoints live under the untracked `data/` directory.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -e '.[dev]'
cp .env.example .env
mkdir -p data/raw
# Copy only licensed medical PDFs into data/raw/

# Terminal 1: FastAPI backend (:8000)
python main.py

# Terminal 2: Streamlit frontend (:8501)
python app.py
```

### Individual commands

| Command | What it does |
|---------|--------------|
| `python main.py` | FastAPI backend only (:8000) |
| `python app.py` | Streamlit frontend only (:8501) |
| `python main.py --reload` | Backend with auto-reload |
| `python app.py --api-url http://localhost:8000 --port 8502` | Frontend pointing at a custom backend |
| `druggpt index` | rebuild Chroma index from `data/raw` |
| `druggpt check` | resolved config + API health |
| `druggpt test` | run the pytest suite |

## Safety and limitations

DrugGPT answers medical science and drug-study questions only. It declines unrelated questions, patient-specific diagnosis/dosing/treatment requests, and urgent-care situations. If no indexed source sufficiently supports a question, it asks for a narrower rephrase rather than inventing an answer. Verify research conclusions against the original materials and qualified professionals.

## Documentation

- [Architecture](docs/architecture.md)
- [Setup and configuration](docs/setup.md)
- [API reference](docs/api.md)
- [RAG and source-data workflow](docs/rag-and-data.md)
- [Safety and scope](docs/safety-and-scope.md)
- [Development guide](docs/development.md)
- [Architecture decision records](docs/adr/0001-local-chroma-source-grounded-rag.md)
