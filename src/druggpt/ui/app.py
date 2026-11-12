"""Patient chat page. Run with: streamlit run src/druggpt/ui/app.py."""

import os

import requests
import streamlit as st

from druggpt.ui.api_client import DrugGPTApiClient

st.set_page_config(page_title="DrugGPT Patient Chat", page_icon="💊", layout="wide")
client = DrugGPTApiClient(os.getenv("DRUGGPT_API_URL", "http://127.0.0.1:8000"))


def show_sources(sources: list[dict]) -> None:
    for source in sources:
        title = f"[{source['id']}] {source['title']}"
        if source.get("page"):
            title += f" — page {source['page']}"
        with st.expander(title):
            st.caption(f"Relevance: {source['relevance_score']:.0%}")
            st.write(source["excerpt"])


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
    st.caption("Medication-related personal guidance is paused for clinician review before it appears here.")

for message in client.messages(conversation["id"]):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        metadata = message.get("metadata", {})
        if metadata.get("answer_mode") == "general_education":
            st.caption("General educational information — not a diagnosis or prescription.")
        show_sources(metadata.get("sources", []))

if prompt := st.chat_input("Ask a health or medical question..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            with st.status("Thinking through your medical question…", expanded=False) as status:
                result = client.send_message(conversation["id"], prompt)
                status.update(label="Response ready", state="complete", expanded=False)
            st.markdown(result["answer"])
            if result["status"] == "review_pending":
                st.info("A clinician review is pending. Check back here after it is approved or rejected.")
            if result["answer_mode"] == "general_education":
                st.caption("General educational information — not a diagnosis or prescription.")
            show_sources(result.get("sources", []))
        except requests.RequestException as error:
            st.error(f"Unable to send the message: {error}")
