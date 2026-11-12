"""HTTP API for the local DrugGPT development workflow."""

from fastapi import FastAPI, HTTPException

from druggpt.core.models import (
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
from druggpt.rag.indexing import rebuild_index
from druggpt.rag.service import MedicalRAGService


def create_app(service: MedicalRAGService | None = None) -> FastAPI:
    app = FastAPI(title="DrugGPT", version="3.0.0", description="Local medical conversation and clinician-review API")
    rag_service = service or MedicalRAGService()

    def get_or_404(action):
        try:
            return action()
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "running", "mode": "local-development-only"}

    @app.get("/vector-db/status", response_model=DatabaseStatus)
    def vector_database_status() -> DatabaseStatus:
        return rag_service.retriever.status()

    @app.post("/vector-db/rebuild")
    def rebuild_vector_database() -> dict[str, int | str]:
        try:
            return rebuild_index(rag_service.settings)
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.get("/patients", response_model=list[Patient])
    def list_patients() -> list[Patient]:
        return rag_service.store.list_patients()

    @app.post("/patients", response_model=Patient, status_code=201)
    def create_patient(request: PatientCreate) -> Patient:
        return rag_service.store.create_patient(request.name, request.date_of_birth, request.sex)

    @app.get("/patients/{patient_id}", response_model=Patient)
    def get_patient(patient_id: str) -> Patient:
        return get_or_404(lambda: rag_service.store.get_patient(patient_id))

    @app.patch("/patients/{patient_id}", response_model=Patient)
    def update_patient(patient_id: str, request: PatientUpdate) -> Patient:
        return get_or_404(lambda: rag_service.store.update_patient(patient_id, **request.model_dump(exclude_unset=True)))

    @app.get("/patients/{patient_id}/summary", response_model=PatientSummary)
    def patient_summary(patient_id: str) -> PatientSummary:
        patient = get_or_404(lambda: rag_service.store.get_patient(patient_id))
        return PatientSummary(patient=patient, summary=rag_service.store.latest_summary(patient_id), facts=rag_service.store.list_facts(patient_id))

    @app.post("/patients/{patient_id}/facts", response_model=PatientFact, status_code=201)
    def add_patient_fact(patient_id: str, request: PatientFactCreate) -> PatientFact:
        return get_or_404(lambda: rag_service.store.add_fact(patient_id, request.category, request.value, request.approved))

    @app.get("/patients/{patient_id}/conversations", response_model=list[Conversation])
    def list_conversations(patient_id: str) -> list[Conversation]:
        get_or_404(lambda: rag_service.store.get_patient(patient_id))
        return rag_service.store.list_conversations(patient_id)

    @app.post("/conversations", response_model=Conversation, status_code=201)
    def create_conversation(request: ConversationCreate) -> Conversation:
        return get_or_404(lambda: rag_service.store.create_conversation(request.patient_id, request.title))

    @app.get("/conversations/{conversation_id}/messages", response_model=list[ConversationMessage])
    def list_messages(conversation_id: str) -> list[ConversationMessage]:
        return get_or_404(lambda: rag_service.store.list_messages(conversation_id))

    @app.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
    def send_message(conversation_id: str, request: MessageRequest) -> ChatResponse:
        try:
            return rag_service.send_message(conversation_id, request.message)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.get("/reviews", response_model=list[MedicationReview])
    def list_reviews(status: str = "pending") -> list[MedicationReview]:
        return rag_service.store.list_reviews(status)

    @app.get("/reviews/{review_id}")
    def get_review(review_id: str) -> dict:
        review = get_or_404(lambda: rag_service.store.get_review(review_id))
        return {"review": review, "context": rag_service.store.review_context(review_id)}

    @app.post("/reviews/{review_id}/decision", response_model=ChatResponse)
    def decide_review(review_id: str, request: ReviewDecisionRequest) -> ChatResponse:
        try:
            review = rag_service.store.decide_review(
                review_id, request.decision, request.reviewer_name, request.reviewer_note, request.approved_guidance
            )
            return rag_service.resume_review(review)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.post("/chat", response_model=ChatResponse)
    def legacy_chat(request: ChatRequest) -> ChatResponse:
        """Legacy endpoint; new clients should use a conversation endpoint."""
        try:
            return rag_service.answer(request.message, request.thread_id)
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    return app


app = create_app()
