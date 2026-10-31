"""Manual check: conversations are isolated per authenticated user.

Run from the project root:

    python -m test.auth_isolation_test

Uses a temporary SQLite database and a fake graph, so it does not touch the
real chat data or call Supabase/Groq/Pinecone.
"""

import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace

from fastapi import Request
from fastapi.testclient import TestClient

from backend.api.dependencies import get_current_user
from backend.api.schemas import AuthUser
from backend.main import app
from backend.memory import db as db_module


class FakeGraph:
    """Minimal stand-in for the compiled LangGraph app."""

    async def aget_state(self, config):
        return SimpleNamespace(values={"messages": []})


class FakeCheckpointer:
    """Records thread deletions instead of touching a real checkpointer."""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def adelete_thread(self, thread_id: str) -> None:
        self.deleted.append(thread_id)


async def _fake_user(request: Request) -> AuthUser:
    """Pick a user from a header so one test can act as two accounts."""
    user_id = request.headers.get("X-Test-User", "user-a")
    return AuthUser(id=user_id, email=f"{user_id}@example.com")


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_module.DATA_DIR = tmp_path
        db_module.SQLITE_APP_DB = tmp_path / "app.sqlite"
        db_module.SQLITE_CHECKPOINT_DB = tmp_path / "checkpoints.sqlite"
        asyncio.run(db_module.init_app_db())

        app.state.graph = FakeGraph()
        app.state.checkpointer = FakeCheckpointer()
        app.dependency_overrides[get_current_user] = _fake_user

        client = TestClient(app)
        user_a = {"X-Test-User": "user-a"}
        user_b = {"X-Test-User": "user-b"}

        created = client.post("/threads", headers=user_a)
        assert created.status_code == 201, created.text
        thread_id = created.json()["thread_id"]

        assert len(client.get("/threads", headers=user_a).json()) == 1
        assert client.get("/threads", headers=user_b).json() == []

        # User B must not see, open, rename, or delete user A's thread.
        assert client.get(f"/threads/{thread_id}", headers=user_b).status_code == 404
        assert (
            client.patch(
                f"/threads/{thread_id}",
                headers=user_b,
                json={"title": "stolen"},
            ).status_code
            == 404
        )
        assert (
            client.delete(f"/threads/{thread_id}", headers=user_b).status_code
            == 404
        )
        assert (
            client.post(
                "/chat",
                headers=user_b,
                json={"message": "hijack", "thread_id": thread_id},
            ).status_code
            == 404
        )

        # The owner can still do all of it.
        assert client.get(f"/threads/{thread_id}", headers=user_a).status_code == 200
        assert (
            client.patch(
                f"/threads/{thread_id}",
                headers=user_a,
                json={"title": "mine"},
            ).status_code
            == 200
        )
        assert client.delete(f"/threads/{thread_id}", headers=user_a).status_code == 204
        assert app.state.checkpointer.deleted == [thread_id]

        # Without a dependency override, a request with no token is rejected.
        app.dependency_overrides.pop(get_current_user, None)
        assert client.get("/threads").status_code == 401

        print("auth isolation ok")


if __name__ == "__main__":
    main()
