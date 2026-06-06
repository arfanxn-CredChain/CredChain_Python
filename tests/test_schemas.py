from app.schemas import (
    ExtractData,
    ExtractIdsData,
    HealthData,
    Response,
    VerifyData,
    VerifyDescription,
    VerifyMetadataItem,
)


def test_extract_data_only_has_raw_text_and_embeddings():
    data = ExtractData(raw_text="hello", embeddings=[0.1, 0.2])
    assert data.raw_text == "hello"
    assert data.embeddings == [0.1, 0.2]
    assert not hasattr(data, "extracted_fields")


def test_verify_data_no_field_comparison_no_processing():
    data = VerifyData(
        similarity_score=0.91,
        similarity_percent="91.0%",
        verdict="suspicious",
        description=VerifyDescription(id="ID desc", en="EN desc"),
    )
    assert data.verdict == "suspicious"
    assert not hasattr(data, "field_comparison")
    assert not hasattr(data, "processing")


def test_verify_metadata_item_only_has_stored_embeddings():
    item = VerifyMetadataItem(stored_embeddings=[0.1, 0.2])
    assert item.stored_embeddings == [0.1, 0.2]
    assert not hasattr(item, "stored_fields")


def test_verify_metadata_item_rejects_extra_fields_silently():
    item = VerifyMetadataItem(stored_embeddings=[0.1], stored_fields={"a": "b"})  # type: ignore[call-arg]
    assert item.stored_embeddings == [0.1]
    assert not hasattr(item, "stored_fields")


def test_field_comparison_entry_removed():
    from app import schemas
    assert not hasattr(schemas, "FieldComparisonEntry")


def test_verify_processing_removed():
    from app import schemas
    assert not hasattr(schemas, "VerifyProcessing")


def test_extract_ids_data_unchanged():
    data = ExtractIdsData(raw_text="hello 1234", potential_ids=["1234"])
    assert data.potential_ids == ["1234"]


def test_health_data_unchanged():
    data = HealthData(status="ok", models_loaded=True)
    assert data.models_loaded is True


def test_response_envelope_generic():
    resp = Response[ExtractIdsData](
        code=500300,
        message="ok",
        data=ExtractIdsData(raw_text="x", potential_ids=[]),
    )
    assert resp.code == 500300
