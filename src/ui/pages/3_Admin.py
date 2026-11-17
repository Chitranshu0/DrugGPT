"""Source-index administration page."""

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

st.set_page_config(page_title="DrugGPT Admin", page_icon="⚙️")
client = get_client()
st.title("⚙️ Source index administration")
try:
    status = client.status()
    if status["ready"]:
        st.success(f"Ready: {status['chunks_indexed']} chunks from {status['documents_indexed']} documents.")
    else:
        st.warning("No local source index is currently available. General educational chat still works.")
    st.caption(
        "The configured data directory is resolved by the API from its project path, "
        "not from the Streamlit working directory."
    )
    if st.button("Rebuild local medical source index"):
        with st.spinner("Building index from data/raw…"):
            result = client.rebuild()
        st.success(result["message"])
except requests.RequestException as error:
    st.error(f"The API is unavailable: {error}")
