"""Local patient-profile page."""

import sys
from pathlib import Path

# Allow `streamlit run src/ui/pages/...` to work without an editable install by
# putting the repository root (marked by pyproject.toml) on sys.path.
for _parent in Path(__file__).resolve().parents:
    if (_parent / "pyproject.toml").is_file():
        sys.path.insert(0, str(_parent))
        break

import requests  # noqa: E402
import streamlit as st  # noqa: E402

from src.ui.api_client import get_client  # noqa: E402

st.set_page_config(page_title="DrugGPT Patient Profile", page_icon="🧾", layout="wide")
client = get_client()
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
