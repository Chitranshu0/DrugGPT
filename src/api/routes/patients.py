"""Patient records, facts, summaries and their conversations."""

import logging

from fastapi import APIRouter

from src.api.deps import get_or_404
from src.core.models import (
    Conversation,
    Patient,
    PatientCreate,
    PatientFact,
    PatientFactCreate,
    PatientSummary,
    PatientUpdate,
)
from src.rag.service import MedicalRAGService

logger = logging.getLogger("druggpt.api")


def make_router(service: MedicalRAGService) -> APIRouter:
    router = APIRouter(prefix="/patients", tags=["Patients"])

    @router.get("", response_model=list[Patient], tags=["Patients"], summary="List patients")
    def list_patients() -> list[Patient]:
        return service.store.list_patients()

    @router.post(
        "",
        response_model=Patient,
        status_code=201,
        tags=["Patients"],
        summary="Create a patient",
    )
    def create_patient(request: PatientCreate) -> Patient:
        logger.info("Creating a new patient record")
        patient = service.store.create_patient(request.name, request.date_of_birth, request.sex)
        logger.info("Patient %s created (name=%r)", patient.id, patient.name)
        return patient

    @router.get(
        "/{patient_id}",
        response_model=Patient,
        tags=["Patients"],
        summary="Get a patient",
    )
    def get_patient(patient_id: str) -> Patient:
        return get_or_404(lambda: service.store.get_patient(patient_id))

    @router.patch(
        "/{patient_id}",
        response_model=Patient,
        tags=["Patients"],
        summary="Update a patient",
    )
    def update_patient(patient_id: str, request: PatientUpdate) -> Patient:
        return get_or_404(
            lambda: service.store.update_patient(patient_id, **request.model_dump(exclude_unset=True))
        )

    @router.get(
        "/{patient_id}/summary",
        response_model=PatientSummary,
        tags=["Patients"],
        summary="Get a patient summary with approved facts",
    )
    def patient_summary(patient_id: str) -> PatientSummary:
        patient = get_or_404(lambda: service.store.get_patient(patient_id))
        return PatientSummary(
            patient=patient,
            summary=service.store.latest_summary(patient_id),
            facts=service.store.list_facts(patient_id),
        )

    @router.post(
        "/{patient_id}/facts",
        response_model=PatientFact,
        status_code=201,
        tags=["Patients"],
        summary="Add a patient fact",
    )
    def add_patient_fact(patient_id: str, request: PatientFactCreate) -> PatientFact:
        return get_or_404(
            lambda: service.store.add_fact(patient_id, request.category, request.value, request.approved)
        )

    @router.get(
        "/{patient_id}/conversations",
        response_model=list[Conversation],
        tags=["Chat"],
        summary="List a patient's conversations",
    )
    def list_conversations(patient_id: str) -> list[Conversation]:
        get_or_404(lambda: service.store.get_patient(patient_id))
        return service.store.list_conversations(patient_id)

    return router
