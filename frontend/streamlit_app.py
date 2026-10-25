"""Streamlit chat UI for DrugGPT.

Run from the project root:

    streamlit run frontend/streamlit_app.py
"""

import uuid

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(page_title="DrugGPT")
st.title("💊 DrugGPT")


def init_session():
    """Create the session values we need on the first page load."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "messages" not in st.session_state:
        st.session_state.messages = []


def show_history():
    """Render all previous chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def ask_backend(question: str) -> str:
    """Send the question to the FastAPI backend and return the answer."""
    response = requests.post(
        API_URL,
        json={
            "message": question,
            "thread_id": st.session_state.thread_id,
        },
    )
    response.raise_for_status()
    return response.text


def main():
    init_session()
    show_history()

    question = st.chat_input("Ask a medical question...")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        answer = ask_backend(question)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})


main()
