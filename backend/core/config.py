"""All environment-based settings live here.

Instead of calling os.getenv() in every file, modules import from this
file. That way a new developer can see every setting the project needs
in one place.
"""

import os

from dotenv import load_dotenv

# Load the .env file once, when this module is imported.
load_dotenv()

# --- LLM (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# --- Vector database (Pinecone) ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "medical-rag")
EMBEDDING_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL_NAME",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# --- Document ingestion ---
MEDICAL_BOOKS_DIR = os.getenv("MEDICAL_BOOKS_DIR", "Medical Books")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
