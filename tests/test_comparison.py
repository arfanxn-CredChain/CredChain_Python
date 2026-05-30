from app import comparison


def test_verdict_for_tampered_high_score():
    assert comparison.verdict_for(1.0) == "TAMPERED"
    assert comparison.verdict_for(0.95) == "TAMPERED"


def test_verdict_for_suspicious_band():
    assert comparison.verdict_for(0.94) == "SUSPICIOUS"
    assert comparison.verdict_for(0.80) == "SUSPICIOUS"
    assert comparison.verdict_for(0.75) == "SUSPICIOUS"


def test_verdict_for_low_similarity_band():
    assert comparison.verdict_for(0.74) == "LOW_SIMILARITY"
    assert comparison.verdict_for(0.50) == "LOW_SIMILARITY"
    assert comparison.verdict_for(0.40) == "LOW_SIMILARITY"


def test_verdict_for_not_similar_band():
    assert comparison.verdict_for(0.39) == "NOT_SIMILAR"
    assert comparison.verdict_for(0.0) == "NOT_SIMILAR"


def test_verdict_for_negative_clamps_to_not_similar():
    assert comparison.verdict_for(-0.5) == "NOT_SIMILAR"


def test_format_percent():
    assert comparison.format_percent(0.91) == "91.0%"
    assert comparison.format_percent(0.50) == "50.0%"
    assert comparison.format_percent(1.0) == "100.0%"
    assert comparison.format_percent(0.0) == "0.0%"


def test_compare_fields_exact_match():
    stored = {"name": "John Doe", "year": "2024"}
    uploaded = {"name": "John Doe", "year": "2024"}
    out = comparison.compare_fields(stored, uploaded)
    assert out["name"].match is True
    assert out["name"].stored == "John Doe"
    assert out["name"].uploaded == "John Doe"
    assert out["year"].match is True


def test_compare_fields_fuzzy_key_matching():
    stored = {"date_of_birth": "1990-01-01"}
    uploaded = {"birth_date": "1990-01-01"}
    out = comparison.compare_fields(stored, uploaded)
    assert "date_of_birth" in out
    assert out["date_of_birth"].match is True
    assert out["date_of_birth"].uploaded == "1990-01-01"


def test_compare_fields_value_mismatch():
    stored = {"name": "John Doe"}
    uploaded = {"name": "Jane Smith"}
    out = comparison.compare_fields(stored, uploaded)
    assert out["name"].match is False
    assert out["name"].stored == "John Doe"
    assert out["name"].uploaded == "Jane Smith"


def test_compare_fields_value_within_threshold_matches():
    stored = {"name": "John Doe"}
    uploaded = {"name": "John  Doe"}
    out = comparison.compare_fields(stored, uploaded)
    assert out["name"].match is True


def test_compare_fields_no_uploaded_match_returns_empty_uploaded():
    stored = {"name": "John Doe"}
    uploaded = {"completely_unrelated_field_xyz": "anything"}
    out = comparison.compare_fields(stored, uploaded)
    assert "name" in out
    assert out["name"].uploaded == ""
    assert out["name"].match is False


def test_compare_fields_uploaded_key_matched_at_most_once():
    stored = {"name1": "Alice", "name2": "Alice"}
    uploaded = {"name": "Alice"}
    out = comparison.compare_fields(stored, uploaded)
    matched = [k for k, v in out.items() if v.uploaded == "Alice"]
    assert len(matched) == 1


def test_compare_fields_empty_stored_returns_empty():
    out = comparison.compare_fields({}, {"k": "v"})
    assert out == {}


def test_compare_fields_empty_uploaded_returns_unmatched_stored():
    out = comparison.compare_fields({"name": "X"}, {})
    assert out["name"].match is False
    assert out["name"].uploaded == ""


def test_thresholds_are_module_constants():
    assert comparison.KEY_MATCH_THRESHOLD == 80
    assert comparison.VALUE_MATCH_THRESHOLD == 85
    assert comparison.VERDICT_TAMPERED_MIN == 0.95
    assert comparison.VERDICT_SUSPICIOUS_MIN == 0.75
    assert comparison.VERDICT_LOW_SIMILARITY_MIN == 0.40
