import pytest

from app import codes
from app.errors import DEFAULT_MESSAGES, AppError, http_status_for


def test_app_error_carries_code_message_errors():
    e = AppError(codes.CODE_AI_VALIDATION, message="bad input", errors={"file": ["required"]})
    assert e.code == codes.CODE_AI_VALIDATION
    assert e.message == "bad input"
    assert e.errors == {"file": ["required"]}


def test_app_error_uses_default_message_when_omitted():
    e = AppError(codes.CODE_AI_EXTRACT_OCR_FAILED)
    assert e.message == DEFAULT_MESSAGES[codes.CODE_AI_EXTRACT_OCR_FAILED]


def test_app_error_unknown_code_falls_back():
    e = AppError(999999)
    assert e.message == "error"


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        (codes.CODE_AI_SUCCESS, 200),
        (codes.CODE_AI_EXTRACT_SUCCESS, 200),
        (codes.CODE_AI_HEALTH_SUCCESS, 200),
        (codes.CODE_AI_VALIDATION, 400),
        (codes.CODE_AI_VERIFY_INVALID_INPUT, 400),
        (codes.CODE_AI_EXTRACT_OCR_FAILED, 400),
        (codes.CODE_AI_INTERNAL, 500),
        (codes.CODE_AI_HEALTH_NOT_READY, 500),
    ],
)
def test_http_status_for(code, expected_status):
    assert http_status_for(code) == expected_status


def test_default_messages_cover_every_code():
    code_values = {
        v for k, v in vars(codes).items() if k.startswith("CODE_") and isinstance(v, int)
    }
    for c in code_values:
        assert c in DEFAULT_MESSAGES, f"missing default message for code {c}"
