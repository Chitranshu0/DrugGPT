from dataclasses import replace

import pytest

from druggpt.core.config import Settings
from druggpt.core.models import Evidence


class FakeRetriever:
    def __init__(self, evidence=None, ready=True):
        self.evidence = evidence or []
        self.ready = ready

    def search(self, query):
        return self.evidence

    def status(self):
        from druggpt.core.models import DatabaseStatus

        return DatabaseStatus(ready=self.ready, chunks_indexed=len(self.evidence), documents_indexed=1)


class FakeLLM:
    def invoke(self, values):
        class Response:
            content = "A sourced educational answer."

        return Response()


@pytest.fixture
def app_settings(tmp_path):
    return replace(Settings(), data_dir=tmp_path / "data", relevance_threshold=0.35)


@pytest.fixture
def evidence():
    return [
        Evidence(
            content="Aspirin irreversibly inhibits cyclooxygenase in platelets.",
            source_path="data/raw/pharmacology.pdf",
            source_title="Pharmacology",
            page=42,
            score=0.91,
        )
    ]
