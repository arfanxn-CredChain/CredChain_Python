import pytest
from pydantic import ValidationError

from app.schemas import (
    ExtractData,
    ExtractIdsData,
    FieldComparisonEntry,
    HealthData,
    Response,
    VerifyData,
    VerifyDescription,
    VerifyMetadataItem,
    VerifyProcessing,
)


def test_response_envelope_with_data():
    resp = Response[ExtractData](
        code=500100,
        message="ok",
        data=ExtractData(raw_text="x", embeddings=[0.1, 0.2], extracted_fields={"k": "v"}),
    )
    dumped = resp.model_dump(exclude_none=True)
    assert dumped["code"] == 500100
    assert dumped["message"] == "ok"
    assert dumped["data"]["raw_text"] == "x"
    assert "errors" not in dumped


def test_response_envelope_with_errors():
    resp = Response[ExtractData](
        code=500040, message="bad", errors={"file": ["required"]}
    )
    dumped = resp.model_dump(exclude_none=True)
    assert dumped["errors"] == {"file": ["required"]}
    assert "data" not in dumped


def test_extract_data_requires_all_fields():
    with pytest.raises(ValidationError):
        ExtractData(raw_text="x", embeddings=[])  # type: ignore[call-arg]


def test_verify_data_full_shape():
    v = VerifyData(
        similarity_score=0.91,
        similarity_percent="91.0%",
        verdict="SUSPICIOUS",
        description=VerifyDescription(id="ID summary", en="EN summary"),
        field_comparison={
            "name": FieldComparisonEntry(stored="A", uploaded="A", match=True),
        },
        processing=VerifyProcessing(ocr_char_count=100, model_used="LaBSE"),
    )
    assert v.similarity_score == 0.91
    assert v.field_comparison["name"].match is True


def test_verify_metadata_item_parses_lists_and_dicts():
    r = VerifyMetadataItem(stored_embeddings=[0.1, 0.2], stored_fields={"k": "v"})
    assert r.stored_embeddings == [0.1, 0.2]
    assert r.stored_fields == {"k": "v"}


def test_extract_ids_data_potential_ids_can_be_empty():
    d = ExtractIdsData(raw_text="x", potential_ids=[])
    assert d.potential_ids == []


def test_health_data_models_loaded_required():
    h = HealthData(status="ok", models_loaded=True)
    assert h.status == "ok"
    assert h.models_loaded is True
