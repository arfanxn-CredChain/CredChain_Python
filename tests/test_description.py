"""Tests for app/description.py — single-language description rendering."""

from app.description import build_description


class TestBuildDescription:
    def test_english_tampered(self):
        result = build_description("tampered", "97.5%", "en")
        assert "97.5%" in result
        assert "almost identical" in result.lower()

    def test_english_suspicious(self):
        result = build_description("suspicious", "85.0%", "en")
        assert "85.0%" in result
        assert "strong match" in result.lower()

    def test_english_not_similar(self):
        result = build_description("not_similar", "10.0%", "en")
        assert "10.0%" in result
        assert "not appear to match" in result.lower()

    def test_indonesian_tampered(self):
        result = build_description("tampered", "97.5%", "id")
        assert "97.5%" in result
        assert "hampir identik" in result.lower()

    def test_defaults_to_id_when_unknown_lang(self):
        result = build_description("tampered", "97.5%", "fr")
        assert "97.5%" in result
        assert "hampir identik" in result.lower()
