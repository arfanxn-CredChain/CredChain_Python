from app.comparison import (
    VERDICT_LOW_SIMILARITY_MIN,
    VERDICT_SUSPICIOUS_MIN,
    VERDICT_TAMPERED_MIN,
    format_percent,
    verdict_for,
)


def test_verdict_for_returns_lowercase_tampered():
    assert verdict_for(0.95) == "tampered"
    assert verdict_for(0.99) == "tampered"


def test_verdict_for_returns_lowercase_suspicious():
    assert verdict_for(0.75) == "suspicious"
    assert verdict_for(0.94) == "suspicious"


def test_verdict_for_returns_lowercase_low_similarity():
    assert verdict_for(0.40) == "low_similarity"
    assert verdict_for(0.74) == "low_similarity"


def test_verdict_for_returns_lowercase_not_similar():
    assert verdict_for(0.0) == "not_similar"
    assert verdict_for(-1.0) == "not_similar"
    assert verdict_for(0.39) == "not_similar"


def test_format_percent_one_decimal():
    assert format_percent(0.5) == "50.0%"
    assert format_percent(0.123) == "12.3%"


def test_thresholds_are_constants():
    assert VERDICT_TAMPERED_MIN == 0.95
    assert VERDICT_SUSPICIOUS_MIN == 0.75
    assert VERDICT_LOW_SIMILARITY_MIN == 0.40
