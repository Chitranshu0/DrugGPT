"""Chat endpoint: runs the RAG graph and streams the answer."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.api.schemas import ChatRequest
from backend.rag.graph import graph

router = APIRouter(tags=["chat"])


async def generate_response(message: str, thread_id: str):
    """Run the graph and yield the final answer."""
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"question": message}, config=config)

    yield result["answer"]


@router.post("/chat")
async def chat(request: ChatRequest):
    """Answer a medical question using retrieved context."""
    return StreamingResponse(
        generate_response(request.message, request.thread_id),
        media_type="text/plain",
    )
