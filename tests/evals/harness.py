"""Invoke the real DrugGPT service with a DeepEval LangGraph callback attached."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import mkdtemp
from uuid import uuid4

from src.core.runtime import configure_runtime

configure_runtime()

from deepeval.integrations.langchain import CallbackHandler  # noqa: E402

from src.core.config import settings  # noqa: E402
from src.core.models import ChatResponse  # noqa: E402
from src.core.persistence import LocalStore  # noqa: E402
from src.rag.retrieval import MedicalRetriever  # noqa: E402
from src.rag.service import MedicalRAGService  # noqa: E402
from tests.evals.judge import build_chat_model  # noqa: E402


class RecordingRetriever(MedicalRetriever):
    """Keep the full evidence chunks so Faithfulness scores real source text."""

    def __init__(self, app_settings) -> None:
        super().__init__(app_settings)
        self.last_evidence: list = []

    def search(self, query: str):
        self.last_evidence = super().search(query)
        return self.last_evidence


@dataclass
class RunResult:
    response: ChatResponse
    retrieval_context: list[str]
    llm_calls: int


def _new_service() -> tuple[MedicalRAGService, LocalStore, RecordingRetriever, dict[str, int]]:
    workdir = Path(mkdtemp(prefix="druggpt-eval-"))
    # Keep the real data_dir so retrieval uses the built Chroma index; isolate
    # only the conversation DB so eval messages never touch the app database.
    app_settings = settings
    store = LocalStore(workdir / "druggpt.db")
    retriever = RecordingRetriever(app_settings)
    calls = {"llm": 0}

    def llm_factory():
        calls["llm"] += 1
        # Use the same provider as the judge so a single configured key drives
        # both the app under test and the metrics that score it.
        return build_chat_model(1500, 0.2)

    service = MedicalRAGService(
        retriever=retriever, app_settings=app_settings, llm_factory=llm_factory, store=store
    )
    return service, store, retriever, calls


_SERVICE, _STORE, _RETRIEVER, _CALLS = _new_service()


def run_golden(input_text: str) -> RunResult:
    """Run one golden end-to-end and attach a fresh DeepEval trace."""
    patient = _STORE.ensure_demo_patient()
    conversation = _STORE.create_conversation(patient.id, f"eval-{uuid4()}")
    retriever = _RETRIEVER
    retriever.last_evidence = []
    _CALLS["llm"] = 0
    response = _SERVICE.send_message(conversation.id, input_text, callbacks=[CallbackHandler()])
    return RunResult(
        response=response,
        retrieval_context=[evidence.content for evidence in retriever.last_evidence],
        llm_calls=_CALLS["llm"],
    )
