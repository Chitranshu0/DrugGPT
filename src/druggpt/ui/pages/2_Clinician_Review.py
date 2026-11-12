"""Clinician-review queue for local development only."""

import os

import requests
import streamlit as st

from druggpt.ui.api_client import DrugGPTApiClient

st.set_page_config(page_title="DrugGPT Clinician Review", page_icon="🩺", layout="wide")
client = DrugGPTApiClient(os.getenv("DRUGGPT_API_URL", "http://127.0.0.1:8000"))
st.title("🩺 Clinician medication review")
st.error("Development-only review workflow. Use only under an authorised clinician’s supervision.")

try:
    reviews = client.reviews("pending")
except requests.RequestException as error:
    st.error(f"The API is unavailable: {error}")
    st.stop()
if not reviews:
    st.success("No medication guidance is waiting for review.")
    st.stop()
labels = {f"{item['id'][:8]} — {item['created_at']}": item for item in reviews}
review = labels[st.selectbox("Pending request", labels)]
details = client.review(review["id"])
st.subheader("Patient context")
st.json(details["context"])
st.subheader("Internal draft — do not share until approved")
st.text_area("Draft", value=review["draft_guidance"], height=180, disabled=True)
with st.form("decision"):
    reviewer = st.text_input("Clinician name")
    guidance = st.text_area("Approved patient-facing guidance", value=review["draft_guidance"], height=180)
    note = st.text_area("Review note")
    approve = st.form_submit_button("Approve and send to chat")
    reject = st.form_submit_button("Reject")
    if approve or reject:
        if not reviewer.strip():
            st.error("Enter the clinician reviewer name.")
        else:
            result = client.decide_review(review["id"], "approved" if approve else "rejected", reviewer.strip(), guidance if approve else None, note or None)
            st.success(f"Review complete: {result['status']}")
            st.rerun()
