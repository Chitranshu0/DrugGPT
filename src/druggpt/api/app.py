"""HTTP API for DrugGPT."""

from fastapi import FastAPI, HTTPException

from druggpt.core.models import ChatRequest, ChatResponse, DatabaseStatus
from druggpt.rag.indexing import rebuild_index
from druggpt.rag.retrieval import VectorDatabaseNotReadyError
from druggpt.rag.service import MedicalRAGService


def create_app(service: MedicalRAGService | None = None) -> FastAPI:
    app = FastAPI(title="DrugGPT", version="2.0.0", description="Source-grounded medical study RAG API")
    rag_service = service or MedicalRAGService()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "running"}

    @app.get("/vector-db/status", response_model=DatabaseStatus)
    def vector_database_status() -> DatabaseStatus:
        return rag_service.retriever.status()

    @app.post("/vector-db/rebuild")
    def rebuild_vector_database() -> dict[str, int | str]:
        try:
            return rebuild_index(rag_service.settings)
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        try:
            return rag_service.answer(request.message, request.thread_id)
        except VectorDatabaseNotReadyError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    return app


app = create_app()
