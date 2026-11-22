"""HTTP API for the local DrugGPT development workflow.

This module exposes a small, typed REST surface around
:class:`src.rag.service.MedicalRAGService`. Every route is tagged and
documented so the interactive Swagger UI at ``/docs`` reads like a real
developer console instead of a bare endpoint list.
"""

import json
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.core.models import (
    ChatResponse,
    ClinicianReplyRequest,
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

API_VERSION = "3.0.0"

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
            "Send messages and read conversation history. LangGraph routes each message to an "
            "educational answer, a clarification question, emergency/scope guidance, or a "
            "`review_pending` status when a clinician must review a personal health decision."
        ),
    },
    {
        "name": "Reviews",
        "description": (
            "List pending clinician reviews (medicines, tests, treatments, report interpretation) "
            "and record a decision to resume a chat."
        ),
    },
    {
        "name": "Clinician",
        "description": "Read a full conversation transcript and record a clinician's free-text reply.",
    },
]


def create_app(service: MedicalRAGService | None = None) -> FastAPI:
    """Build the FastAPI application.

    ``service`` is injectable so tests can supply fakes; in normal operation a
    real :class:`MedicalRAGService` is constructed from environment settings.
    """
    app = FastAPI(
        title="DrugGPT API",
        version=API_VERSION,
        description=(
            "Local, development-only medical education and clinician-review API.\n\n"
            "**Typical flow**\n"
            "1. `POST /patients` to create a patient.\n"
            "2. `POST /conversations` with that patient id.\n"
            "3. `POST /conversations/{conversation_id}/messages` to chat. LangGraph routes the message "
            "to RAG-backed education, a clarification question, emergency/scope guidance, or clinician review.\n"
            "4. If the response status is `review_pending`, decide it with "
            "`POST /reviews/{review_id}/decision` or reply with "
            "`POST /conversations/{conversation_id}/clinician-reply`.\n\n"
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
        # Log the root cause in the summary line; logger.exception keeps the traceback.
        logger.exception(
            "Request failed: %s %s raised %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            exc,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Check the server logs for details."},
        )

    @app.get("/", tags=["Meta"], summary="Service landing page")
    def root() -> dict[str, object]:
        """Human-friendly entry point that points at the useful URLs."""
        return {
            "service": "DrugGPT API",
            "version": API_VERSION,
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

    @app.get("/v1/models", tags=["Meta"], include_in_schema=False, summary="OpenAI-compatible model discovery")
    def models() -> dict[str, object]:
        """Minimal shim for external OpenAI-compatible probes (no code in this repo calls it)."""
        logger.debug("Model discovery probe answered for %s", rag_service.settings.llm_model)
        return {
            "object": "list",
            "data": [{"id": rag_service.settings.llm_model, "object": "model", "owned_by": "openrouter"}],
        }

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
    def rebuild_vector_database() -> dict[str, object]:
        logger.info(
            "Rebuilding vector index from PDFs in %s (this replaces the existing collection)",
            rag_service.settings.raw_documents_dir,
        )
        try:
            result = rebuild_index(rag_service.settings)
        except (FileNotFoundError, ValueError) as error:
            logger.warning("Vector index rebuild rejected (%s): %s", type(error).__name__, error)
            raise HTTPException(status_code=400, detail=str(error)) from error
        logger.info(
            "Vector index rebuilt successfully: %s chunks from %s documents",
            result.get("chunks_indexed"),
            result.get("documents_indexed"),
        )
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
        logger.info("Creating a new patient record")
        patient = rag_service.store.create_patient(request.name, request.date_of_birth, request.sex)
        logger.info("Patient %s created (name=%r)", patient.id, patient.name)
        return patient

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
        logger.info("Creating conversation for patient %s (title=%r)", request.patient_id, request.title)
        conversation = get_or_404(
            lambda: rag_service.store.create_conversation(request.patient_id, request.title)
        )
        logger.info(
            "Conversation %s created for patient %s - awaiting messages",
            conversation.id,
            request.patient_id,
        )
        return conversation

    @app.get(
        "/conversations/{conversation_id}/messages",
        response_model=list[ConversationMessage],
        tags=["Chat"],
        summary="List conversation messages",
    )
    def list_messages(conversation_id: str) -> list[ConversationMessage]:
        return get_or_404(lambda: rag_service.store.list_messages(conversation_id))

    @app.get(
        "/conversations/{conversation_id}/messages/since",
        tags=["Chat"],
        summary="List only messages added after a given message id",
    )
    def list_messages_since(conversation_id: str, after: str | None = None) -> dict[str, object]:
        """Cheap polling payload for the Streamlit transcript fragment."""
        messages = get_or_404(lambda: rag_service.store.list_messages(conversation_id))
        version = len(messages)
        if after:
            positions = [index for index, message in enumerate(messages) if message.id == after]
            if positions:
                messages = messages[positions[-1] + 1 :]
        return {
            "messages": [message.model_dump(mode="json") for message in messages],
            "version": version,
        }

    @app.post(
        "/conversations/{conversation_id}/messages",
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
            response = rag_service.send_message(conversation_id, request.message)
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

    @app.post(
        "/conversations/{conversation_id}/messages/stream",
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
                for event in rag_service.send_message_stream(conversation_id, request.message):
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
        logger.info(
            "Recording clinician decision on review %s: %s by %s",
            review_id,
            request.decision,
            request.reviewer_name,
        )
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

    @app.get(
        "/conversations/{conversation_id}/transcript",
        tags=["Clinician"],
        summary="Full transcript plus any open review and its issue context",
    )
    def conversation_transcript(conversation_id: str) -> dict:
        """Return every message plus the open medication review (if any) and its context."""
        get_or_404(lambda: rag_service.store.get_conversation(conversation_id))
        messages = rag_service.store.list_messages(conversation_id)
        open_review = rag_service.store.open_review_for_conversation(conversation_id)
        context = None
        if open_review is not None:
            context = rag_service.store.review_context(open_review.id)
        return {
            "messages": [m.model_dump(mode="json") for m in messages],
            "open_review": open_review.model_dump(mode="json") if open_review else None,
            "context": context,
        }

    @app.post(
        "/conversations/{conversation_id}/clinician-reply",
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
            return rag_service.reply_as_clinician(
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

    return app


app = create_app()
