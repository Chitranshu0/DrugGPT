"""Source-index administration page."""

import os

import requests
import streamlit as st

from druggpt.ui.api_client import DrugGPTApiClient

st.set_page_config(page_title="DrugGPT Admin", page_icon="⚙️")
client = DrugGPTApiClient(os.getenv("DRUGGPT_API_URL", "http://127.0.0.1:8000"))
st.title("⚙️ Source index administration")
try:
    status = client.status()
    if status["ready"]:
        st.success(f"Ready: {status['chunks_indexed']} chunks from {status['documents_indexed']} documents.")
    else:
        st.warning("No local source index is currently available. General educational chat still works.")
    st.caption("The configured data directory is resolved by the API from its project path, not from the Streamlit working directory.")
    if st.button("Rebuild local medical source index"):
        with st.spinner("Building index from data/raw…"):
            result = client.rebuild()
        st.success(result["message"])
except requests.RequestException as error:
    st.error(f"The API is unavailable: {error}")
