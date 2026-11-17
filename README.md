# DrugGPT

DrugGPT is a source-grounded assistant for **medical science and drug-study research**. It automatically searches locally indexed medical PDFs, answers only when relevant evidence is found, and displays the supporting source and page for every answer.

It is designed for students and researchers. It is not a diagnostic, prescribing, or emergency-care service.

## What it does

- FastAPI backend with typed JSON chat responses
- Streamlit research chat interface with visible RAG tool activity and source cards
- Local ChromaDB vector index for licensed medical PDFs
- LangGraph-orchestrated `search_medical_sources` tool
- Educational-only scope and safety guardrails
- Clinician medication-review and free-text chat workflow
- Pytest and Ruff configuration for repeatable development
- Two entrypoints: `uvicorn main:app` (backend) and `streamlit run` (frontend)

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
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Streamlit frontend (:8501)
streamlit run src/ui/Patient_Chat.py --server.port 8501
```

### Individual commands

| Command | What it does |
|---------|--------------|
| `uvicorn main:app --reload` | FastAPI backend only (:8000) |
| `streamlit run src/ui/Patient_Chat.py --server.port 8501` | Streamlit frontend only (:8501) |
| `python -m src.cli index` | rebuild Chroma index from `data/raw` |
| `python -m src.cli check` | resolved config + API health |
| `python -m src.cli test` | run the pytest suite |

There is no `python main.py` or `python app.py`; run uvicorn and Streamlit directly.

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
