"""Streamlit chat UI for DrugGPT.

Run from the project root:

    streamlit run frontend/streamlit_app.py

The backend owns conversation history in SQLite. This UI only keeps the
active thread id and the messages currently on screen.
"""

import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT = 120

st.set_page_config(page_title="DrugGPT", page_icon="💊", layout="wide")
st.title("💊 DrugGPT")


def _request(method: str, path: str, **kwargs) -> requests.Response:
    """Send a request to the backend and raise on HTTP errors."""
    response = requests.request(
        method,
        f"{API_BASE_URL}{path}",
        timeout=REQUEST_TIMEOUT,
        **kwargs,
    )
    response.raise_for_status()
    return response


def fetch_threads() -> list[dict]:
    """Load the conversation list."""
    return _request("GET", "/threads").json()


def create_thread() -> dict:
    """Create a new empty conversation."""
    return _request("POST", "/threads").json()


def fetch_thread(thread_id: str) -> dict:
    """Load one conversation with its persisted messages."""
    return _request("GET", f"/threads/{thread_id}").json()


def rename_thread(thread_id: str, title: str) -> None:
    """Rename a conversation."""
    _request("PATCH", f"/threads/{thread_id}", json={"title": title})


def delete_thread(thread_id: str) -> None:
    """Delete a conversation and its graph state."""
    _request("DELETE", f"/threads/{thread_id}")


def ask_backend(question: str, thread_id: str) -> str:
    """Send the question to the FastAPI backend and return the answer."""
    response = _request(
        "POST",
        "/chat",
        json={"message": question, "thread_id": thread_id},
    )
    return response.text


def init_session() -> None:
    """Create the session values we need on the first page load."""
    st.session_state.setdefault("thread_id", None)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("threads", [])


def start_new_chat() -> None:
    """Create a thread and make it the active conversation."""
    thread = create_thread()
    st.session_state.thread_id = thread["thread_id"]
    st.session_state.messages = []


def open_thread(thread_id: str) -> None:
    """Load a conversation's messages into the current session."""
    detail = fetch_thread(thread_id)
    st.session_state.thread_id = thread_id
    st.session_state.messages = detail["messages"]


def show_history() -> None:
    """Render all messages in the active conversation."""
    if not st.session_state.messages:
        st.caption("Start a new chat or pick one from the sidebar.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def render_sidebar() -> None:
    """Render the chat list and its controls."""
    with st.sidebar:
        st.subheader("Chats")

        if st.button("➕ New chat", use_container_width=True):
            try:
                start_new_chat()
            except requests.RequestException as exc:
                st.error(f"Could not create a chat: {exc}")
            else:
                st.rerun()

        try:
            threads = fetch_threads()
        except requests.RequestException as exc:
            st.error(f"Could not load chats: {exc}")
            return

        st.session_state.threads = threads

        if not threads:
            st.caption("No chats yet.")
            return

        for thread in threads:
            thread_id = thread["thread_id"]
            active = thread_id == st.session_state.thread_id

            open_col, rename_col, delete_col = st.columns([0.72, 0.14, 0.14])

            if open_col.button(
                thread["title"],
                key=f"open-{thread_id}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                try:
                    open_thread(thread_id)
                except requests.RequestException as exc:
                    st.error(f"Could not open chat: {exc}")
                else:
                    st.rerun()

            with rename_col.popover("✏️"):
                new_title = st.text_input(
                    "Title",
                    value=thread["title"],
                    key=f"title-{thread_id}",
                    label_visibility="collapsed",
                )
                if st.button("Save", key=f"save-{thread_id}"):
                    if not new_title.strip():
                        st.warning("Title cannot be empty.")
                    else:
                        try:
                            rename_thread(thread_id, new_title.strip())
                        except requests.RequestException as exc:
                            st.error(f"Could not rename chat: {exc}")
                        else:
                            st.rerun()

            if delete_col.button("🗑", key=f"delete-{thread_id}", help="Delete chat"):
                try:
                    delete_thread(thread_id)
                except requests.RequestException as exc:
                    st.error(f"Could not delete chat: {exc}")
                else:
                    if active:
                        st.session_state.thread_id = None
                        st.session_state.messages = []
                    st.rerun()


def main() -> None:
    init_session()
    render_sidebar()
    show_history()

    question = st.chat_input("Ask a medical question...")
    if not question:
        return

    try:
        if st.session_state.thread_id is None:
            start_new_chat()

        thread_id = st.session_state.thread_id

        st.session_state.messages.append(
            {"role": "user", "content": question}
        )
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Searching the medical books..."):
                answer = ask_backend(question, thread_id)
            st.markdown(answer)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )
    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return

    # Refresh the sidebar so a new thread or title appears immediately.
    st.rerun()


main()
