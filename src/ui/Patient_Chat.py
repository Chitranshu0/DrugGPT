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

import requests  # noqa: E402
import streamlit as st  # noqa: E402

from src.ui.api_client import get_client  # noqa: E402

st.set_page_config(page_title="DrugGPT Patient Chat", page_icon="💊", layout="wide")
client = get_client()

st.title("💊 DrugGPT")
st.caption("Medical information chat for education and clinician-reviewed medication guidance.")
st.warning("Local development demo — do not enter real patient data. This is not emergency or medical care.")

try:
    patients = client.patients()
except requests.RequestException as error:
    st.error(f"The API is unavailable: {error}")
    st.stop()

with st.sidebar:
    st.header("Patient and conversation")
    if not patients:
        name = st.text_input("Create a local demo profile", value="Guest patient")
        if st.button("Create profile", use_container_width=True):
            client.create_patient(name)
            st.rerun()
        st.stop()
    patient_names = {f"{patient['name']} ({patient['id'][:8]})": patient for patient in patients}
    selected_label = st.selectbox("Active patient", patient_names)
    patient = patient_names[selected_label]
    conversations = client.conversations(patient["id"])
    if st.button("New conversation", use_container_width=True):
        client.create_conversation(patient["id"], "New medical chat")
        st.rerun()
    if not conversations:
        conversation = client.create_conversation(patient["id"], "General medical chat")
    else:
        labels = {f"{item['title']} ({item['id'][:8]})": item for item in conversations}
        conversation = labels[st.selectbox("Conversation", labels)]
    st.divider()
    st.caption(
        "Personal decisions about medicines, tests, treatments, and test reports are paused for clinician review."
    )


@st.fragment(run_every="3s")
def render_transcript(conversation_id: str) -> None:
    for message in client.messages(conversation_id):
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


def show_sources(sources: list[dict]) -> None:
    for source in sources:
        title = f"[{source['id']}] {source['title']}"
        if source.get("page"):
            title += f" — page {source['page']}"
        with st.expander(title):
            st.caption(f"Relevance: {source['relevance_score']:.0%}")
            st.write(source["excerpt"])


render_transcript(conversation["id"])

if prompt := st.chat_input("Ask a health or medical question..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            with st.status("Thinking through your medical question…", expanded=False) as status:
                result = client.send_message(conversation["id"], prompt)
                status.update(label="Response ready", state="complete", expanded=False)
            st.markdown(result["answer"])
            answer_mode = result.get("answer_mode", "")
            if answer_mode == "human_hold":
                st.info("A clinician has taken over this conversation. They will reply here directly — check back shortly.")
            elif result["status"] == "review_pending":
                st.info("A clinician review is pending. Check back here after it has been reviewed.")
            elif answer_mode == "clarification":
                st.caption("I need a little more detail to help — please answer the question above.")
            elif answer_mode == "general_education":
                st.caption("General educational information — not a diagnosis or prescription.")
            show_sources(result.get("sources", []))
        except requests.RequestException as error:
            st.error(f"Unable to send the message: {error}")
