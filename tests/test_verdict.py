"""Tests for app/verdict.py — configurable verdict thresholds."""

from app.verdict import format_percent, verdict_for


class TestVerdictFor:
    def test_tampered_at_threshold(self):
        assert verdict_for(0.95) == "tampered"

    def test_tampered_above_threshold(self):
        assert verdict_for(0.98) == "tampered"

    def test_suspicious_at_threshold(self):
        assert verdict_for(0.75) == "suspicious"

    def test_suspicious_between_thresholds(self):
        assert verdict_for(0.85) == "suspicious"

    def test_low_similarity_at_threshold(self):
        assert verdict_for(0.55) == "low_similarity"

    def test_low_similarity_between_thresholds(self):
        assert verdict_for(0.60) == "low_similarity"

    def test_not_similar_below_threshold(self):
        assert verdict_for(0.30) == "not_similar"

    def test_not_similar_zero(self):
        assert verdict_for(0.0) == "not_similar"

    def test_negative_clamps_to_not_similar(self):
        assert verdict_for(-0.5) == "not_similar"

    def test_exactly_one_is_tampered(self):
        assert verdict_for(1.0) == "tampered"


class TestFormatPercent:
    def test_half_is_50(self):
        assert format_percent(0.5) == "50.0%"

    def test_near_perfect(self):
        assert format_percent(0.9876) == "98.8%"

    def test_zero(self):
        assert format_percent(0.0) == "0.0%"

    def test_one(self):
        assert format_percent(1.0) == "100.0%"
