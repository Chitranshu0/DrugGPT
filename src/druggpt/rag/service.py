"""Persistent conversational medical agent with clinician medication review."""

import sqlite3
from collections.abc import Callable
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from langchain_groq import ChatGroq
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict

from druggpt.core.config import Settings, settings
from druggpt.core.models import ChatResponse, ChatStatus, Evidence, MedicationReview, SourceCitation, ToolActivity
from druggpt.core.persistence import LocalStore
from druggpt.rag.guardrails import EMERGENCY_MESSAGE, OUT_OF_SCOPE_MESSAGE, Triage, triage_query
from druggpt.rag.retrieval import MedicalRetriever, VectorDatabaseNotReadyError

GROUNDED_PROMPT = ChatPromptTemplate.from_template("""You are DrugGPT, a helpful medical education assistant.
Answer the user's question clearly and naturally, using the source excerpts below. Do not diagnose or prescribe.
Mention uncertainty when the excerpts are incomplete.

Source excerpts:
{context}

Patient context (use only if relevant):
{patient_context}

Question: {question}""")
GENERAL_PROMPT = ChatPromptTemplate.from_template("""You are DrugGPT, a helpful medical education assistant.
Give a concise, empathetic, plain-language educational answer to the question. Do not diagnose, prescribe,
or give an individual dose. For personal symptoms, explain when professional or urgent help is appropriate.

Patient context (use only if relevant):
{patient_context}

Recent conversation:
{history}

Question: {question}""")
DRAFT_PROMPT = ChatPromptTemplate.from_template("""You are drafting internal clinical guidance for clinician review.
Based on the question and patient context, write a cautious short draft. Never claim a diagnosis. Include
information a clinician should verify (allergies, interactions, contraindications, age/pregnancy, severity).

Patient context: {patient_context}
Question: {question}""")


class AgentState(TypedDict, total=False):
    question: str
    patient_id: str
    conversation_id: str
    message_id: str
    thread_id: str
    triage: str
    patient_context: str
    history: str
    answer: str
    status: str
    sources: list[dict[str, Any]]
    tool_activity: dict[str, Any]
    answer_mode: str
    review_id: str
    review_status: str


def citations_from_evidence(evidence: list[Evidence]) -> list[SourceCitation]:
    return [
        SourceCitation(
            id=index,
            title=item.source_title,
            path=item.source_path,
            page=item.page,
            excerpt=item.content[:320].strip(),
            relevance_score=round(item.score, 3),
        )
        for index, item in enumerate(evidence, start=1)
    ]


class MedicalRAGService:
    """Coordinates memory, retrieval, general education, and review-required medication drafts."""

    def __init__(
        self,
        retriever: MedicalRetriever | None = None,
        app_settings: Settings = settings,
        llm_factory: Callable[[], object] | None = None,
        store: LocalStore | None = None,
    ) -> None:
        self.settings = app_settings
        self.retriever = retriever or MedicalRetriever(app_settings)
        self.store = store or LocalStore(app_settings.application_db)
        self.llm_factory = llm_factory or self._default_llm
        app_settings.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
        self._checkpoint_connection = sqlite3.connect(app_settings.checkpoint_db, check_same_thread=False)
        self.checkpointer = SqliteSaver(self._checkpoint_connection)
        self.checkpointer.setup()
        self._search_tool = StructuredTool.from_function(
            func=self.search_medical_sources,
            name="search_medical_sources",
            description="Search local medical source documents for an educational question.",
        )
        self.graph = self._build_graph()

    def _default_llm(self) -> ChatGroq:
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY must be configured to generate answers.")
        return ChatGroq(model=self.settings.groq_model, temperature=0.2, max_tokens=700)

    def _generate(self, prompt: ChatPromptTemplate, **values: str) -> str:
        response = self.llm_factory().invoke(prompt.invoke(values))
        return str(response.content)

    def search_medical_sources(self, query: str) -> list[Evidence]:
        return self.retriever.search(query)

    def _triage_node(self, state: AgentState) -> AgentState:
        return {"triage": triage_query(state["question"]).value}

    def _load_context_node(self, state: AgentState) -> AgentState:
        patient = self.store.get_patient(state["patient_id"])
        facts = self.store.list_facts(patient.id, approved_only=True)
        facts_text = "; ".join(f"{fact.category}: {fact.value}" for fact in facts) or "No approved facts recorded."
        summary = self.store.latest_summary(patient.id) or "No approved clinical summary recorded."
        messages = self.store.list_messages(state["conversation_id"], limit=8)
        history = "\n".join(f"{message.role}: {message.content}" for message in messages) or "No earlier messages."
        return {"patient_context": f"Patient: {patient.name}. Summary: {summary}. Facts: {facts_text}", "history": history}

    def _general_answer_node(self, state: AgentState) -> AgentState:
        evidence: list[Evidence] = []
        try:
            evidence = self._search_tool.invoke({"query": state["question"]})
        except VectorDatabaseNotReadyError:
            pass
        acceptable = [item for item in evidence if item.score >= self.settings.relevance_threshold]
        if acceptable:
            context = "\n\n".join(
                f"[Source {index}: {item.source_title}, page {item.page or 'unknown'}]\n{item.content}"
                for index, item in enumerate(acceptable, start=1)
            )
            answer = self._generate(GROUNDED_PROMPT, context=context, patient_context=state["patient_context"], question=state["question"])
            return {
                "answer": answer,
                "status": ChatStatus.ANSWERED.value,
                "sources": [citation.model_dump() for citation in citations_from_evidence(acceptable)],
                "tool_activity": ToolActivity(tool_name="search_medical_sources", message="Used local medical sources.", sources_found=len(acceptable)).model_dump(),
                "answer_mode": "source_grounded",
            }
        answer = self._generate(GENERAL_PROMPT, patient_context=state["patient_context"], history=state["history"], question=state["question"])
        return {
            "answer": answer,
            "status": ChatStatus.ANSWERED.value,
            "sources": [],
            "tool_activity": ToolActivity(tool_name="search_medical_sources", message="No sufficiently relevant local source found; used general educational information.", sources_found=0).model_dump(),
            "answer_mode": "general_education",
        }

    def _emergency_node(self, state: AgentState) -> AgentState:
        return {"answer": EMERGENCY_MESSAGE, "status": ChatStatus.EMERGENCY_GUIDANCE.value, "answer_mode": "emergency"}

    def _out_of_scope_node(self, state: AgentState) -> AgentState:
        return {"answer": OUT_OF_SCOPE_MESSAGE, "status": ChatStatus.OUT_OF_SCOPE.value, "answer_mode": "scope_notice"}

    def _review_node(self, state: AgentState) -> AgentState:
        draft = self._generate(DRAFT_PROMPT, patient_context=state["patient_context"], question=state["question"])
        review = self.store.create_or_get_review(
            state["patient_id"], state["conversation_id"], state["message_id"], state["thread_id"], draft,
            {"patient_context": state["patient_context"], "question": state["question"], "history": state["history"]},
        )
        decision = interrupt({
            "type": "medication_review", "review_id": review.id, "patient_id": review.patient_id,
            "conversation_id": review.conversation_id, "draft_guidance": review.draft_guidance,
            "context": self.store.review_context(review.id),
        })
        if decision.get("decision") == "approved":
            return {
                "answer": decision["approved_guidance"], "status": ChatStatus.ANSWERED.value,
                "review_id": review.id, "review_status": "approved", "answer_mode": "clinician_approved",
            }
        return {
            "answer": "The clinician reviewer did not approve medication guidance for this request. Please contact a healthcare professional for personalised care.",
            "status": ChatStatus.SAFETY_REFUSAL.value, "review_id": review.id,
            "review_status": "rejected", "answer_mode": "clinician_review",
        }

    @staticmethod
    def _route(state: AgentState) -> str:
        return state["triage"]

    def _build_graph(self):
        graph = StateGraph(AgentState)
        graph.add_node("triage", self._triage_node)
        graph.add_node("load_context", self._load_context_node)
        graph.add_node("answer", self._general_answer_node)
        graph.add_node("emergency", self._emergency_node)
        graph.add_node("out_of_scope", self._out_of_scope_node)
        graph.add_node("medication_review", self._review_node)
        graph.add_edge(START, "triage")
        graph.add_conditional_edges("triage", self._route, {
            Triage.GENERAL.value: "load_context", Triage.SYMPTOM.value: "load_context",
            Triage.MEDICATION_REVIEW.value: "load_context", Triage.EMERGENCY.value: "emergency",
            Triage.OUT_OF_SCOPE.value: "out_of_scope",
        })
        graph.add_conditional_edges("load_context", self._route, {
            Triage.GENERAL.value: "answer", Triage.SYMPTOM.value: "answer", Triage.MEDICATION_REVIEW.value: "medication_review",
        })
        graph.add_edge("answer", END)
        graph.add_edge("emergency", END)
        graph.add_edge("out_of_scope", END)
        graph.add_edge("medication_review", END)
        return graph.compile(checkpointer=self.checkpointer)

    def _response_from_state(self, state: dict[str, Any], thread_id: str) -> ChatResponse:
        return ChatResponse(
            answer=state["answer"], sources=[SourceCitation(**source) for source in state.get("sources", [])],
            tool_activity=ToolActivity(**state["tool_activity"]) if state.get("tool_activity") else None,
            status=ChatStatus(state["status"]), thread_id=thread_id, review_id=state.get("review_id"),
            review_status=state.get("review_status"), answer_mode=state.get("answer_mode", "general_education"),
        )

    def send_message(self, conversation_id: str, message: str) -> ChatResponse:
        conversation = self.store.get_conversation(conversation_id)
        user_message = self.store.add_message(conversation_id, "user", message)
        thread_id = f"conversation:{conversation_id}:message:{user_message.id}"
        result = self.graph.invoke(
            {"question": message, "patient_id": conversation.patient_id, "conversation_id": conversation_id,
             "message_id": user_message.id, "thread_id": thread_id},
            config={"configurable": {"thread_id": thread_id}},
        )
        review = self.store.find_pending_review(thread_id)
        if review:
            response = ChatResponse(
                answer="I’ve prepared this medication-related request for clinician review. You will receive guidance here after it has been approved.",
                status=ChatStatus.REVIEW_PENDING, thread_id=thread_id, review_id=review.id, review_status="pending",
                answer_mode="clinician_review",
            )
        else:
            response = self._response_from_state(result, thread_id)
        self.store.add_message(conversation_id, "assistant", response.answer, response.status.value, response.model_dump(mode="json"))
        return response

    def resume_review(self, review: MedicationReview) -> ChatResponse:
        thread_id = self.store.review_graph_thread_id(review.id)
        result = self.graph.invoke(
            Command(resume={"decision": review.status, "approved_guidance": review.approved_guidance or ""}),
            config={"configurable": {"thread_id": thread_id}},
        )
        response = self._response_from_state(result, thread_id)
        self.store.add_message(review.conversation_id, "assistant", response.answer, response.status.value, response.model_dump(mode="json"))
        return response

    def answer(self, question: str, thread_id: str) -> ChatResponse:
        """Compatibility wrapper for the legacy /chat endpoint."""
        patient = self.store.ensure_demo_patient()
        conversation = self.store.ensure_demo_conversation(patient.id)
        return self.send_message(conversation.id, question)
