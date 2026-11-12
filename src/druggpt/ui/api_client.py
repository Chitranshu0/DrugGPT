"""Small, testable HTTP client used by the Streamlit app."""

import requests


class DrugGPTApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def status(self) -> dict:
        response = requests.get(f"{self.base_url}/vector-db/status", timeout=10)
        response.raise_for_status()
        return response.json()

    def rebuild(self) -> dict:
        response = requests.post(f"{self.base_url}/vector-db/rebuild", timeout=600)
        response.raise_for_status()
        return response.json()

    def chat(self, message: str, thread_id: str) -> dict:
        response = requests.post(
            f"{self.base_url}/chat", json={"message": message, "thread_id": thread_id}, timeout=120
        )
        response.raise_for_status()
        return response.json()
