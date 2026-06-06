import uuid
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(
    page_title="DrugGPT"
)

st.title("💊 DrugGPT")


if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(
        uuid.uuid4()
    )

if "messages" not in st.session_state:
    st.session_state.messages = []


for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


if prompt := st.chat_input(
    "Ask a medical question..."
):

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        response = requests.post(
            API_URL,
            json={
                "message": prompt,
                "thread_id":
                st.session_state.thread_id
            }
        )

        answer = response.text

        st.markdown(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )