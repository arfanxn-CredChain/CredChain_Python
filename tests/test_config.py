import pytest

from app.config import Settings


def test_default_values():
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.fastapi_port == 8081
    assert s.log_level == "info"
    assert s.log_output == "stdout"
    assert s.model_dir == "/models"
    assert s.easyocr_langs == ["id", "en"]
    assert s.ocr_max_image_pixels == 2_000_000
    assert s.cors_allow_origins == ["*"]


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("FASTAPI_PORT", "9090")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("EASYOCR_LANGS", "en,fr,de")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.fastapi_port == 9090
    assert s.log_level == "debug"
    assert s.easyocr_langs == ["en", "fr", "de"]


def test_invalid_port_rejected(monkeypatch):
    monkeypatch.setenv("FASTAPI_PORT", "not_a_number")
    with pytest.raises(ValueError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_singleton_importable():
    from app.config import settings
    assert isinstance(settings, Settings)


def test_settings_has_no_llm_attributes():
    from app.config import settings
    assert not hasattr(settings, "llm_max_new_tokens")
    assert not hasattr(settings, "llm_device")
    assert not hasattr(settings, "llm_timeout_seconds")
    assert not hasattr(settings, "llm_model_name")
    assert not hasattr(settings, "llm_model_file")
    assert not hasattr(settings, "embedding_model_name")
