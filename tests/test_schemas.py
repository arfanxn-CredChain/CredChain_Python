"""Tests for app/schemas.py — Pydantic models."""

from typing import Any

from app.schemas import (
    ExtractData,
    ExtractIdsData,
    HealthData,
    Response,
    VerifyData,
    VerifyMetadataItem,
)


class TestResponse:
    def test_minimal_success(self) -> None:
        r: Response[Any] = Response(code=500100, message="ok")
        assert r.code == 500100
        assert r.message == "ok"
        assert r.data is None
        assert r.errors is None

    def test_with_data(self):
        r = Response(code=500100, message="ok", data={"key": "val"})
        assert r.data == {"key": "val"}

    def test_with_errors(self) -> None:
        r: Response[Any] = Response(code=500040, message="fail", errors={"file": ["bad"]})
        assert r.errors == {"file": ["bad"]}


class TestExtractData:
    def test_valid_data(self):
        d = ExtractData(
            raw_text="hello",
            ids=[{"type": "passport", "value": "X123"}],
            embeddings=[0.1, 0.2],
        )
        assert d.raw_text == "hello"
        assert d.ids == [{"type": "passport", "value": "X123"}]
        assert d.embeddings == [0.1, 0.2]

    def test_ids_can_be_empty(self):
        d = ExtractData(raw_text="hello", ids=[], embeddings=[0.1])
        assert d.ids == []


class TestVerifyData:
    def test_valid_data(self):
        d = VerifyData(
            similarity_score=0.95,
            similarity_percent="95.0%",
            verdict="tampered",
            description="This document looks almost identical...",
        )
        assert d.similarity_score == 0.95
        assert d.similarity_percent == "95.0%"
        assert d.verdict == "tampered"
        assert isinstance(d.description, str)


class TestExtractIdsData:
    def test_valid_data(self):
        d = ExtractIdsData(ids=[{"type": "nik", "value": "1234567890123456"}])
        assert len(d.ids) == 1
        assert d.ids[0]["type"] == "nik"

    def test_empty_ids(self):
        d = ExtractIdsData(ids=[])
        assert d.ids == []


class TestHealthData:
    def test_valid_data(self):
        d = HealthData(message="healthy")
        assert d.message == "healthy"


class TestVerifyMetadataItem:
    def test_valid(self):
        m = VerifyMetadataItem(stored_embeddings=[0.1, 0.2, 0.3])
        assert m.stored_embeddings == [0.1, 0.2, 0.3]
