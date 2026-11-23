"""DrugGPT backend package.

Layers:
    api/        -> HTTP routes and request/response models
    core/       -> settings and shared model setup
    rag/        -> retrieval, generation, and the LangGraph workflow
    ingestion/  -> PDF -> Pinecone indexing
"""

__version__ = "1.0"
