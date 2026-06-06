def test_build_description_returns_bilingual_dict():
    from app.description import build_description
    result = build_description("suspicious", "91.0%")
    assert "id" in result
    assert "en" in result
    assert isinstance(result["id"], str)
    assert isinstance(result["en"], str)
    assert "91.0%" in result["en"]


def test_build_description_handles_all_verdicts():
    from app.description import build_description
    for verdict in ("tampered", "suspicious", "low_similarity", "not_similar"):
        result = build_description(verdict, "50.0%")
        assert result["id"]
        assert result["en"]


def test_build_description_does_not_import_field_comparison_entry():
    import app.description as module
    with open(module.__file__) as f:
        src = f.read()
    assert "FieldComparisonEntry" not in src
