"""Request and response models for the API."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """A user question plus the conversation it belongs to."""

    message: str
    thread_id: str | None = None


class MessageOut(BaseModel):
    """One persisted chat message."""

    role: str
    content: str


class ThreadSummary(BaseModel):
    """Conversation metadata shown in the chat sidebar."""

    thread_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ThreadDetail(ThreadSummary):
    """A conversation plus its persisted messages."""

    messages: list[MessageOut]
    pending_interrupt: Any | None = None


class ThreadRenameRequest(BaseModel):
    """New title for an existing conversation."""

    title: str = Field(min_length=1, max_length=200)


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
