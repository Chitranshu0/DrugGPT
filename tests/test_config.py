from dataclasses import replace

import pytest

from src.core.config import PROJECT_ROOT, Settings


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
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
    settings = Settings.from_env()
    assert settings.openrouter_api_key is None
    assert settings.llm_model == "nvidia/nemotron-3.5-lightning:free"
    assert settings.relevance_threshold == 0.35
    assert settings.retrieval_k == 5
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.ui_port == 8501


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


def test_ensure_directories_creates_runtime_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("DRUGGPT_DATA_DIR", str(tmp_path / "data"))
    settings = Settings.from_env()
    settings.ensure_directories()
    assert (tmp_path / "data" / "raw").is_dir()
    assert (tmp_path / "data" / "chroma").is_dir()
    assert (tmp_path / "data" / "checkpoints").is_dir()
