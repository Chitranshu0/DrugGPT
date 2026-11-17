import pytest
from langchain_core.documents import Document

import src.rag.retrieval as retrieval
from src.core.config import PROJECT_ROOT, Settings
from src.rag.retrieval import (
    MedicalRetriever,
    VectorDatabaseNotReadyError,
    cosine_relevance,
    invalidate_caches,
    normalize_source_path,
)


@pytest.fixture(autouse=True)
def _clear_retrieval_caches():
    invalidate_caches()
    yield
    invalidate_caches()


class _Collection:
    def __init__(self, metadata=None, count=1) -> None:
        self.metadata = metadata
        self._count = count

    def count(self) -> int:
        return self._count

    def get(self, include=None):
        return {"metadatas": [{"source": "data/raw/a.pdf"}]}


class _Client:
    def __init__(self, collection: _Collection) -> None:
        self.collection = collection

    def get_collection(self, name: str):
        return self.collection


class _Store:
    def __init__(self, results) -> None:
        self.results = results
        self.calls = 0

    def similarity_search_with_score(self, query, k=5):
        self.calls += 1
        return self.results


def test_status_reports_not_ready_when_store_is_unreadable(monkeypatch, tmp_path):
    def broken_client(*args, **kwargs):
        raise RuntimeError("database disk image is malformed")

    monkeypatch.setattr(retrieval.chromadb, "PersistentClient", broken_client)
    retriever = MedicalRetriever(Settings.from_env())

    status = retriever.status()

    assert status.ready is False
    assert status.chunks_indexed == 0


def test_search_raises_not_ready_instead_of_crashing(monkeypatch):
    def broken_client(*args, **kwargs):
        raise RuntimeError("database disk image is malformed")

    monkeypatch.setattr(retrieval.chromadb, "PersistentClient", broken_client)
    retriever = MedicalRetriever(Settings.from_env())

    with pytest.raises(VectorDatabaseNotReadyError):
        retriever.search("aspirin")


def test_cosine_relevance_clamps_negative_and_oversized_similarities():
    assert cosine_relevance(0.2) == pytest.approx(0.8)
    assert cosine_relevance(-0.4) == 1.0
    assert cosine_relevance(1.6) == 0.0


def test_normalize_source_path_makes_legacy_windows_paths_relative():
    absolute = str(PROJECT_ROOT / "data" / "raw" / "guide.pdf")
    assert normalize_source_path(absolute, Settings.from_env()) == "data/raw/guide.pdf"
    assert normalize_source_path("data/raw/guide.pdf", Settings.from_env()) == "data/raw/guide.pdf"


def test_status_rejects_legacy_schema(monkeypatch, app_settings):
    monkeypatch.setattr(
        retrieval, "_get_client", lambda _dir: _Client(_Collection(metadata={"hnsw:space": "l2"}, count=5))
    )
    status = MedicalRetriever(app_settings).status()
    assert status.ready is False
    assert status.needs_rebuild is True
    assert "python -m src.cli index" in status.message


def test_search_clamps_scores_and_caches_store(monkeypatch, app_settings):
    monkeypatch.setattr(
        retrieval,
        "_get_client",
        lambda _dir: _Client(_Collection(metadata=dict(retrieval.COLLECTION_METADATA), count=3)),
    )
    document = Document(page_content="Aspirin irreversibly inhibits cyclooxygenase.", metadata={"page": 4})
    legacy_source = str(PROJECT_ROOT / "data" / "raw" / "aspirin.pdf")
    document.metadata["source"] = legacy_source
    store = _Store([(document, -0.4), (document, 0.2), (document, 1.6)])
    monkeypatch.setattr(retrieval, "_get_store", lambda _dir: store)

    retriever = MedicalRetriever(app_settings)
    first = retriever.search("aspirin")
    second = retriever.search("aspirin")

    assert [item.score for item in first] == [1.0, pytest.approx(0.8), 0.0]
    assert first[0].page == 5
    assert first[0].source_path == "data/raw/aspirin.pdf"
    assert [item.score for item in second] == [item.score for item in first]


def test_get_store_is_cached_and_invalidation_clears_it(monkeypatch):
    created = []
    monkeypatch.setattr(retrieval, "get_embeddings", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(retrieval, "Chroma", lambda **_kwargs: created.append(1) or object())

    first = retrieval._get_store("chroma-dir")
    assert retrieval._get_store("chroma-dir") is first
    assert len(created) == 1

    invalidate_caches()
    assert retrieval._get_store("chroma-dir") is not first
    assert len(created) == 2
