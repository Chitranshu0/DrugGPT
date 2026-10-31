"""Chat endpoint: runs the RAG graph and streams UI events.

The response is newline-delimited JSON (NDJSON). Each line is one event:

    {"type": "thinking", "label": "..."}
    {"type": "tool_call", "tool": {...}}
    {"type": "tool_result", "tool": {...}, "sources": [...]}
    {"type": "answer", "content": "..."}
    {"type": "error", "message": "..."}
    {"type": "done"}

The Streamlit UI consumes these events to render Claude-style tool cards.
"""

import json
import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from backend.api.schemas import ChatRequest
from backend.memory import conversations
from backend.rag.generation import TOOL_NAME, TOOL_TITLE

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


def _event(payload: dict) -> str:
    """Serialize one UI event as a single NDJSON line."""
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _tool_summary(sources: list[dict]) -> str:
    """Describe the retrieval result for the tool card."""
    count = len(sources)
    if count == 0:
        return "No matching passages found"
    if count == 1:
        return "Found 1 relevant passage"
    return f"Found {count} relevant passages"


def _tool_payload(message: str, status: str, summary: str = "") -> dict:
    """Build the tool metadata sent to the UI."""
    tool = {
        "name": TOOL_NAME,
        "title": TOOL_TITLE,
        "input": {"question": message},
        "status": status,
    }
    if summary:
        tool["summary"] = summary
    return tool


async def generate_response(graph, message: str, thread_id: str):
    """Run the graph and stream status, tool, source, and answer events."""
    config = {"configurable": {"thread_id": thread_id}}

    yield _event(
        {"type": "thinking", "label": "Thinking about your question..."}
    )
    yield _event(
        {
            "type": "tool_call",
            "tool": _tool_payload(message, "running"),
        }
    )

    try:
        result = await graph.ainvoke(
            {
                "question": message,
                "messages": [HumanMessage(content=message)],
            },
            config=config,
        )
    except Exception:
        logger.exception("Chat generation failed for thread %s", thread_id)
        yield _event(
            {
                "type": "error",
                "message": (
                    "Sorry, something went wrong while generating the answer."
                ),
            }
        )
        return

    await conversations.record_turn(thread_id, message)

    sources = result.get("sources", []) or []
    yield _event(
        {
            "type": "tool_result",
            "tool": _tool_payload(
                message, "completed", _tool_summary(sources)
            ),
            "sources": sources,
        }
    )
    yield _event({"type": "answer", "content": result["answer"]})
    yield _event({"type": "done"})


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request):
    """Answer a medical question using retrieved context."""
    thread_id = payload.thread_id or str(uuid.uuid4())

    # Create the metadata row before generation so a new chat appears in the
    # sidebar even if the first answer takes a while.
    await conversations.ensure_thread(thread_id)

    return StreamingResponse(
        generate_response(request.app.state.graph, payload.message, thread_id),
        media_type="application/x-ndjson",
        headers={"X-Thread-ID": thread_id},
    )
