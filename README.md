# DrugGPT

DrugGPT is a source-grounded assistant for **medical science and drug-study research**. It automatically searches locally indexed medical PDFs, prefers source-grounded answers when relevant evidence is found, and falls back to general educational information otherwise. It displays the supporting source and page for every grounded answer.

It is designed for students and researchers. It is not a diagnostic, prescribing, or emergency-care service.

## What it does

- FastAPI backend with typed JSON chat responses
- Streamlit chat interface with visible RAG tool activity and source cards
- Local ChromaDB vector index for licensed medical PDFs
- LangGraph state graph that routes each message: triage → context → RAG answer / clarification / emergency / clinician review
- Deterministic safety guardrails; RAG is invoked only for educational questions
- Human-in-the-loop for personal decisions about medicines, tests, treatments, and test reports
- Educational-only scope — not a diagnostic, prescribing, or emergency-care service
- Pytest and Ruff configuration for repeatable development
- Two entrypoints: `uvicorn main:app` (backend) and `streamlit run` (frontend)

## Architecture

`Streamlit UI → FastAPI → LangGraph triage → context → (RAG answer | clarification | emergency/scope | clinician review) → ChatResponse`

LangGraph owns the conversation flow; FastAPI owns the HTTP boundary. RAG (`search_medical_sources` → ChromaDB) is invoked only on the educational/symptom path. Personal clinical decisions pause for a human clinician before any guidance is shown. See [the architecture doc](docs/architecture.md) for the full flow diagram.

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

**Upgrading an existing checkout:** run `python -m src.cli index` once. The index now uses cosine similarity, normalized embeddings and relative citation paths; older L2 indexes are detected as needing a rebuild and will not produce citations until recreated.

Chat answers can also be streamed through `POST /conversations/{id}/messages/stream` (server-sent events); guardrails and clinician review are unchanged.

## Safety and limitations

DrugGPT answers medical science and drug-study questions only. It declines unrelated questions, patient-specific diagnosis/dosing/treatment requests, and urgent-care situations. If no indexed source sufficiently supports a question, it provides general educational information rather than inventing an answer. Verify research conclusions against the original materials and qualified professionals.

## Documentation

- [Architecture](docs/architecture.md)
- [Setup and configuration](docs/setup.md)
- [API reference](docs/api.md)
- [RAG and source-data workflow](docs/rag-and-data.md)
- [Safety and scope](docs/safety-and-scope.md)
- [Development guide](docs/development.md)
- [Architecture decision records](docs/adr/0001-local-chroma-source-grounded-rag.md)
