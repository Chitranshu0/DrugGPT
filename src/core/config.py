"""Environment-backed application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# src/druggpt is gone; this module lives at src/core/config.py, so parents[2]
# is the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from the repository root regardless of the current working dir.
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    """Runtime settings with local, non-source defaults.

    Precedence for every value: CLI flag > environment variable > .env > default.
    Values are re-read from ``os.environ`` on every instantiation so that tests
    and the CLI can override them after the module has been imported.
    """

    data_dir: Path = field(default_factory=lambda: _project_path(os.getenv("DRUGGPT_DATA_DIR", "data")))
    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    groq_model: str = field(default_factory=lambda: os.getenv("DRUGGPT_MODEL", "openai/gpt-oss-120b"))
    relevance_threshold: float = field(
        default_factory=lambda: float(os.getenv("DRUGGPT_RELEVANCE_THRESHOLD", "0.35"))
    )
    retrieval_k: int = field(default_factory=lambda: int(os.getenv("DRUGGPT_RETRIEVAL_K", "5")))
    api_host: str = field(default_factory=lambda: os.getenv("DRUGGPT_API_HOST", "127.0.0.1"))
    api_port: int = field(default_factory=lambda: int(os.getenv("DRUGGPT_API_PORT", "8000")))
    ui_port: int = field(default_factory=lambda: int(os.getenv("DRUGGPT_UI_PORT", "8501")))

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the current environment/.env file.

        Re-instantiating re-reads env vars, which is useful for tests that set
        ``os.environ`` before importing or for the CLI's --data-dir override.
        """
        return cls()

    @property
    def raw_documents_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def checkpoint_db(self) -> Path:
        return self.data_dir / "checkpoints" / "langgraph.db"

    @property
    def application_db(self) -> Path:
        return self.data_dir / "druggpt.db"

    def ensure_directories(self) -> None:
        """Create the local runtime directories DrugGPT needs at startup."""
        for directory in (self.raw_documents_dir, self.chroma_dir, self.checkpoint_db.parent):
            directory.mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        """Raise ValueError when settings are out of acceptable range."""
        if not 0.0 <= self.relevance_threshold <= 1.0:
            raise ValueError(f"DRUGGPT_RELEVANCE_THRESHOLD must be in [0, 1], got {self.relevance_threshold}")
        if self.retrieval_k < 1:
            raise ValueError(f"DRUGGPT_RETRIEVAL_K must be >= 1, got {self.retrieval_k}")


settings = Settings.from_env()
