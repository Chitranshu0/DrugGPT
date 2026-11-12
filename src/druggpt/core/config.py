"""Environment-backed application settings."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime settings with local, non-source defaults."""

    data_dir: Path = Path(os.getenv("DRUGGPT_DATA_DIR", "data"))
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("DRUGGPT_MODEL", "openai/gpt-oss-120b")
    relevance_threshold: float = float(os.getenv("DRUGGPT_RELEVANCE_THRESHOLD", "0.35"))
    retrieval_k: int = int(os.getenv("DRUGGPT_RETRIEVAL_K", "5"))

    @property
    def raw_documents_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def checkpoint_db(self) -> Path:
        return self.data_dir / "checkpoints" / "medicine_chat.db"


settings = Settings()
