"""All environment-based settings live here.

Instead of calling os.getenv() in every file, modules import from this
file. That way a new developer can see every setting the project needs
in one place.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load the .env file once, when this module is imported.
load_dotenv()

# Resolve relative paths from the project root, not the current directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_path(value: str) -> Path:
    """Return an absolute path, treating relative values as project-relative."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _get_bool(name: str, default: bool) -> bool:
    """Read a true/false value from the environment."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# --- LLM (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# The scope guard is a tiny extra check that keeps the chatbot medical-only.
# It fails open (allows the question) if the classifier call itself fails.
MEDICAL_SCOPE_GUARD = _get_bool("MEDICAL_SCOPE_GUARD", True)
SCOPE_MODEL = os.getenv("SCOPE_MODEL") or LLM_MODEL

# --- Vector database (Pinecone) ---
# The index is a Pinecone document index. Pinecone embeds chunk_text with
# NVIDIA llama-text-embed-v2 on the server, so the app never generates
# embeddings locally.
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "medicalchatbot")
PINECONE_INDEX_HOST = (
    os.getenv("PINECONE_INDEX_HOST", "")
    .strip()
    .removeprefix("https://")
    .removeprefix("http://")
    .rstrip("/")
)
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "medical-books")
PINECONE_EMBED_MODEL = os.getenv("PINECONE_EMBED_MODEL", "llama-text-embed-v2")
PINECONE_EMBED_DIMENSION = int(os.getenv("PINECONE_EMBED_DIMENSION", "1024"))
PINECONE_EMBED_METRIC = os.getenv("PINECONE_EMBED_METRIC", "cosine")

# --- Retrieval ---
# "hybrid" = dense embedding search + BM25 keyword search, fused with RRF.
# "dense"  = semantic search only.
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "hybrid").strip().lower()
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
RETRIEVAL_FETCH_K = int(os.getenv("RETRIEVAL_FETCH_K", "20"))
RETRIEVAL_RRF_K = int(os.getenv("RETRIEVAL_RRF_K", "60"))
RETRIEVAL_RERANK = _get_bool("RETRIEVAL_RERANK", True)
RERANK_MODEL = os.getenv("RERANK_MODEL", "bge-reranker-v2-m3")
MEDICAL_DOMAIN = os.getenv("MEDICAL_DOMAIN", "medical")

# --- Document ingestion ---
MEDICAL_BOOKS_DIR = os.getenv("MEDICAL_BOOKS_DIR", "Medical Books")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
MIN_CHUNK_CHARS = int(os.getenv("MIN_CHUNK_CHARS", "80"))
UPSERT_BATCH_SIZE = int(os.getenv("UPSERT_BATCH_SIZE", "90"))

# --- Persistence (SQLite) ---
DATA_DIR = _resolve_path(os.getenv("DATA_DIR", "data"))
SQLITE_CHECKPOINT_DB = _resolve_path(
    os.getenv("SQLITE_CHECKPOINT_DB", str(DATA_DIR / "checkpoints.sqlite"))
)
SQLITE_APP_DB = _resolve_path(
    os.getenv("SQLITE_APP_DB", str(DATA_DIR / "app.sqlite"))
)
SQLITE_BUSY_TIMEOUT_MS = int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "5000"))

# --- Conversation memory ---
# How many recent messages are sent to the LLM with each question.
MEMORY_WINDOW_MESSAGES = int(os.getenv("MEMORY_WINDOW_MESSAGES", "12"))
THREAD_TITLE_MAX_LEN = int(os.getenv("THREAD_TITLE_MAX_LEN", "60"))
