from app.description import build_description
from app.schemas import FieldComparisonEntry


def _cmp(matched_keys: list[str], mismatched_keys: list[str]) -> dict[str, FieldComparisonEntry]:
    result = {}
    for k in matched_keys:
        result[k] = FieldComparisonEntry(stored="A", uploaded="A", match=True)
    for k in mismatched_keys:
        result[k] = FieldComparisonEntry(stored="A", uploaded="B", match=False)
    return result


def test_returns_id_and_en_keys():
    out = build_description("TAMPERED", 0.97, "97.0%", _cmp(["name"], ["dob"]))
    assert "id" in out
    assert "en" in out


def test_tampered_contains_percent():
    out = build_description("TAMPERED", 0.97, "97.0%", _cmp(["name"], []))
    assert "97.0%" in out["id"]
    assert "97.0%" in out["en"]


def test_matched_fields_appear_in_output():
    out = build_description("SUSPICIOUS", 0.85, "85.0%", _cmp(["name", "year"], ["dob"]))
    assert "name" in out["id"]
    assert "year" in out["id"]


def test_mismatched_fields_appear_in_output():
    out = build_description("LOW_SIMILARITY", 0.55, "55.0%", _cmp(["name"], ["dob", "gpa"]))
    assert "dob" in out["id"]
    assert "gpa" in out["id"]


def test_empty_comparison_renders_dash():
    out = build_description("NOT_SIMILAR", 0.10, "10.0%", {})
    assert out["id"]
    assert out["en"]


def test_match_count_correct():
    out = build_description("SUSPICIOUS", 0.80, "80.0%", _cmp(["a", "b"], ["c"]))
    assert "2" in out["id"]
    assert "3" in out["id"]


def test_all_verdicts_render():
    for verdict in ("TAMPERED", "SUSPICIOUS", "LOW_SIMILARITY", "NOT_SIMILAR"):
        out = build_description(verdict, 0.5, "50.0%", _cmp(["name"], ["dob"]))
        assert out["id"]
        assert out["en"]
