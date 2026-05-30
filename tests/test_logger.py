import json
import logging

from app.logger import JsonFormatter, get_logger


def test_json_formatter_emits_valid_json():
    fmt = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="x.py", lineno=1,
        msg="hello", args=(), exc_info=None,
    )
    out = fmt.format(record)
    parsed = json.loads(out)
    assert parsed["message"] == "hello"
    assert parsed["level"] == "info"
    assert parsed["logger"] == "test"
    assert "timestamp" in parsed


def test_json_formatter_includes_extra_fields():
    fmt = JsonFormatter()
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="x.py", lineno=1,
        msg="req done", args=(), exc_info=None,
    )
    record.extra_fields = {
        "request_id": "abc-123",
        "method": "POST",
        "path": "/extract",
        "latency_ms": 42,
        "status_code": 200,
        "outcome": "success",
    }
    parsed = json.loads(fmt.format(record))
    assert parsed["request_id"] == "abc-123"
    assert parsed["method"] == "POST"
    assert parsed["path"] == "/extract"
    assert parsed["latency_ms"] == 42
    assert parsed["status_code"] == 200
    assert parsed["outcome"] == "success"


def test_get_logger_returns_configured_logger():
    log = get_logger("test_logger_module")
    assert log.name == "test_logger_module"
    assert len(log.handlers) > 0
    assert isinstance(log.handlers[0].formatter, JsonFormatter)


def test_get_logger_is_idempotent():
    log1 = get_logger("idem_test")
    log2 = get_logger("idem_test")
    assert log1 is log2
    assert len(log1.handlers) == 1
