import pytest

import src.rag.retrieval as retrieval
from src.core.config import Settings
from src.rag.retrieval import MedicalRetriever, VectorDatabaseNotReadyError


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
