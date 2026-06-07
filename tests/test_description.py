"""Tests for app/description.py — bilingual description rendering."""

from app.description import build_description


class TestBuildDescription:
    def test_tampered_bilingual(self):
        result = build_description("tampered", "97.5%")
        assert isinstance(result, dict)
        assert "en" in result
        assert "id" in result
        assert "97.5%" in result["en"]
        assert "almost identical" in result["en"].lower()
        assert "97.5%" in result["id"]
        assert "hampir identik" in result["id"].lower()

    def test_suspicious_bilingual(self):
        result = build_description("suspicious", "85.0%")
        assert "85.0%" in result["en"]
        assert "strong match" in result["en"].lower()
        assert "85.0%" in result["id"]
        assert "mirip" in result["id"].lower()

    def test_not_similar_bilingual(self):
        result = build_description("not_similar", "10.0%")
        assert "10.0%" in result["en"]
        assert "not appear to match" in result["en"].lower()
        assert "10.0%" in result["id"]
        assert "tidak cocok" in result["id"].lower()

    def test_low_similarity_bilingual(self):
        result = build_description("low_similarity", "55.0%")
        assert "en" in result
        assert "id" in result
        assert "55.0%" in result["en"]
        assert "55.0%" in result["id"]
