"""Typed data exchanged between retrieval, RAG, and API layers."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class ChatStatus(StrEnum):
    ANSWERED = "answered"
    OUT_OF_SCOPE = "out_of_scope"
    SAFETY_REFUSAL = "safety_refusal"
    REVIEW_PENDING = "review_pending"
    EMERGENCY_GUIDANCE = "emergency_guidance"
    NEEDS_MORE_INFORMATION = "needs_more_information"


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


class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    date_of_birth: str | None = None
    sex: str | None = Field(default=None, max_length=50)


class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    date_of_birth: str | None = None
    sex: str | None = Field(default=None, max_length=50)


class Patient(BaseModel):
    id: str
    name: str
    date_of_birth: str | None = None
    sex: str | None = None
    created_at: str
    updated_at: str


class PatientFactCreate(BaseModel):
    category: str = Field(pattern="^(allergy|condition|medication|history|preference)$")
    value: str = Field(min_length=1, max_length=1000)
    approved: bool = False


class PatientFact(BaseModel):
    id: str
    category: str
    value: str
    approved: bool
    created_at: str


class PatientSummary(BaseModel):
    patient: Patient
    summary: str | None = None
    facts: list[PatientFact] = []


class ConversationCreate(BaseModel):
    patient_id: str
    title: str = Field(default="New medical chat", min_length=1, max_length=160)


class Conversation(BaseModel):
    id: str
    patient_id: str
    title: str
    created_at: str
    updated_at: str


class ConversationMessage(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    status: str | None = None
    created_at: str
    metadata: dict = {}


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reviewer_name: str = Field(min_length=1, max_length=120)
    approved_guidance: str | None = Field(default=None, max_length=4000)
    reviewer_note: str | None = Field(default=None, max_length=2000)


class MedicationReview(BaseModel):
    id: str
    patient_id: str
    conversation_id: str
    message_id: str
    status: str
    draft_guidance: str
    reviewer_name: str | None = None
    reviewer_note: str | None = None
    approved_guidance: str | None = None
    created_at: str
    updated_at: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation] = []
    tool_activity: ToolActivity | None = None
    status: ChatStatus
    thread_id: str
    review_id: str | None = None
    review_status: str | None = None
    answer_mode: str = "general_education"


class DatabaseStatus(BaseModel):
    ready: bool
    chunks_indexed: int
    documents_indexed: int = 0
