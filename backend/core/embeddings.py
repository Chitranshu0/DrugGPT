"""Shared embedding model.

Both ingestion (vector_db.py) and retrieval (retrieval.py) use the same
embedding model. Keeping it here avoids creating it twice.
"""

from langchain_huggingface import HuggingFaceEmbeddings

from backend.core.config import EMBEDDING_MODEL_NAME


def get_embedding() -> HuggingFaceEmbeddings:
    """Create the HuggingFace embedding model.

    The model is created on demand so importing this file never downloads
    anything or makes a network call.
    """
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
