import requests
import streamlit as st
import uuid

API_BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{API_BASE_URL}/chat"

st.set_page_config(
    page_title="DrugGPT"
)

st.title("💊 DrugGPT")

if "rebuild_in_progress" not in st.session_state:
    st.session_state.rebuild_in_progress = False


def get_vector_database_status():
    try:
        response = requests.get(f"{API_BASE_URL}/vector-db/status", timeout=10)
        response.raise_for_status()
        return response.json(), None
    except requests.RequestException as error:
        return None, str(error)


with st.sidebar:
    st.header("Vector Database")
    database_status, status_error = get_vector_database_status()

    if status_error:
        st.warning("Could not reach the backend to check the vector database.")
    elif database_status["ready"]:
        st.success(f"Ready: {database_status['chunks_indexed']} chunks indexed")
    else:
        st.warning("Not built yet. Rebuild it before chatting.")

    if st.button(
        "Rebuild from Medical Books",
        disabled=st.session_state.rebuild_in_progress,
        use_container_width=True,
    ):
        st.session_state.rebuild_in_progress = True
        try:
            with st.spinner("Loading PDFs and rebuilding ChromaDB..."):
                response = requests.post(
                    f"{API_BASE_URL}/vector-db/rebuild", timeout=600
                )
                response.raise_for_status()
                result = response.json()
            st.success(
                f"Indexed {result['documents_indexed']} PDFs into "
                f"{result['chunks_indexed']} chunks."
            )
        except requests.RequestException as error:
            detail = ""
            if error.response is not None:
                try:
                    detail = error.response.json().get("detail", "")
                except ValueError:
                    detail = error.response.text
            st.error(detail or f"Rebuild failed: {error}")
        finally:
            st.session_state.rebuild_in_progress = False

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

        try:
            response = requests.post(
                API_URL,
                json={
                    "message": prompt,
                    "thread_id": st.session_state.thread_id,
                },
                timeout=120,
            )
            response.raise_for_status()
            answer = response.text
            st.markdown(answer)
        except requests.RequestException as error:
            if error.response is not None and error.response.status_code == 503:
                answer = "The medical vector database is not ready. Rebuild it from the sidebar first."
            else:
                answer = f"Unable to get an answer from the backend: {error}"
            st.warning(answer)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer
        }
    )
