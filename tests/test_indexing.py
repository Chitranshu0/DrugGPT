from types import SimpleNamespace

from langchain_core.documents import Document

import src.rag.indexing as indexing
from src.rag.retrieval import COLLECTION_METADATA


def test_low_value_pages_and_short_chunks_are_detected(app_settings):
    front_matter = Document(page_content="A" * 200, metadata={"page": 1})
    dedication = Document(page_content="Dedicated to the memory of my parents.", metadata={"page": 20})
    index_page = Document(
        page_content="\n".join(f"Condition {number}" for number in range(100, 120)), metadata={"page": 20}
    )
    real_content = Document(page_content="Aspirin irreversibly inhibits platelet cyclooxygenase. " * 4, metadata={"page": 20})
    short = Document(page_content="iv Message (Commissionerate)", metadata={"page": 20})

    assert indexing.is_low_value_chunk(front_matter, app_settings)
    assert indexing.is_low_value_chunk(dedication, app_settings)
    assert indexing.is_low_value_chunk(index_page, app_settings)
    assert indexing.is_low_value_chunk(short, app_settings)
    assert not indexing.is_low_value_chunk(real_content, app_settings)


def test_cap_per_document_samples_evenly():
    chunks = [Document(page_content=str(index), metadata={"source": "a.pdf"}) for index in range(10)]
    chunks += [Document(page_content="b", metadata={"source": "b.pdf"})]
    kept, dropped = indexing._cap_per_document(chunks, 4)
    assert len(kept) == 5
    assert dropped == 6
    assert {item.metadata["source"] for item in kept} == {"a.pdf", "b.pdf"}
    assert kept[0].page_content == "0"
    assert "9" in [item.page_content for item in kept]


def test_rebuild_writes_cosine_metadata_and_relative_paths(monkeypatch, app_settings):
    raw_dir = app_settings.raw_documents_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "a.pdf").write_bytes(b"%PDF-1.4")
    valid = Document(
        page_content="Aspirin irreversibly inhibits platelet cyclooxygenase. " * 4,
        metadata={"page": 20, "source": str(raw_dir / "a.pdf")},
    )
    junk = Document(page_content="Dedicated to my parents.", metadata={"page": 30, "source": str(raw_dir / "a.pdf")})
    monkeypatch.setattr(
        indexing, "DirectoryLoader", lambda **_kwargs: SimpleNamespace(load=lambda: [valid, junk])
    )
    monkeypatch.setattr(
        indexing.chromadb,
        "PersistentClient",
        lambda **_kwargs: SimpleNamespace(delete_collection=lambda _name: None),
    )
    monkeypatch.setattr(indexing, "get_embeddings", lambda: object())
    captured = {}

    def fake_from_documents(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(indexing.Chroma, "from_documents", staticmethod(fake_from_documents))

    result = indexing.rebuild_index(app_settings)

    assert captured["collection_metadata"] == COLLECTION_METADATA
    assert result["chunks_indexed"] == 1
    assert result["chunks_dropped"] >= 1
    assert all(not item.metadata["source"].startswith("C:") for item in captured["documents"])
