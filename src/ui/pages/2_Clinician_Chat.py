"""Clinician chat page: review pending requests and reply as a human doctor.

Run as part of ``streamlit run src/ui/Patient_Chat.py`` (multipage sidebar).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run src/ui/pages/...` to work without an editable install by
# putting the repository root (marked by pyproject.toml) on sys.path.
for _parent in Path(__file__).resolve().parents:
    if (_parent / "pyproject.toml").is_file():
        sys.path.insert(0, str(_parent))
        break

from src.core.runtime import configure_runtime  # noqa: E402

configure_runtime()

import requests  # noqa: E402
import streamlit as st  # noqa: E402

from src.ui.api_client import get_client  # noqa: E402

st.set_page_config(page_title="DrugGPT Clinician Chat", page_icon="🩺", layout="wide")
client = get_client()

st.title("🩺 Clinician chat")
st.error("Development-only review workflow. Use only under an authorised clinician's supervision.")

try:
    pending = client.reviews("pending")
except requests.RequestException as error:
    st.error(f"The API is unavailable: {error}")
    st.stop()

if not pending:
    st.success("No medication guidance is waiting for clinician review.")
    st.stop()

labels = {f"{item['id'][:8]} — {item['created_at']}": item for item in pending}
selected_label = st.sidebar.selectbox("Pending request", labels)
review = labels[selected_label]
review_id = review["id"]
conversation_id = review["conversation_id"]

details = client.review(review_id)
context = details.get("context", {})

left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("Pending review")
    st.write(f"**Review id:** {review_id[:8]}")
    st.write(f"**Conversation:** {conversation_id[:8]}")
    st.write(f"**Created:** {review.get('created_at')}")
    st.subheader("Patient context (issue summary)")
    st.json(context)
    st.subheader("Internal draft — do not share until approved")
    st.text_area("Draft", value=review.get("draft_guidance", ""), height=200, disabled=True)
    st.divider()
    with st.form("quick_decision"):
        reviewer = st.text_input("Clinician name", key="quick_reviewer")
        guidance = st.text_area("Approved patient-facing guidance", value=review.get("draft_guidance", ""), height=160)
        note = st.text_area("Review note", key="quick_note")
        approve = st.form_submit_button("Approve draft & send")
        reject = st.form_submit_button("Reject")
        if approve or reject:
            if not reviewer.strip():
                st.error("Enter the clinician reviewer name.")
            else:
                try:
                    result = client.decide_review(
                        review_id,
                        "approved" if approve else "rejected",
                        reviewer.strip(),
                        guidance if approve else None,
                        note or None,
                    )
                    st.success(f"Review complete: {result['status']}")
                    st.rerun()
                except requests.RequestException as error:
                    st.error(f"Decision failed: {error}")

with right:
    st.subheader("Conversation transcript")
    try:
        transcript = client.transcript(conversation_id)
    except requests.RequestException as error:
        st.error(f"Could not load transcript: {error}")
        transcript = {"messages": [], "open_review": None}

    for message in transcript.get("messages", []):
        role = message.get("role", "assistant")
        with st.chat_message(role):
            content = message["content"]
            if role == "clinician":
                reviewer = (message.get("metadata") or {}).get("reviewer_name", "clinician")
                content = f"🩺 **Dr. {reviewer}:**\n\n{content}"
            st.markdown(content)

    st.divider()
    st.subheader("Reply to the patient as a doctor")
    reply_reviewer = st.text_input("Your name", key="reply_reviewer")
    reply_message = st.text_area("Your message", height=180, key="reply_message")
    if st.button("Send reply", use_container_width=True, type="primary"):
        if not reply_reviewer.strip():
            st.error("Enter your name.")
        elif not reply_message.strip():
            st.error("Type a message before sending.")
        else:
            try:
                result = client.clinician_reply(
                    conversation_id,
                    reply_message.strip(),
                    reply_reviewer.strip(),
                    review_id,
                )
                st.success(f"Sent ({result.get('status')}). The patient will see your reply in the chat.")
                st.rerun()
            except requests.RequestException as error:
                st.error(f"Could not send reply: {error}")
