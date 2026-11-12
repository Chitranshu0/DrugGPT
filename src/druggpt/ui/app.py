"""Run with: streamlit run src/druggpt/ui/app.py"""

import os
import uuid

import requests
import streamlit as st

from druggpt.ui.api_client import DrugGPTApiClient

st.set_page_config(page_title="DrugGPT", page_icon="💊", layout="wide")
client = DrugGPTApiClient(os.getenv("DRUGGPT_API_URL", "http://127.0.0.1:8000"))

st.title("💊 DrugGPT")
st.caption("Educational, source-grounded medical science and drug-study research assistant.")
st.info("Not medical advice. DrugGPT cannot diagnose, prescribe, or guide urgent treatment.")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("Medical source index")
    try:
        index_status = client.status()
        if index_status["ready"]:
            st.success(f"Ready: {index_status['chunks_indexed']} evidence chunks")
        else:
            st.warning("No source index is available. Add PDFs to data/raw and rebuild.")
    except requests.RequestException:
        st.error("Backend is unavailable.")
    if st.button("Rebuild medical source index", use_container_width=True):
        try:
            with st.spinner("Loading PDFs and building the index..."):
                rebuilt = client.rebuild()
            st.success(f"Indexed {rebuilt['documents_indexed']} PDFs into {rebuilt['chunks_indexed']} chunks.")
        except requests.RequestException as error:
            st.error(f"Rebuild failed: {error}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        for source in message.get("sources", []):
            label = f"[{source['id']}] {source['title']}" + (f" — page {source['page']}" if source.get("page") else "")
            with st.expander(label):
                st.caption(f"Relevance: {source['relevance_score']:.0%}")
                st.write(source["excerpt"])

if prompt := st.chat_input("Ask a medical science or drug-study question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        try:
            with st.status("Searching medical sources…", expanded=False) as status:
                result = client.chat(prompt, st.session_state.thread_id)
                activity = result.get("tool_activity")
                status.update(
                    label=activity["message"] if activity else "Request checked.",
                    state="complete",
                    expanded=False,
                )
            st.markdown(result["answer"])
            for source in result.get("sources", []):
                label = f"[{source['id']}] {source['title']}" + (f" — page {source['page']}" if source.get("page") else "")
                with st.expander(label):
                    st.caption(f"Relevance: {source['relevance_score']:.0%}")
                    st.write(source["excerpt"])
        except requests.RequestException as error:
            result = {"answer": f"Unable to reach DrugGPT: {error}", "sources": []}
            st.error(result["answer"])
    st.session_state.messages.append({"role": "assistant", "content": result["answer"], "sources": result.get("sources", [])})
