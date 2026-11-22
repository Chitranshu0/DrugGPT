import os
from dataclasses import replace

import pytest

from src.core.config import PROJECT_ROOT, Settings
from src.core.runtime import configure_runtime


def test_runtime_shims_disable_tensorflow(monkeypatch):
    for key in ("USE_TF", "TRANSFORMERS_NO_TF", "TF_CPP_MIN_LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)
    # configure_runtime is idempotent; reset its guard so the assertion is meaningful.
    import src.core.runtime as runtime

    monkeypatch.setattr(runtime, "_CONFIGURED", False)
    configure_runtime()
    assert os.environ["USE_TF"] == "0"
    assert os.environ["TRANSFORMERS_NO_TF"] == "1"
    assert os.environ["TF_CPP_MIN_LOG_LEVEL"] == "3"


def test_project_root_is_repository_root():
    assert PROJECT_ROOT.name == "DrugGPT"
    assert (PROJECT_ROOT / "pyproject.toml").exists()
    assert (PROJECT_ROOT / "src" / "core" / "config.py").exists()


def test_settings_read_env_and_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("DRUGGPT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DRUGGPT_RELEVANCE_THRESHOLD", "0.7")
    monkeypatch.setenv("DRUGGPT_RETRIEVAL_K", "8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    settings = Settings.from_env()
    assert settings.data_dir == tmp_path / "data"
    assert settings.relevance_threshold == 0.7
    assert settings.retrieval_k == 8
    assert settings.openrouter_api_key == "test-key"


def test_defaults_when_env_missing(monkeypatch):
    for var in (
        "DRUGGPT_DATA_DIR",
        "DRUGGPT_MODEL",
        "DRUGGPT_RELEVANCE_THRESHOLD",
        "DRUGGPT_RETRIEVAL_K",
        "DRUGGPT_API_HOST",
        "DRUGGPT_API_PORT",
        "DRUGGPT_UI_PORT",
        "DRUGGPT_CORS_ORIGINS",
        "DRUGGPT_CORS_ORIGIN_REGEX",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    settings = Settings.from_env()
    assert settings.openrouter_api_key is None
    assert settings.cors_origins == (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    )
    assert "vercel" in settings.cors_origin_regex
    assert settings.llm_model == "nvidia/nemotron-3.5-lightning:free"
    assert settings.relevance_threshold == 0.35
    assert settings.retrieval_k == 5
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.ui_port == 8501


def test_cors_origins_parse_comma_separated_env(monkeypatch):
    monkeypatch.setenv(
        "DRUGGPT_CORS_ORIGINS",
        "https://app.example.com, http://localhost:3000 ,",
    )
    assert Settings.from_env().cors_origins == ("https://app.example.com", "http://localhost:3000")


def test_cors_origin_regex_can_be_overridden(monkeypatch):
    monkeypatch.setenv("DRUGGPT_CORS_ORIGIN_REGEX", r"^https://app\.example\.com$")
    assert Settings.from_env().cors_origin_regex == r"^https://app\.example\.com$"


def test_validation_rejects_bad_threshold(monkeypatch):
    monkeypatch.setenv("DRUGGPT_RELEVANCE_THRESHOLD", "1.5")
    with pytest.raises(ValueError):
        Settings.from_env().validate()


def test_validation_rejects_bad_retrieval_k(monkeypatch):
    monkeypatch.setenv("DRUGGPT_RETRIEVAL_K", "0")
    with pytest.raises(ValueError):
        Settings.from_env().validate()


def test_replace_keeps_settings_dataclass_semantics(tmp_path):
    base = Settings.from_env()
    override = replace(base, data_dir=tmp_path / "data", relevance_threshold=0.9)
    assert override.data_dir == tmp_path / "data"
    assert override.relevance_threshold == 0.9
    assert override.openrouter_api_key == base.openrouter_api_key


def test_validation_refuses_remote_bind_without_opt_in():
    settings = replace(Settings.from_env(), api_host="0.0.0.0", allow_remote=False)
    with pytest.raises(ValueError, match="Refusing to bind"):
        settings.validate()


def test_validation_allows_remote_bind_when_explicitly_enabled():
    settings = replace(Settings.from_env(), api_host="0.0.0.0", allow_remote=True)
    settings.validate()


def test_ensure_directories_creates_runtime_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("DRUGGPT_DATA_DIR", str(tmp_path / "data"))
    settings = Settings.from_env()
    settings.ensure_directories()
    assert (tmp_path / "data" / "raw").is_dir()
    assert (tmp_path / "data" / "chroma").is_dir()
    assert (tmp_path / "data" / "checkpoints").is_dir()
