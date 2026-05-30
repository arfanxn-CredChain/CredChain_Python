import pytest

from app.config import Settings


def test_default_values():
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.fastapi_port == 8081
    assert s.log_level == "info"
    assert s.log_output == "stdout"
    assert s.model_dir == "/models"
    assert s.easyocr_langs == ["id", "en"]
    assert s.llm_max_new_tokens == 512
    assert s.llm_device == "cpu"
    assert s.llm_model_name == "Qwen2.5-0.5B-Instruct"
    assert s.embedding_model_name == "LaBSE"
    assert s.cors_allow_origins == ["*"]


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("FASTAPI_PORT", "9090")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("EASYOCR_LANGS", "en,fr,de")
    monkeypatch.setenv("LLM_DEVICE", "cuda")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.fastapi_port == 9090
    assert s.log_level == "debug"
    assert s.easyocr_langs == ["en", "fr", "de"]
    assert s.llm_device == "cuda"


def test_invalid_port_rejected(monkeypatch):
    monkeypatch.setenv("FASTAPI_PORT", "not_a_number")
    with pytest.raises(ValueError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_singleton_importable():
    from app.config import settings
    assert isinstance(settings, Settings)
