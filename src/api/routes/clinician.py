"""Clinician transcript and direct reply endpoints."""

import logging

from fastapi import APIRouter, HTTPException

from src.api.deps import get_or_404
from src.core.models import ChatResponse, ClinicianReplyRequest
from src.rag.service import MedicalRAGService

logger = logging.getLogger("druggpt.api")


def make_router(service: MedicalRAGService) -> APIRouter:
    router = APIRouter(prefix="/conversations", tags=["Clinician"])

    @router.get(
        "/{conversation_id}/transcript",
        tags=["Clinician"],
        summary="Full transcript plus any open review and its issue context",
    )
    def conversation_transcript(conversation_id: str) -> dict:
        """Return every message plus the open medication review (if any) and its context."""
        get_or_404(lambda: service.store.get_conversation(conversation_id))
        messages = service.store.list_messages(conversation_id)
        open_review = service.store.open_review_for_conversation(conversation_id)
        context = None
        if open_review is not None:
            context = service.store.review_context(open_review.id)
        return {
            "messages": [m.model_dump(mode="json") for m in messages],
            "open_review": open_review.model_dump(mode="json") if open_review else None,
            "context": context,
        }

    @router.post(
        "/{conversation_id}/clinician-reply",
        response_model=ChatResponse,
        tags=["Clinician"],
        summary="Record a clinician's free-text reply",
    )
    def clinician_reply(conversation_id: str, request: ClinicianReplyRequest) -> ChatResponse:
        """A clinician writes directly into the conversation. Closes any pending review first."""
        logger.info(
            "Clinician %s replying in conversation %s (%d chars) - closing any open review",
            request.reviewer_name,
            conversation_id,
            len(request.message),
        )
        try:
            return service.reply_as_clinician(
                conversation_id,
                request.message,
                request.reviewer_name,
                request.review_id,
            )
        except KeyError as error:
            logger.warning("Cannot post clinician reply: conversation %s does not exist", conversation_id)
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            logger.warning("Clinician reply for conversation %s rejected: %s", conversation_id, error)
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RuntimeError as error:
            logger.error("Clinician reply for conversation %s failed: %s", conversation_id, error)
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:  # safety net
            logger.exception("Unexpected error recording clinician reply for %s", conversation_id)
            raise HTTPException(
                status_code=500, detail="Internal server error while recording the clinician reply."
            ) from error

    return router
