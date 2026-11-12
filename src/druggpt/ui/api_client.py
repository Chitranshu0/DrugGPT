"""Testable HTTP client shared by Streamlit pages."""

import requests


class DrugGPTApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, **kwargs) -> dict | list:
        response = requests.request(method, f"{self.base_url}{path}", timeout=120, **kwargs)
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
        return self._request("POST", f"/patients/{patient_id}/facts", json={"category": category, "value": value, "approved": approved})

    def conversations(self, patient_id: str) -> list[dict]:
        return self._request("GET", f"/patients/{patient_id}/conversations")

    def create_conversation(self, patient_id: str, title: str) -> dict:
        return self._request("POST", "/conversations", json={"patient_id": patient_id, "title": title})

    def messages(self, conversation_id: str) -> list[dict]:
        return self._request("GET", f"/conversations/{conversation_id}/messages")

    def send_message(self, conversation_id: str, message: str) -> dict:
        return self._request("POST", f"/conversations/{conversation_id}/messages", json={"message": message})

    def reviews(self, status: str = "pending") -> list[dict]:
        return self._request("GET", f"/reviews?status={status}")

    def review(self, review_id: str) -> dict:
        return self._request("GET", f"/reviews/{review_id}")

    def decide_review(self, review_id: str, decision: str, reviewer_name: str, approved_guidance: str | None, reviewer_note: str | None) -> dict:
        return self._request("POST", f"/reviews/{review_id}/decision", json={"decision": decision, "reviewer_name": reviewer_name, "approved_guidance": approved_guidance, "reviewer_note": reviewer_note})
