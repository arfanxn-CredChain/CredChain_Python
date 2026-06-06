from unittest.mock import patch

from fastapi.testclient import TestClient


def test_app_module_exposes_app():
    from app.main import app
    assert app is not None
    assert app.title == "CredChain Python AI Service"


def test_lifespan_loads_only_two_models(mock_easyocr_reader, mock_embedding_model):
    from app.main import create_app

    app = create_app()
    with patch("easyocr.Reader", return_value=mock_easyocr_reader), patch(
        "sentence_transformers.SentenceTransformer", return_value=mock_embedding_model
    ), TestClient(app):
            assert hasattr(app.state, "easyocr_reader")
            assert hasattr(app.state, "embedding_model")
            assert app.state.easyocr_reader is mock_easyocr_reader
            assert app.state.embedding_model is mock_embedding_model
            assert not hasattr(app.state, "llm")
            assert not hasattr(app.state, "llm_lock")
            assert app.state.models_loaded is True


def test_app_registers_routes():
    from app.main import app
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/extract" in paths
    assert "/verify" in paths
    assert "/extract-ids" in paths
    assert "/health" in paths


def test_app_error_handler_returns_envelope():
    from fastapi import FastAPI

    from app import codes
    from app.errors import AppError
    from app.main import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)

    @app.get("/raise")
    async def raise_app_error():
        raise AppError(codes.CODE_AI_VALIDATION, errors={"x": ["bad"]})

    client = TestClient(app)
    resp = client.get("/raise")
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == codes.CODE_AI_VALIDATION
    assert body["errors"] == {"x": ["bad"]}


def test_validation_handler_returns_envelope_on_pydantic_error():
    from fastapi import FastAPI
    from pydantic import BaseModel

    from app import codes
    from app.main import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)

    class Body(BaseModel):
        x: int

    @app.post("/echo")
    async def echo(b: Body):
        return {"x": b.x}

    client = TestClient(app)
    resp = client.post("/echo", json={"x": "not an int"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == codes.CODE_AI_VALIDATION
    assert "errors" in body
    assert body["errors"]


def test_unhandled_exception_returns_500_envelope():
    from fastapi import FastAPI

    from app import codes
    from app.main import register_error_handlers

    app = FastAPI()
    register_error_handlers(app)

    @app.get("/crash")
    async def crash():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/crash")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == codes.CODE_AI_INTERNAL
