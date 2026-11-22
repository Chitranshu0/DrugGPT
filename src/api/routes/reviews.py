"""Clinician review queue and decisions."""

import logging

from fastapi import APIRouter, HTTPException

from src.api.deps import get_or_404
from src.core.models import ChatResponse, MedicationReview, ReviewDecisionRequest
from src.rag.service import MedicalRAGService

logger = logging.getLogger("druggpt.api")


def make_router(service: MedicalRAGService) -> APIRouter:
    router = APIRouter(prefix="/reviews", tags=["Reviews"])

    @router.get(
        "",
        response_model=list[MedicationReview],
        tags=["Reviews"],
        summary="List reviews",
    )
    def list_reviews(status: str = "pending") -> list[MedicationReview]:
        return service.store.list_reviews(status)

    @router.get("/{review_id}", tags=["Reviews"], summary="Get a review with context")
    def get_review(review_id: str) -> dict:
        review = get_or_404(lambda: service.store.get_review(review_id))
        return {"review": review, "context": service.store.review_context(review_id)}

    @router.post(
        "/{review_id}/decision",
        response_model=ChatResponse,
        tags=["Reviews"],
        summary="Record a clinician decision and resume the chat",
        description=(
            "Approve or reject pending medication guidance. On approval, `approved_guidance` "
            "is required and becomes the assistant's reply."
        ),
    )
    def decide_review(review_id: str, request: ReviewDecisionRequest) -> ChatResponse:
        logger.info(
            "Recording clinician decision on review %s: %s by %s",
            review_id,
            request.decision,
            request.reviewer_name,
        )
        try:
            review = service.store.decide_review(
                review_id,
                request.decision,
                request.reviewer_name,
                request.reviewer_note,
                request.approved_guidance,
            )
            response = service.resume_review(review)
        except KeyError as error:
            logger.warning("Cannot decide review %s: no such review exists", review_id)
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            logger.warning("Review %s cannot be decided as %s: %s", review_id, request.decision, error)
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RuntimeError as error:
            logger.error("Resuming chat after review %s failed: %s", review_id, error)
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:
            logger.exception("Unexpected error while deciding review %s", review_id)
            raise HTTPException(
                status_code=500,
                detail="Internal server error while recording the review decision.",
            ) from error
        logger.info(
            "Review %s marked %s - chat resumed (status=%s, answer_mode=%s)",
            review_id,
            request.decision,
            response.status.value,
            response.answer_mode,
        )
        return response

    return router
