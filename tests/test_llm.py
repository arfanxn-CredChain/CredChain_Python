from unittest.mock import MagicMock

import pytest

from app import llm
from app.errors import AppError


def _make_llm(response_text: str) -> MagicMock:
    mock = MagicMock()
    mock.create_chat_completion.return_value = {
        "choices": [{"message": {"content": response_text}}]
    }
    return mock


def test_extract_fields_returns_dict():
    m = _make_llm('{"name": "John", "year": "2024"}')
    assert llm.extract_fields(m, "some document text") == {"name": "John", "year": "2024"}


def test_extract_fields_retries_on_bad_json():
    m = MagicMock()
    m.create_chat_completion.side_effect = [
        {"choices": [{"message": {"content": "not valid json"}}]},
        {"choices": [{"message": {"content": '{"k": "v"}'}}]},
    ]
    assert llm.extract_fields(m, "text") == {"k": "v"}
    assert m.create_chat_completion.call_count == 2


def test_extract_fields_raises_after_two_failures():
    m = MagicMock()
    m.create_chat_completion.side_effect = [
        {"choices": [{"message": {"content": "bad json 1"}}]},
        {"choices": [{"message": {"content": "bad json 2"}}]},
    ]
    with pytest.raises(AppError) as exc:
        llm.extract_fields(m, "text")
    assert exc.value.code == 500150


def test_extract_fields_empty_text_returns_empty_dict():
    m = _make_llm("{}")
    assert llm.extract_fields(m, "") == {}


def test_prompt_constants_are_defined():
    assert hasattr(llm, "EXTRACT_PROMPT")
    assert len(llm.EXTRACT_PROMPT) > 50


def test_extract_fields_uses_json_mode():
    m = _make_llm("{}")
    llm.extract_fields(m, "text")
    call_kwargs = m.create_chat_completion.call_args.kwargs
    assert call_kwargs.get("response_format") == {"type": "json_object"}


def test_generate_uses_settings_max_tokens(monkeypatch):
    monkeypatch.setattr("app.llm.settings.llm_max_new_tokens", 128)
    m = _make_llm("{}")
    llm.extract_fields(m, "text")
    call = m.create_chat_completion.call_args
    assert call.kwargs["max_tokens"] == 128
