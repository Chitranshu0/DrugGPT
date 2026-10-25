"""Request and response models for the API."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """A user question plus the conversation it belongs to."""

    message: str
    thread_id: str


class HealthResponse(BaseModel):
    """Small status payload used by health checks."""

    status: str
    service: str
    version: str


class ModelInfo(BaseModel):
    """One model in an OpenAI-compatible model list."""

    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "groq"


class ModelListResponse(BaseModel):
    """OpenAI-compatible GET /v1/models response."""

    object: str = "list"
    data: list[ModelInfo]
