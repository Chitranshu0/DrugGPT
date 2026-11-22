"""Testable HTTP client shared by Streamlit pages."""

import json
import os
from collections.abc import Iterator
from functools import lru_cache

import requests

from src.core.config import settings


def api_base_url() -> str:
    """Resolve the backend URL once so every page reads from a single source of truth."""
    return os.getenv("DRUGGPT_API_URL") or f"http://{settings.api_host}:{settings.api_port}"


@lru_cache(maxsize=8)
def get_client() -> "DrugGPTApiClient":
    """Build a client pointed at the configured backend URL (once per process)."""
    return DrugGPTApiClient(api_base_url())


class DrugGPTApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        timeout = kwargs.pop("timeout", 120)
        response = requests.request(method, f"{self.base_url}{path}", timeout=timeout, **kwargs)
        response.raise_for_status()
        return response.json()

    def status(self) -> dict:
        return self._request("GET", "/vector-db/status")

    def rebuild(self) -> dict:
        return self._request("POST", "/vector-db/rebuild", timeout=600)

    def patients(self) -> list[dict]:
        return self._request("GET", "/patients")

    def create_patient(self, name: str, date_of_birth: str | None = None, sex: str | None = None) -> dict:
        return self._request("POST", "/patients", json={"name": name, "date_of_birth": date_of_birth, "sex": sex})

    def patient_summary(self, patient_id: str) -> dict:
        return self._request("GET", f"/patients/{patient_id}/summary")

    def add_fact(self, patient_id: str, category: str, value: str, approved: bool = True) -> dict:
        return self._request(
            "POST",
            f"/patients/{patient_id}/facts",
            json={"category": category, "value": value, "approved": approved},
        )

    def conversations(self, patient_id: str) -> list[dict]:
        return self._request("GET", f"/patients/{patient_id}/conversations")

    def create_conversation(self, patient_id: str, title: str) -> dict:
        return self._request("POST", "/conversations", json={"patient_id": patient_id, "title": title})

    def messages(self, conversation_id: str) -> list[dict]:
        return self._request("GET", f"/conversations/{conversation_id}/messages")

    def messages_since(self, conversation_id: str, after: str | None = None) -> dict:
        """Return only messages added after ``after`` plus the current count."""
        suffix = f"?after={after}" if after else ""
        return self._request("GET", f"/conversations/{conversation_id}/messages/since{suffix}")

    def send_message(self, conversation_id: str, message: str) -> dict:
        return self._request("POST", f"/conversations/{conversation_id}/messages", json={"message": message})

    def send_message_stream(self, conversation_id: str, message: str) -> Iterator[dict]:
        """Yield SSE payloads from the streaming chat endpoint."""
        with requests.post(
            f"{self.base_url}/conversations/{conversation_id}/messages/stream",
            json={"message": message},
            stream=True,
            timeout=120,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    yield json.loads(line.removeprefix("data: "))

    def reviews(self, status: str = "pending") -> list[dict]:
        return self._request("GET", f"/reviews?status={status}")

    def review(self, review_id: str) -> dict:
        return self._request("GET", f"/reviews/{review_id}")

    def decide_review(
        self,
        review_id: str,
        decision: str,
        reviewer_name: str,
        approved_guidance: str | None,
        reviewer_note: str | None,
    ) -> dict:
        return self._request(
            "POST",
            f"/reviews/{review_id}/decision",
            json={
                "decision": decision,
                "reviewer_name": reviewer_name,
                "approved_guidance": approved_guidance,
                "reviewer_note": reviewer_note,
            },
        )

    def transcript(self, conversation_id: str) -> dict:
        """Return the full message list plus any open review and its context."""
        return self._request("GET", f"/conversations/{conversation_id}/transcript")

    def clinician_reply(
        self,
        conversation_id: str,
        message: str,
        reviewer_name: str,
        review_id: str | None = None,
    ) -> dict:
        """Record a clinician's free-text reply and close the open review."""
        return self._request(
            "POST",
            f"/conversations/{conversation_id}/clinician-reply",
            json={
                "message": message,
                "reviewer_name": reviewer_name,
                "review_id": review_id,
            },
        )
