import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import codes, routes
from app.errors import AppError, http_status_for


def _build_app(easyocr_reader=None, embedding_model=None) -> FastAPI:
    app = FastAPI()
    app.state.models_loaded = True
    app.state.easyocr_reader = easyocr_reader or MagicMock()
    app.state.embedding_model = embedding_model or MagicMock()
    app.include_router(routes.router)

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=http_status_for(exc.code),
            content={
                "code": exc.code,
                "message": exc.message,
                "errors": exc.errors,
            },
        )

    return app


def test_health_endpoint_returns_ok():
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == codes.CODE_AI_HEALTH_SUCCESS
    assert body["data"]["models_loaded"] is True


def test_extract_rejects_unsupported_mime(monkeypatch):
    app = _build_app()
    client = TestClient(app)
    monkeypatch.setattr(routes.ocr, "extract_text", lambda *a, **k: "raw text")
    resp = client.post(
        "/extract",
        files=[("files", ("doc.zip", BytesIO(b"PK\x03\x04"), "application/zip"))],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"][0] is None
    assert "files.0" in body["errors"]


def test_extract_empty_files_list_rejected():
    app = _build_app()
    client = TestClient(app)
    resp = client.post("/extract", files=[])
    assert resp.status_code in (400, 422)


def test_extract_happy_path_single_file(monkeypatch):
    app = _build_app()
    client = TestClient(app)
    monkeypatch.setattr(routes.ocr, "extract_text", lambda *a, **k: "raw text")
    monkeypatch.setattr(routes.embeddings, "encode", lambda *a, **k: [0.1] * 768)
    resp = client.post(
        "/extract",
        files=[("files", ("doc.pdf", BytesIO(b"%PDF-1.4 content"), "application/pdf"))],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == codes.CODE_AI_EXTRACT_SUCCESS
    assert body["data"][0]["raw_text"] == "raw text"
    assert body["data"][0]["embeddings"] == [0.1] * 768


def test_extract_no_extracted_fields_in_response(monkeypatch):
    app = _build_app()
    client = TestClient(app)
    monkeypatch.setattr(routes.ocr, "extract_text", lambda *a, **k: "raw text")
    monkeypatch.setattr(routes.embeddings, "encode", lambda *a, **k: [0.1] * 768)
    resp = client.post(
        "/extract",
        files=[("files", ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"))],
    )
    body = resp.json()
    assert "extracted_fields" not in body["data"][0]


def test_extract_multiple_files(monkeypatch):
    app = _build_app()
    client = TestClient(app)
    monkeypatch.setattr(routes.ocr, "extract_text", lambda *a, **k: "raw text")
    monkeypatch.setattr(routes.embeddings, "encode", lambda *a, **k: [0.1] * 768)
    resp = client.post(
        "/extract",
        files=[
            ("files", ("a.pdf", BytesIO(b"%PDF-1.4 a"), "application/pdf")),
            ("files", ("b.pdf", BytesIO(b"%PDF-1.4 b"), "application/pdf")),
        ],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2


def test_verify_happy_path_metadata(monkeypatch):
    app = _build_app()
    client = TestClient(app)
    monkeypatch.setattr(routes.ocr, "extract_text", lambda *a, **k: "uploaded text")
    monkeypatch.setattr(routes.embeddings, "encode", lambda *a, **k: [0.5] * 768)
    monkeypatch.setattr(routes.embeddings, "cosine_similarity", lambda *a, **k: 0.91)
    monkeypatch.setattr(
        routes.desc_module,
        "build_description",
        lambda *a, **k: {"id": "Ringkasan", "en": "EN summary"},
    )
    metadata = json.dumps([{"stored_embeddings": [0.5] * 768}])
    resp = client.post(
        "/verify",
        files=[("files", ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"))],
        data={"metadata": metadata},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == codes.CODE_AI_VERIFY_SUCCESS
    assert body["data"][0]["similarity_score"] == pytest.approx(0.91)


def test_verify_returns_lowercase_verdict(monkeypatch):
    app = _build_app()
    client = TestClient(app)
    monkeypatch.setattr(routes.ocr, "extract_text", lambda *a, **k: "uploaded text")
    monkeypatch.setattr(routes.embeddings, "encode", lambda *a, **k: [0.5] * 768)
    monkeypatch.setattr(routes.embeddings, "cosine_similarity", lambda *a, **k: 0.91)
    monkeypatch.setattr(
        routes.desc_module,
        "build_description",
        lambda *a, **k: {"id": "x", "en": "y"},
    )
    metadata = json.dumps([{"stored_embeddings": [0.5] * 768}])
    resp = client.post(
        "/verify",
        files=[("files", ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"))],
        data={"metadata": metadata},
    )
    body = resp.json()
    assert body["data"][0]["verdict"] == "suspicious"


def test_verify_no_field_comparison_in_response(monkeypatch):
    app = _build_app()
    client = TestClient(app)
    monkeypatch.setattr(routes.ocr, "extract_text", lambda *a, **k: "x")
    monkeypatch.setattr(routes.embeddings, "encode", lambda *a, **k: [0.5] * 768)
    monkeypatch.setattr(routes.embeddings, "cosine_similarity", lambda *a, **k: 0.5)
    monkeypatch.setattr(
        routes.desc_module,
        "build_description",
        lambda *a, **k: {"id": "x", "en": "y"},
    )
    metadata = json.dumps([{"stored_embeddings": [0.5] * 768}])
    resp = client.post(
        "/verify",
        files=[("files", ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"))],
        data={"metadata": metadata},
    )
    body = resp.json()
    assert "field_comparison" not in body["data"][0]
    assert "processing" not in body["data"][0]


def test_verify_metadata_no_stored_fields_required(monkeypatch):
    app = _build_app()
    client = TestClient(app)
    monkeypatch.setattr(routes.ocr, "extract_text", lambda *a, **k: "x")
    monkeypatch.setattr(routes.embeddings, "encode", lambda *a, **k: [0.5] * 768)
    monkeypatch.setattr(routes.embeddings, "cosine_similarity", lambda *a, **k: 0.5)
    monkeypatch.setattr(
        routes.desc_module,
        "build_description",
        lambda *a, **k: {"id": "x", "en": "y"},
    )
    metadata = json.dumps([{"stored_embeddings": [0.5] * 768}])
    resp = client.post(
        "/verify",
        files=[("files", ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"))],
        data={"metadata": metadata},
    )
    assert resp.status_code == 200


def test_verify_metadata_length_mismatch():
    app = _build_app()
    client = TestClient(app)
    metadata = json.dumps([
        {"stored_embeddings": [0.5] * 768},
        {"stored_embeddings": [0.5] * 768},
    ])
    resp = client.post(
        "/verify",
        files=[("files", ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"))],
        data={"metadata": metadata},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == codes.CODE_AI_VERIFY_INVALID_INPUT


def test_extract_ids_regex_only(monkeypatch):
    app = _build_app()
    client = TestClient(app)
    monkeypatch.setattr(routes.ocr, "extract_text", lambda *a, **k: "ID: UI-CS-2023-001234")
    resp = client.post(
        "/extract-ids",
        files=[("files", ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf"))],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == codes.CODE_AI_EXTRACT_IDS_SUCCESS
    assert "UI-CS-2023-001234" in body["data"][0]["potential_ids"]
