"""Patient chat page.

Run with ``streamlit run src/ui/Patient_Chat.py`` (:8501).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run src/ui/Patient_Chat.py` to work without an editable install
# by putting the repository root (marked by pyproject.toml) on sys.path.
for _parent in Path(__file__).resolve().parents:
    if (_parent / "pyproject.toml").is_file():
        sys.path.insert(0, str(_parent))
        break

from src.core.runtime import configure_runtime  # noqa: E402

configure_runtime()

import requests  # noqa: E402
import streamlit as st  # noqa: E402

from src.ui.api_client import get_client  # noqa: E402

st.set_page_config(page_title="DrugGPT Patient Chat", page_icon="💊", layout="wide")
client = get_client()

st.title("💊 DrugGPT")
st.caption("Medical information chat for education and clinician-reviewed medication guidance.")
st.warning("Local development demo — do not enter real patient data. This is not emergency or medical care.")


@st.cache_data(ttl=30, show_spinner=False)
def load_patients() -> list[dict]:
    return client.patients()


@st.cache_data(ttl=30, show_spinner=False)
def load_conversations(patient_id: str) -> list[dict]:
    return client.conversations(patient_id)


try:
    patients = load_patients()
except requests.RequestException as error:
    st.error(f"The API is unavailable: {error}")
    st.stop()

with st.sidebar:
    st.header("Patient and conversation")
    if not patients:
        name = st.text_input("Create a local demo profile", value="Guest patient")
        if st.button("Create profile", use_container_width=True):
            client.create_patient(name)
            load_patients.clear()
            st.rerun()
        st.stop()
    patient_names = {f"{patient['name']} ({patient['id'][:8]})": patient for patient in patients}
    selected_label = st.selectbox("Active patient", patient_names)
    patient = patient_names[selected_label]
    conversations = load_conversations(patient["id"])
    if st.button("New conversation", use_container_width=True):
        client.create_conversation(patient["id"], "New medical chat")
        load_conversations.clear()
        st.rerun()
    if not conversations:
        conversation = client.create_conversation(patient["id"], "General medical chat")
        load_conversations.clear()
    else:
        labels = {f"{item['title']} ({item['id'][:8]})": item for item in conversations}
        conversation = labels[st.selectbox("Conversation", labels)]
    st.divider()
    st.caption(
        "Personal decisions about medicines, tests, treatments, and test reports are paused for clinician review."
    )


@st.fragment(run_every="10s")
def render_transcript(conversation_id: str) -> None:
    """Poll for new messages only, instead of re-fetching the whole transcript."""
    cursor_key = f"last_message:{conversation_id}"
    try:
        payload = client.messages_since(conversation_id, after=st.session_state.get(cursor_key))
    except requests.RequestException as error:
        st.error(f"Could not refresh the transcript: {error}")
        return
    for message in payload.get("messages", []):
        role = message.get("role", "assistant")
        with st.chat_message(role):
            content = message["content"]
            if role == "clinician":
                reviewer = (message.get("metadata") or {}).get("reviewer_name", "clinician")
                content = f"🩺 **Dr. {reviewer}:**\n\n{content}"
            st.markdown(content)
            metadata = message.get("metadata", {})
            if metadata.get("answer_mode") == "general_education":
                st.caption("General educational information — not a diagnosis or prescription.")
            if metadata.get("answer_mode") == "clarification":
                st.caption("Follow-up question to better understand your request.")
            show_sources(metadata.get("sources", []))
    if payload.get("messages"):
        st.session_state[cursor_key] = payload["messages"][-1]["id"]


def show_sources(sources: list[dict]) -> None:
    for source in sources:
        title = f"[{source['id']}] {source['title']}"
        if source.get("page"):
            title += f" — page {source['page']}"
        with st.expander(title):
            st.caption(f"Relevance: {source['relevance_score']:.0%}")
            st.write(source["excerpt"])


def render_answer_details(result: dict, streamed_text: str) -> None:
    """Show the non-token parts of a streamed response."""
    if not streamed_text.strip():
        st.markdown(result["answer"])
    answer_mode = result.get("answer_mode", "")
    if result.get("status") == "review_pending":
        st.info("A clinician review is pending. Check back here after it has been reviewed.")
    elif answer_mode == "clarification":
        st.caption("I need a little more detail to help — please answer the question above.")
    elif answer_mode == "general_education":
        st.caption("General educational information — not a diagnosis or prescription.")
    show_sources(result.get("sources", []))


render_transcript(conversation["id"])

if prompt := st.chat_input("Ask a health or medical question..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        final: dict[str, dict] = {}
        try:

            def tokens():
                for event in client.send_message_stream(conversation["id"], prompt):
                    if event["type"] == "token":
                        yield event["token"]
                    elif event["type"] == "response":
                        final["response"] = event["response"]
                    elif event["type"] == "error":
                        raise RuntimeError(event.get("detail", "The streaming response failed."))

            with st.status("Thinking through your medical question…", expanded=False) as status:
                streamed_text = st.write_stream(tokens())
                status.update(label="Response ready", state="complete", expanded=False)
            result = final.get("response")
            if result is None:
                st.error("The API returned no response for this message.")
            else:
                render_answer_details(result, streamed_text)
            # Advance the polling cursor so the new messages are not re-rendered.
            history = client.messages(conversation["id"])
            if history:
                st.session_state[f"last_message:{conversation['id']}"] = history[-1]["id"]
        except (requests.RequestException, RuntimeError) as error:
            st.error(f"Unable to send the message: {error}")
