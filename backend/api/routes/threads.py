"""Thread endpoints: list, create, inspect, rename, and delete chats."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from langchain_core.messages import BaseMessage

from backend.api.schemas import (
    MessageOut,
    ThreadDetail,
    ThreadRenameRequest,
    ThreadSummary,
)
from backend.memory import conversations

router = APIRouter(prefix="/threads", tags=["threads"])

ROLE_NAMES = {
    "human": "user",
    "ai": "assistant",
}


def _message_text(message: BaseMessage) -> str:
    """Return plain text from a message, ignoring non-text content blocks."""
    if isinstance(message.content, str):
        return message.content

    parts: list[str] = []
    for block in message.content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            text = block.get("text")
            if text:
                parts.append(str(text))
    return " ".join(parts)


def _serialize_message(message: BaseMessage) -> MessageOut:
    """Convert a LangChain message into the API shape."""
    return MessageOut(
        role=ROLE_NAMES.get(message.type, message.type),
        content=_message_text(message),
    )


async def _load_messages(request: Request, thread_id: str) -> list[MessageOut]:
    """Read persisted messages from the LangGraph checkpoint."""
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = await graph.aget_state(config)
    messages: list[Any] = snapshot.values.get("messages", [])
    return [_serialize_message(message) for message in messages]


@router.get("", response_model=list[ThreadSummary])
async def list_threads() -> list[ThreadSummary]:
    """Return all conversations, most recently active first."""
    rows = await conversations.list_threads()
    return [ThreadSummary(**row) for row in rows]


@router.post("", response_model=ThreadSummary, status_code=status.HTTP_201_CREATED)
async def create_thread() -> ThreadSummary:
    """Create an empty conversation and return its id."""
    row = await conversations.create_thread(str(uuid.uuid4()))
    return ThreadSummary(**row)


@router.get("/{thread_id}", response_model=ThreadDetail)
async def get_thread(thread_id: str, request: Request) -> ThreadDetail:
    """Return one conversation with its persisted messages."""
    row = await conversations.get_thread(thread_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    messages = await _load_messages(request, thread_id)

    return ThreadDetail(
        **row,
        messages=messages,
        pending_interrupt=None,
    )


@router.patch("/{thread_id}", response_model=ThreadSummary)
async def rename_thread(
    thread_id: str,
    payload: ThreadRenameRequest,
) -> ThreadSummary:
    """Rename a conversation."""
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    renamed = await conversations.rename_thread(thread_id, title)
    if not renamed:
        raise HTTPException(status_code=404, detail="Thread not found")

    row = await conversations.get_thread(thread_id)
    return ThreadSummary(**row)


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(thread_id: str, request: Request) -> Response:
    """Delete a conversation and all of its persisted graph state."""
    row = await conversations.get_thread(thread_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    checkpointer = request.app.state.checkpointer
    await checkpointer.adelete_thread(thread_id)
    await conversations.delete_thread(thread_id)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
