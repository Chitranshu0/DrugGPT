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


# --- LLM (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# --- Google embeddings ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "models/gemini-embedding-001",
)

# Must match the output dimensionality used by get_embedding().
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))

# --- Vector database (Pinecone) ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv(
    "PINECONE_INDEX_NAME",
    "druggpt-medical-google-768",
)

# --- Document ingestion ---
MEDICAL_BOOKS_DIR = os.getenv("MEDICAL_BOOKS_DIR", "Medical Books")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

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
