# Architecture

DrugGPT is a local-first, source-grounded research application.

## Components

- `druggpt.api`: FastAPI application and HTTP boundary.
- `druggpt.core`: settings and typed shared API/domain models.
- `druggpt.rag`: guardrails, PDF indexing, Chroma retrieval, LangGraph tool orchestration, and citation mapping.
- `druggpt.ui`: Streamlit application and testable HTTP client.

## Request flow

1. The UI posts `message` and `thread_id` to `POST /chat`.
2. The deterministic guardrail permits a medical/drug-study research question, rejects non-medical prompts, or refuses personal/urgent clinical requests.
3. LangGraph invokes the `search_medical_sources` tool.
4. Chroma returns chunks with their PDF path, page metadata, and relevance score.
5. Only chunks meeting the configured score threshold are passed to the LLM.
6. The API returns the answer, tool activity, status, and citation records together.

## Persistence

`data/raw` holds local licensed PDFs; `data/chroma` holds the disposable Chroma index; `data/checkpoints` is reserved for local conversation checkpoints. None are committed to Git.
