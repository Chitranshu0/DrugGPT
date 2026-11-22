"""Conversations, chat turns and token streaming."""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.deps import get_or_404
from src.core.models import (
    ChatResponse,
    Conversation,
    ConversationCreate,
    ConversationMessage,
    MessageRequest,
)
from src.rag.service import MedicalRAGService

logger = logging.getLogger("druggpt.api")


def make_router(service: MedicalRAGService) -> APIRouter:
    router = APIRouter(prefix="/conversations", tags=["Chat"])

    @router.post(
        "",
        response_model=Conversation,
        status_code=201,
        tags=["Chat"],
        summary="Create a conversation",
    )
    def create_conversation(request: ConversationCreate) -> Conversation:
        logger.info("Creating conversation for patient %s (title=%r)", request.patient_id, request.title)
        conversation = get_or_404(
            lambda: service.store.create_conversation(request.patient_id, request.title)
        )
        logger.info(
            "Conversation %s created for patient %s - awaiting messages",
            conversation.id,
            request.patient_id,
        )
        return conversation

    @router.get(
        "/{conversation_id}/messages",
        response_model=list[ConversationMessage],
        tags=["Chat"],
        summary="List conversation messages",
    )
    def list_messages(conversation_id: str) -> list[ConversationMessage]:
        return get_or_404(lambda: service.store.list_messages(conversation_id))

    @router.get(
        "/{conversation_id}/messages/since",
        tags=["Chat"],
        summary="List only messages added after a given message id",
    )
    def list_messages_since(conversation_id: str, after: str | None = None) -> dict[str, object]:
        """Cheap polling payload for incremental transcript updates."""
        messages = get_or_404(lambda: service.store.list_messages(conversation_id))
        version = len(messages)
        if after:
            positions = [index for index, message in enumerate(messages) if message.id == after]
            if positions:
                messages = messages[positions[-1] + 1 :]
        return {
            "messages": [message.model_dump(mode="json") for message in messages],
            "version": version,
        }

    @router.post(
        "/{conversation_id}/messages",
        response_model=ChatResponse,
        tags=["Chat"],
        summary="Send a chat message",
        description=(
            "Run one turn of the medical assistant. Returns an educational or clarifying answer "
            "immediately, or a `review_pending` response with a `review_id` when a clinician "
            "must review a personal decision about a medicine, test, treatment, or report."
        ),
    )
    def send_message(conversation_id: str, request: MessageRequest) -> ChatResponse:
        logger.info(
            "Chat request received for conversation %s (%d chars) - handing to the RAG service",
            conversation_id,
            len(request.message),
        )
        try:
            response = service.send_message(conversation_id, request.message)
        except KeyError as error:
            logger.warning("Cannot process message: conversation %s does not exist", conversation_id)
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RuntimeError as error:
            logger.error("Chat generation failed for conversation %s (%s)", conversation_id, error)
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:  # safety net: never leak a raw 500 traceback to clients
            logger.exception("Unexpected error while processing conversation %s", conversation_id)
            raise HTTPException(
                status_code=500,
                detail="Internal server error while generating a response. Check the server logs.",
            ) from error
        logger.info(
            "Reply sent for conversation %s - status=%s, answer_mode=%s",
            conversation_id,
            response.status.value,
            response.answer_mode,
        )
        return response

    @router.post(
        "/{conversation_id}/messages/stream",
        tags=["Chat"],
        summary="Send a chat message and stream the answer as server-sent events",
        description=(
            "Emits `{\"type\": \"token\", \"token\": \"...\"}` events followed by one "
            "`{\"type\": \"response\", \"response\": {...}}` event carrying the same "
            "`ChatResponse` as the non-stream endpoint. Guardrail and clinician-review "
            "routes emit only the terminal response event."
        ),
    )
    def send_message_stream(conversation_id: str, request: MessageRequest) -> StreamingResponse:
        def events():
            try:
                for event in service.send_message_stream(conversation_id, request.message):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            except KeyError as error:
                logger.warning("Cannot stream message: conversation %s does not exist", conversation_id)
                yield f"data: {json.dumps({'type': 'error', 'detail': str(error)})}\n\n"
            except RuntimeError as error:
                logger.error("Streaming generation failed for conversation %s (%s)", conversation_id, error)
                yield f"data: {json.dumps({'type': 'error', 'detail': str(error), 'status': 503})}\n\n"
            except Exception:  # safety net
                logger.exception("Unexpected error streaming conversation %s", conversation_id)
                yield f"data: {json.dumps({'type': 'error', 'detail': 'Internal server error.'})}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    return router
