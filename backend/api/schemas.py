"""Request and response models for the API."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """A user question plus the conversation it belongs to."""

    message: str
    thread_id: str | None = None


class SourceOut(BaseModel):
    """One retrieved medical reference shown under an answer."""

    title: str = ""
    source: str = ""
    page: int | None = None
    score: float = 0.0
    signals: list[str] = Field(default_factory=list)


class ToolCallOut(BaseModel):
    """One tool invocation rendered as a card in the UI."""

    name: str
    title: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"
    summary: str = ""


class MessageOut(BaseModel):
    """One persisted chat message."""

    role: str
    content: str
    sources: list[SourceOut] = Field(default_factory=list)
    tool_calls: list[ToolCallOut] = Field(default_factory=list)


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


class AuthUser(BaseModel):
    """The signed-in account, as exposed to clients."""

    id: str
    email: str = ""
    is_admin: bool = False


class AuthSignupRequest(BaseModel):
    """Credentials for creating a new account."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=6, max_length=200)


class AuthLoginRequest(BaseModel):
    """Credentials for an existing account."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=200)


class AuthRefreshRequest(BaseModel):
    """Refresh token from a previous sign-in."""

    refresh_token: str = Field(min_length=1)


class AuthSession(BaseModel):
    """Tokens plus the user profile returned by sign-in and refresh."""

    access_token: str
    refresh_token: str
    expires_at: int | None = None
    expires_in: int | None = None
    token_type: str = "bearer"
    user: AuthUser


class AuthSignupResponse(BaseModel):
    """Either a session, or a request to confirm the email address."""

    requires_confirmation: bool = False
    user: AuthUser
    session: AuthSession | None = None


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
