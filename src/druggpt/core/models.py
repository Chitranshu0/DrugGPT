"""Typed data exchanged between retrieval, RAG, and API layers."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class ChatStatus(StrEnum):
    ANSWERED = "answered"
    REPHRASE_REQUIRED = "rephrase_required"
    OUT_OF_SCOPE = "out_of_scope"
    SAFETY_REFUSAL = "safety_refusal"


@dataclass(frozen=True)
class Evidence:
    content: str
    source_path: str
    source_title: str
    page: int | None
    score: float


class SourceCitation(BaseModel):
    id: int
    title: str
    path: str
    page: int | None = None
    excerpt: str
    relevance_score: float = Field(ge=0, le=1)


class ToolActivity(BaseModel):
    tool_name: str
    message: str
    sources_found: int = 0


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    thread_id: str = Field(min_length=1, max_length=128)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation] = []
    tool_activity: ToolActivity | None = None
    status: ChatStatus
    thread_id: str


class DatabaseStatus(BaseModel):
    ready: bool
    chunks_indexed: int
    documents_indexed: int = 0
