"""HTTP API for the local DrugGPT development workflow.

This module exposes a small, typed REST surface around
:class:`src.rag.service.MedicalRAGService`. Every route is tagged and
documented so the interactive Swagger UI at ``/docs`` reads like a real
developer console instead of a bare endpoint list.
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from src.core.models import (
    ChatRequest,
    ChatResponse,
    Conversation,
    ConversationCreate,
    ConversationMessage,
    DatabaseStatus,
    MedicationReview,
    MessageRequest,
    Patient,
    PatientCreate,
    PatientFact,
    PatientFactCreate,
    PatientSummary,
    PatientUpdate,
    ReviewDecisionRequest,
)
from src.rag.indexing import rebuild_index
from src.rag.service import MedicalRAGService

logger = logging.getLogger("druggpt.api")

TAGS_METADATA = [
    {
        "name": "Meta",
        "description": "Liveness and discovery endpoints. Start here when wiring up a client.",
    },
    {
        "name": "Index",
        "description": "Inspect or rebuild the local vector index built from PDFs in `data/raw`.",
    },
    {
        "name": "Patients",
        "description": "Create and manage the local patient records that conversations attach to.",
    },
    {
        "name": "Chat",
        "description": (
            "Send messages and read conversation history. A message may return an immediate "
            "answer or a `review_pending` status when clinician review is required."
        ),
    },
    {
        "name": "Reviews",
        "description": "List pending medication reviews and record a clinician decision to resume a chat.",
    },
]


def create_app(service: MedicalRAGService | None = None) -> FastAPI:
    """Build the FastAPI application.

    ``service`` is injectable so tests can supply fakes; in normal operation a
    real :class:`MedicalRAGService` is constructed from environment settings.
    """
    app = FastAPI(
        title="DrugGPT API",
        version="3.0.0",
        description=(
            "Local, development-only medical education and clinician-review API.\n\n"
            "**Typical flow**\n"
            "1. `POST /patients` to create a patient.\n"
            "2. `POST /conversations` with that patient id.\n"
            "3. `POST /conversations/{conversation_id}/messages` to chat.\n"
            "4. If the response status is `review_pending`, decide it with "
            "`POST /reviews/{review_id}/decision`.\n\n"
            "This service is **not** a medical device and must not be used for real clinical decisions."
        ),
        contact={
            "name": "DrugGPT maintainers",
            "url": "https://github.com/",
        },
        license_info={"name": "MIT"},
        terms_of_service="https://github.com/",
        openapi_tags=TAGS_METADATA,
    )
    rag_service = service or MedicalRAGService()
    logger.info("DrugGPT API application constructed (model=%s)", rag_service.settings.llm_model)

    def get_or_404(action):
        try:
            return action()
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Turn any unexpected error into a clean JSON 500 instead of a raw traceback."""
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Check the server logs for details."},
        )

    @app.get("/", tags=["Meta"], summary="Service landing page")
    def root() -> dict[str, object]:
        """Human-friendly entry point that points at the useful URLs."""
        return {
            "service": "DrugGPT API",
            "version": "3.0.0",
            "status": "running",
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/health",
            "chat": "POST /conversations/{conversation_id}/messages",
        }

    @app.get("/health", tags=["Meta"], summary="Liveness probe")
    def health() -> dict[str, str]:
        """Return a constant payload while the process is accepting requests."""
        return {"status": "running", "mode": "local-development-only"}

    @app.get(
        "/vector-db/status",
        response_model=DatabaseStatus,
        tags=["Index"],
        summary="Inspect the local vector index",
    )
    def vector_database_status() -> DatabaseStatus:
        """Report whether the index is ready and how many documents/chunks it holds."""
        return rag_service.retriever.status()

    @app.post(
        "/vector-db/rebuild",
        tags=["Index"],
        summary="Rebuild the vector index from data/raw",
        description="Re-ingests every PDF in `data/raw` and replaces the local Chroma index.",
    )
    def rebuild_vector_database() -> dict[str, int | str]:
        logger.info("Rebuilding vector index from %s", rag_service.settings.raw_documents_dir)
        try:
            result = rebuild_index(rag_service.settings)
        except (FileNotFoundError, ValueError) as error:
            logger.warning("Vector index rebuild rejected: %s", error)
            raise HTTPException(status_code=400, detail=str(error)) from error
        logger.info("Vector index rebuild complete: %s", result)
        return result

    @app.get("/patients", response_model=list[Patient], tags=["Patients"], summary="List patients")
    def list_patients() -> list[Patient]:
        return rag_service.store.list_patients()

    @app.post(
        "/patients",
        response_model=Patient,
        status_code=201,
        tags=["Patients"],
        summary="Create a patient",
    )
    def create_patient(request: PatientCreate) -> Patient:
        logger.info("Creating patient record")
        return rag_service.store.create_patient(request.name, request.date_of_birth, request.sex)

    @app.get("/patients/{patient_id}", response_model=Patient, tags=["Patients"], summary="Get a patient")
    def get_patient(patient_id: str) -> Patient:
        return get_or_404(lambda: rag_service.store.get_patient(patient_id))

    @app.patch(
        "/patients/{patient_id}",
        response_model=Patient,
        tags=["Patients"],
        summary="Update a patient",
    )
    def update_patient(patient_id: str, request: PatientUpdate) -> Patient:
        return get_or_404(
            lambda: rag_service.store.update_patient(patient_id, **request.model_dump(exclude_unset=True))
        )

    @app.get(
        "/patients/{patient_id}/summary",
        response_model=PatientSummary,
        tags=["Patients"],
        summary="Get a patient summary with approved facts",
    )
    def patient_summary(patient_id: str) -> PatientSummary:
        patient = get_or_404(lambda: rag_service.store.get_patient(patient_id))
        return PatientSummary(
            patient=patient,
            summary=rag_service.store.latest_summary(patient_id),
            facts=rag_service.store.list_facts(patient_id),
        )

    @app.post(
        "/patients/{patient_id}/facts",
        response_model=PatientFact,
        status_code=201,
        tags=["Patients"],
        summary="Add a patient fact",
    )
    def add_patient_fact(patient_id: str, request: PatientFactCreate) -> PatientFact:
        return get_or_404(
            lambda: rag_service.store.add_fact(
                patient_id, request.category, request.value, request.approved
            )
        )

    @app.get(
        "/patients/{patient_id}/conversations",
        response_model=list[Conversation],
        tags=["Chat"],
        summary="List a patient's conversations",
    )
    def list_conversations(patient_id: str) -> list[Conversation]:
        get_or_404(lambda: rag_service.store.get_patient(patient_id))
        return rag_service.store.list_conversations(patient_id)

    @app.post(
        "/conversations",
        response_model=Conversation,
        status_code=201,
        tags=["Chat"],
        summary="Create a conversation",
    )
    def create_conversation(request: ConversationCreate) -> Conversation:
        logger.info("Creating conversation for patient %s", request.patient_id)
        return get_or_404(
            lambda: rag_service.store.create_conversation(request.patient_id, request.title)
        )

    @app.get(
        "/conversations/{conversation_id}/messages",
        response_model=list[ConversationMessage],
        tags=["Chat"],
        summary="List conversation messages",
    )
    def list_messages(conversation_id: str) -> list[ConversationMessage]:
        return get_or_404(lambda: rag_service.store.list_messages(conversation_id))

    @app.post(
        "/conversations/{conversation_id}/messages",
        response_model=ChatResponse,
        tags=["Chat"],
        summary="Send a chat message",
        description=(
            "Run one turn of the medical assistant. Returns an answer immediately, or a "
            "`review_pending` response with a `review_id` when a clinician must approve "
            "medication guidance first."
        ),
    )
    def send_message(conversation_id: str, request: MessageRequest) -> ChatResponse:
        logger.info(
            "POST /conversations/%s/messages (chars=%d)", conversation_id, len(request.message)
        )
        try:
            response = rag_service.send_message(conversation_id, request.message)
        except KeyError as error:
            logger.warning("Conversation not found: %s", conversation_id)
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RuntimeError as error:
            logger.error("Chat generation failed for conversation %s: %s", conversation_id, error)
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:  # safety net: never leak a raw 500 traceback to clients
            logger.exception("Unexpected error while processing conversation %s", conversation_id)
            raise HTTPException(
                status_code=500,
                detail="Internal server error while generating a response. Check the server logs.",
            ) from error
        logger.info(
            "Chat response conversation=%s status=%s mode=%s",
            conversation_id,
            response.status.value,
            response.answer_mode,
        )
        return response

    @app.get("/reviews", response_model=list[MedicationReview], tags=["Reviews"], summary="List reviews")
    def list_reviews(status: str = "pending") -> list[MedicationReview]:
        return rag_service.store.list_reviews(status)

    @app.get("/reviews/{review_id}", tags=["Reviews"], summary="Get a review with context")
    def get_review(review_id: str) -> dict:
        review = get_or_404(lambda: rag_service.store.get_review(review_id))
        return {"review": review, "context": rag_service.store.review_context(review_id)}

    @app.post(
        "/reviews/{review_id}/decision",
        response_model=ChatResponse,
        tags=["Reviews"],
        summary="Record a clinician decision and resume the chat",
        description=(
            "Approve or reject pending medication guidance. On approval, `approved_guidance` "
            "is required and becomes the assistant's reply."
        ),
    )
    def decide_review(review_id: str, request: ReviewDecisionRequest) -> ChatResponse:
        logger.info("POST /reviews/%s/decision (%s)", review_id, request.decision)
        try:
            review = rag_service.store.decide_review(
                review_id,
                request.decision,
                request.reviewer_name,
                request.reviewer_note,
                request.approved_guidance,
            )
            response = rag_service.resume_review(review)
        except KeyError as error:
            logger.warning("Review not found: %s", review_id)
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            logger.warning("Invalid review decision for %s: %s", review_id, error)
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RuntimeError as error:
            logger.error("Resuming review %s failed: %s", review_id, error)
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:
            logger.exception("Unexpected error while deciding review %s", review_id)
            raise HTTPException(
                status_code=500,
                detail="Internal server error while recording the review decision.",
            ) from error
        logger.info("Review %s decided as %s", review_id, request.decision)
        return response

    @app.post(
        "/chat",
        response_model=ChatResponse,
        tags=["Chat"],
        summary="Legacy one-shot chat",
        description="Compatibility endpoint. New clients should use conversation-based chat.",
    )
    def legacy_chat(request: ChatRequest) -> ChatResponse:
        logger.info("POST /chat (legacy, chars=%d)", len(request.message))
        try:
            return rag_service.answer(request.message, request.thread_id)
        except RuntimeError as error:
            logger.error("Legacy chat generation failed: %s", error)
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:
            logger.exception("Unexpected error in legacy chat endpoint")
            raise HTTPException(
                status_code=500,
                detail="Internal server error while generating a response. Check the server logs.",
            ) from error

    return app


app = create_app()
