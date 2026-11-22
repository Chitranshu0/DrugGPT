"""Environment-backed application settings."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# This module lives at src/core/config.py, so parents[2] is the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load .env from the repository root regardless of the current working dir.
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _project_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def setup_logging(level: str = "INFO") -> None:
    """Configure project-wide logging with a clear, developer-friendly format.

    Application logs (``druggpt.*``) stay at the requested level so the story of
    each request is visible. Chatty third-party libraries are demoted to WARNING
    so their per-call HTTP/telemetry chatter does not drown out that narrative.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    for noisy_logger in ("httpx", "httpcore", "chromadb", "sentence_transformers", "posthog"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


@dataclass(frozen=True)
class Settings:
    """Runtime settings with local, non-source defaults.

    Precedence for every value: environment variable > .env > default.
    Values are re-read from ``os.environ`` on every instantiation so tests can
    override them after the module has been imported.
    """

    data_dir: Path = field(default_factory=lambda: _project_path(os.getenv("DRUGGPT_DATA_DIR", "data")))
    openrouter_api_key: str | None = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY"))
    llm_model: str = field(
        default_factory=lambda: os.getenv("DRUGGPT_MODEL", "nvidia/nemotron-3.5-lightning:free")
    )
    relevance_threshold: float = field(
        default_factory=lambda: float(os.getenv("DRUGGPT_RELEVANCE_THRESHOLD", "0.35"))
    )
    retrieval_k: int = field(default_factory=lambda: int(os.getenv("DRUGGPT_RETRIEVAL_K", "5")))
    # Clarifications default to a fixed, reviewed message instead of an LLM reply.
    llm_clarify: bool = field(
        default_factory=lambda: os.getenv("DRUGGPT_LLM_CLARIFY", "0").lower() in {"1", "true", "yes"}
    )
    # Index quality controls: drop low-value pages (front matter, indexes, TOCs).
    min_chunk_chars: int = field(default_factory=lambda: int(os.getenv("DRUGGPT_MIN_CHUNK_CHARS", "120")))
    skip_front_matter_pages: int = field(
        default_factory=lambda: int(os.getenv("DRUGGPT_SKIP_FRONT_MATTER_PAGES", "5"))
    )
    max_chunks_per_document: int = field(
        default_factory=lambda: int(os.getenv("DRUGGPT_MAX_CHUNKS_PER_DOCUMENT", "600"))
    )
    # LocalStore has no auth. Refuse non-loopback binds unless explicitly opted in.
    allow_remote: bool = field(
        default_factory=lambda: os.getenv("DRUGGPT_ALLOW_REMOTE", "0").lower() in {"1", "true", "yes"}
    )
    api_host: str = field(default_factory=lambda: os.getenv("DRUGGPT_API_HOST", "127.0.0.1"))
    api_port: int = field(default_factory=lambda: int(os.getenv("DRUGGPT_API_PORT", "8000")))
    ui_port: int = field(default_factory=lambda: int(os.getenv("DRUGGPT_UI_PORT", "8501")))
    # Eval-only model/key chain. The primary OpenRouter key is never overwritten;
    # the fallback key is used only when a primary call fails.
    eval_model: str = field(
        default_factory=lambda: os.getenv("DRUGGPT_EVAL_MODEL", "inclusionai/ling-3.2-flash:free")
    )
    eval_fallback_api_key: str | None = field(
        default_factory=lambda: os.getenv("OPENROUTER_FALLBACK_API_KEY")
    )
    eval_fallback_model: str = field(
        default_factory=lambda: os.getenv("DRUGGPT_EVAL_FALLBACK_MODEL", "inclusionai/ling-3.2-flash:free")
    )

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings from the current environment/.env file.

        Re-instantiating re-reads env vars, which is useful for tests that set
        ``os.environ`` before importing.
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
        if self.min_chunk_chars < 1:
            raise ValueError(f"DRUGGPT_MIN_CHUNK_CHARS must be >= 1, got {self.min_chunk_chars}")
        if self.skip_front_matter_pages < 0:
            raise ValueError(f"DRUGGPT_SKIP_FRONT_MATTER_PAGES must be >= 0, got {self.skip_front_matter_pages}")
        if self.max_chunks_per_document < 1:
            raise ValueError(f"DRUGGPT_MAX_CHUNKS_PER_DOCUMENT must be >= 1, got {self.max_chunks_per_document}")
        if not self.allow_remote and self.api_host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError(
                f"Refusing to bind to {self.api_host!r}: LocalStore has no authentication. "
                "Set DRUGGPT_ALLOW_REMOTE=1 only for a trusted local network demo."
            )


settings = Settings.from_env()
