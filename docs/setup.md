# Setup and configuration

## Requirements

Python 3.11+, a Groq API key, and medical PDFs that you are authorized to index.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
mkdir -p data/raw
```

Put PDFs in `data/raw`, then start the API with `uvicorn druggpt.api.app:app --reload`. Start the interface with `streamlit run src/druggpt/ui/app.py` and rebuild the index from its sidebar.

## Settings

`GROQ_API_KEY` is required for generated answers. `DRUGGPT_DATA_DIR` defaults to `data`; `DRUGGPT_API_URL` defaults to `http://127.0.0.1:8000`; `DRUGGPT_RELEVANCE_THRESHOLD` defaults to `0.35`; and `DRUGGPT_RETRIEVAL_K` defaults to `5`.

If the index is unavailable, confirm that PDFs are in `data/raw` and rebuild it. If chat generation fails, verify `GROQ_API_KEY` and network access to Groq.
