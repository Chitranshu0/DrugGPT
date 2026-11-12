"""Local patient-profile page."""

import os

import requests
import streamlit as st

from druggpt.ui.api_client import DrugGPTApiClient

st.set_page_config(page_title="DrugGPT Patient Profile", page_icon="🧾", layout="wide")
client = DrugGPTApiClient(os.getenv("DRUGGPT_API_URL", "http://127.0.0.1:8000"))
st.title("🧾 Patient profile")
st.warning("Local development demo — do not enter real patient data.")

try:
    patients = client.patients()
except requests.RequestException as error:
    st.error(f"The API is unavailable: {error}")
    st.stop()
if not patients:
    st.info("Create a patient from the chat page first.")
    st.stop()
labels = {f"{patient['name']} ({patient['id'][:8]})": patient for patient in patients}
patient = labels[st.selectbox("Patient", labels)]
summary = client.patient_summary(patient["id"])
st.subheader("Approved clinical summary")
st.write(summary["summary"] or "No approved summary has been recorded.")
st.subheader("Facts")
for fact in summary["facts"]:
    status = "approved" if fact["approved"] else "awaiting review"
    st.write(f"- **{fact['category']}**: {fact['value']} ({status})")
with st.form("add_fact"):
    category = st.selectbox("Category", ["allergy", "condition", "medication", "history", "preference"])
    value = st.text_input("Value")
    approved = st.checkbox("Mark approved", value=True)
    if st.form_submit_button("Save fact") and value.strip():
        client.add_fact(patient["id"], category, value.strip(), approved)
        st.rerun()
