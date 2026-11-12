"""Orchestration for safe, source-required medical RAG answers."""

from collections.abc import Callable

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from druggpt.core.config import Settings, settings
from druggpt.core.models import ChatResponse, ChatStatus, Evidence, SourceCitation, ToolActivity
from druggpt.rag.guardrails import (
    OUT_OF_SCOPE_MESSAGE,
    SAFETY_MESSAGE,
    GuardrailDecision,
    classify_query,
)
from druggpt.rag.retrieval import MedicalRetriever

PROMPT = ChatPromptTemplate.from_template("""You are DrugGPT, an educational medical and drug-study assistant.
Answer only from the supplied source excerpts. Do not add diagnoses, personalized treatment, doses,
or facts unsupported by the excerpts. If evidence is incomplete, say so plainly.

Source excerpts:
{context}

Research question: {question}
""")


class RAGState(TypedDict, total=False):
    question: str
    evidence: list[Evidence]


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
    def __init__(
        self,
        retriever: MedicalRetriever | None = None,
        app_settings: Settings = settings,
        llm_factory: Callable[[], object] | None = None,
    ) -> None:
        self.settings = app_settings
        self.retriever = retriever or MedicalRetriever(app_settings)
        self.llm_factory = llm_factory or self._default_llm
        self._search_tool = StructuredTool.from_function(
            func=self.search_medical_sources,
            name="search_medical_sources",
            description="Search approved medical source documents for a research question.",
        )

    def _default_llm(self) -> ChatGroq:
        if not self.settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY must be configured to generate answers.")
        return ChatGroq(model=self.settings.groq_model, temperature=0.2, max_tokens=600)

    def search_medical_sources(self, query: str) -> list[Evidence]:
        """Search approved medical source documents for a research question."""
        return self.retriever.search(query)

    def _retrieve_node(self, state: RAGState) -> RAGState:
        return {"evidence": self._search_tool.invoke({"query": state["question"]})}

    def _graph(self):
        graph = StateGraph(RAGState)
        graph.add_node("search_medical_sources", self._retrieve_node)
        graph.add_edge(START, "search_medical_sources")
        graph.add_edge("search_medical_sources", END)
        return graph.compile()

    def answer(self, question: str, thread_id: str) -> ChatResponse:
        decision = classify_query(question)
        if decision == GuardrailDecision.OUT_OF_SCOPE:
            return ChatResponse(answer=OUT_OF_SCOPE_MESSAGE, status=ChatStatus.OUT_OF_SCOPE, thread_id=thread_id)
        if decision == GuardrailDecision.SAFETY_REFUSAL:
            return ChatResponse(answer=SAFETY_MESSAGE, status=ChatStatus.SAFETY_REFUSAL, thread_id=thread_id)

        evidence = self._graph().invoke({"question": question}).get("evidence", [])
        acceptable = [item for item in evidence if item.score >= self.settings.relevance_threshold]
        activity = ToolActivity(
            tool_name="search_medical_sources",
            message="Searched approved medical sources.",
            sources_found=len(acceptable),
        )
        if not acceptable:
            return ChatResponse(
                answer=("I could not find sufficiently relevant evidence in the indexed medical sources. "
                        "Please rephrase with a specific medicine, condition, mechanism, or study topic."),
                status=ChatStatus.REPHRASE_REQUIRED,
                tool_activity=activity,
                thread_id=thread_id,
            )
        context = "\n\n".join(
            f"[Source {index}: {item.source_title}, page {item.page or 'unknown'}]\n{item.content}"
            for index, item in enumerate(acceptable, start=1)
        )
        rendered_prompt = PROMPT.invoke({"context": context, "question": question})
        response = self.llm_factory().invoke(rendered_prompt)
        return ChatResponse(
            answer=response.content,
            sources=citations_from_evidence(acceptable),
            tool_activity=activity,
            status=ChatStatus.ANSWERED,
            thread_id=thread_id,
        )
