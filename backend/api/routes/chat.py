"""Chat endpoint: runs the RAG graph and streams the answer."""

<<<<<<< HEAD
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.schemas import ChatRequest
from backend.rag.graph import graph

router = APIRouter(tags=["chat"])


async def generate_response(message: str, thread_id: str):
    """Run the graph and yield the final answer."""
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"question": message}, config=config)

=======
import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from backend.api.schemas import ChatRequest
from backend.memory import conversations

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


async def generate_response(graph, message: str, thread_id: str):
    """Run the graph, record the turn, and yield the final answer."""
    config = {"configurable": {"thread_id": thread_id}}

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
        yield "Sorry, something went wrong while generating the answer."
        return

    await conversations.record_turn(thread_id, message)
>>>>>>> fix/RAG
    yield result["answer"]


@router.post("/chat")
<<<<<<< HEAD
async def chat(request: ChatRequest):
    """Answer a medical question using retrieved context."""
    return StreamingResponse(
        generate_response(request.message, request.thread_id),
        media_type="text/plain",
=======
async def chat(payload: ChatRequest, request: Request):
    """Answer a medical question using retrieved context."""
    thread_id = payload.thread_id or str(uuid.uuid4())

    # Create the metadata row before generation so a new chat appears in the
    # sidebar even if the first answer takes a while.
    await conversations.ensure_thread(thread_id)

    return StreamingResponse(
        generate_response(request.app.state.graph, payload.message, thread_id),
        media_type="text/plain",
        headers={"X-Thread-ID": thread_id},
>>>>>>> fix/RAG
    )
