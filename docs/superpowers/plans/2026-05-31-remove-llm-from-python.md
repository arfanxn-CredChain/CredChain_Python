# Remove LLM from CredChain_Python — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Qwen LLM (field extraction) from CredChain_Python, switch Docker to multi-stage build with baked-in models, and lowercase verdict strings.

**Architecture:** TDD-driven aggressive removal. Tests assert new wire format first; implementation deletes old code. Each task produces a focused, committable change. Order is bottom-up: codes → schemas → comparison/description → routes/main → Docker/build → docs.

**Tech Stack:** Python 3.11, FastAPI 0.115, pydantic 2.10, EasyOCR 1.7, sentence-transformers 3.3 (LaBSE), pytest 8.3, mypy 1.13, ruff 0.8, Docker multi-stage build.

**Spec:** `docs/superpowers/specs/2026-05-31-remove-llm-from-python-design.md`

**Working directory:** `CredChain_Python/` for all commands.

---

## Task 1: Setup branch / baseline verification

**Files:**
- None (verification only)

- [ ] **Step 1.1: Confirm clean working tree**

```bash
cd CredChain_Python
git status
```

Expected: clean working tree on `master` branch.

- [ ] **Step 1.2: Run baseline tests to confirm green starting point**

```bash
make lint && make typecheck && make test
```

Expected: all pass. If anything fails before changes, stop and fix root cause first.

- [ ] **Step 1.3: Verify spec is committed and accessible**

```bash
ls docs/superpowers/specs/2026-05-31-remove-llm-from-python-design.md
```

Expected: file exists.

---

## Task 2: Remove LLM-only response codes

**Files:**
- Modify: `app/codes.py`
- Modify: `app/errors.py`
- Modify: `tests/test_codes.py` (if it asserts these codes)
- Modify: `tests/test_errors.py` (if it asserts these messages)

- [ ] **Step 2.1: Write a failing test asserting LLM codes are removed**

Add to `tests/test_codes.py`:

```python
def test_no_llm_response_codes():
    from app import codes
    assert not hasattr(codes, "CODE_AI_EXTRACT_LLM_FAILED")
    assert not hasattr(codes, "CODE_AI_LLM_TIMEOUT")
    assert not hasattr(codes, "CODE_AI_VERIFY_LLM_FAILED")
```

- [ ] **Step 2.2: Run the test, confirm it fails**

```bash
pytest tests/test_codes.py::test_no_llm_response_codes -v
```

Expected: FAIL — attributes still exist.

- [ ] **Step 2.3: Remove the LLM codes from `app/codes.py`**

Delete these lines from `app/codes.py`:

```python
CODE_AI_EXTRACT_LLM_FAILED = 500150
CODE_AI_LLM_TIMEOUT = 500151
```

And:

```python
CODE_AI_VERIFY_LLM_FAILED = 500250
```

- [ ] **Step 2.4: Remove matching entries from `app/errors.py`**

Delete from `DEFAULT_MESSAGES` dict in `app/errors.py`:

```python
codes.CODE_AI_EXTRACT_LLM_FAILED: "LLM extraction failed",
codes.CODE_AI_LLM_TIMEOUT: "LLM inference timed out",
codes.CODE_AI_VERIFY_LLM_FAILED: "LLM description generation failed",
```

Also update the message for `CODE_AI_VERIFY_INVALID_INPUT` from `"Invalid stored_embeddings or stored_fields"` to `"Invalid stored_embeddings"`.

- [ ] **Step 2.5: Run the test, confirm it passes**

```bash
pytest tests/test_codes.py::test_no_llm_response_codes -v
```

Expected: PASS.

- [ ] **Step 2.6: Run full test suite to confirm nothing else broke yet**

```bash
make test
```

Expected: failures only in tests that reference the deleted codes (`test_llm.py`, `test_errors.py`, `test_routes.py` — addressed in later tasks). Note the failure count.

- [ ] **Step 2.7: Commit**

```bash
git add app/codes.py app/errors.py tests/test_codes.py
git commit -m "refactor: remove LLM-only response codes"
```

---

## Task 3: Lowercase verdict strings in `comparison.py`

**Files:**
- Modify: `app/comparison.py`
- Modify: `tests/test_comparison.py`

- [ ] **Step 3.1: Update `tests/test_comparison.py` to expect lowercase verdicts**

Replace existing `verdict_for` tests with:

```python
import pytest
from app.comparison import (
    VERDICT_LOW_SIMILARITY_MIN,
    VERDICT_SUSPICIOUS_MIN,
    VERDICT_TAMPERED_MIN,
    format_percent,
    verdict_for,
)


def test_verdict_for_returns_lowercase_tampered():
    assert verdict_for(0.95) == "tampered"
    assert verdict_for(0.99) == "tampered"


def test_verdict_for_returns_lowercase_suspicious():
    assert verdict_for(0.75) == "suspicious"
    assert verdict_for(0.94) == "suspicious"


def test_verdict_for_returns_lowercase_low_similarity():
    assert verdict_for(0.40) == "low_similarity"
    assert verdict_for(0.74) == "low_similarity"


def test_verdict_for_returns_lowercase_not_similar():
    assert verdict_for(0.0) == "not_similar"
    assert verdict_for(-1.0) == "not_similar"
    assert verdict_for(0.39) == "not_similar"


def test_format_percent_one_decimal():
    assert format_percent(0.5) == "50.0%"
    assert format_percent(0.123) == "12.3%"


def test_thresholds_are_constants():
    assert VERDICT_TAMPERED_MIN == 0.95
    assert VERDICT_SUSPICIOUS_MIN == 0.75
    assert VERDICT_LOW_SIMILARITY_MIN == 0.40
```

Drop any imports/tests for `compare_fields`, `_best_key_match`, `KEY_MATCH_THRESHOLD`, `VALUE_MATCH_THRESHOLD`.

- [ ] **Step 3.2: Run tests, confirm they fail**

```bash
pytest tests/test_comparison.py -v
```

Expected: FAIL — verdict still uppercase, `compare_fields` references break collection.

- [ ] **Step 3.3: Replace `app/comparison.py` with simplified version**

Full replacement:

```python
"""Verdict mapping for similarity-based document verification.

Verdict thresholds map a cosine similarity in [-1, 1] to a lowercase label.
Counter-intuitively, very high similarity (>=0.95) implies TAMPERED,
because authentic re-issued documents always have natural OCR variance.
"""

VERDICT_TAMPERED_MIN = 0.95
VERDICT_SUSPICIOUS_MIN = 0.75
VERDICT_LOW_SIMILARITY_MIN = 0.40


def verdict_for(similarity: float) -> str:
    """Map a cosine similarity in [-1, 1] to one of four lowercase verdicts.

    Negative values clamp to "not_similar". The 0.95+ band is "tampered"
    (suspected copy/paste); 0.75-0.94 is "suspicious"; 0.40-0.74 is
    "low_similarity"; below 0.40 is "not_similar".
    """
    if similarity >= VERDICT_TAMPERED_MIN:
        return "tampered"
    if similarity >= VERDICT_SUSPICIOUS_MIN:
        return "suspicious"
    if similarity >= VERDICT_LOW_SIMILARITY_MIN:
        return "low_similarity"
    return "not_similar"


def format_percent(similarity: float) -> str:
    """Format a 0-1 similarity as a one-decimal percent string."""
    return f"{similarity * 100:.1f}%"
```

- [ ] **Step 3.4: Run tests, confirm pass**

```bash
pytest tests/test_comparison.py -v
```

Expected: PASS.

- [ ] **Step 3.5: Commit**

```bash
git add app/comparison.py tests/test_comparison.py
git commit -m "refactor: lowercase verdict strings, drop field comparison logic"
```

---

## Task 4: Update schemas — drop LLM-related fields and types

**Files:**
- Modify: `app/schemas.py`
- Modify: `tests/test_schemas.py`

- [ ] **Step 4.1: Update `tests/test_schemas.py` to assert new shapes**

Replace existing schema tests with:

```python
import pytest
from pydantic import ValidationError

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
    item = VerifyMetadataItem(stored_embeddings=[0.1], stored_fields={"a": "b"})
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
```

- [ ] **Step 4.2: Run tests, confirm they fail**

```bash
pytest tests/test_schemas.py -v
```

Expected: FAIL — old fields still exist.

- [ ] **Step 4.3: Replace `app/schemas.py` with simplified version**

```python
"""Pydantic request/response models for every endpoint."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """Unified API response envelope. Mirrors Go's response.Response[T]."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    code: int
    message: str
    data: T | None = None
    errors: dict[str, list[str]] | None = None


class ExtractData(BaseModel):
    """Payload returned from POST /extract."""

    raw_text: str
    embeddings: list[float]


class VerifyDescription(BaseModel):
    """Bilingual natural-language summary of the verify result."""

    id: str
    en: str


class VerifyData(BaseModel):
    """Payload returned from POST /verify."""

    similarity_score: float
    similarity_percent: str
    verdict: str
    description: VerifyDescription


class VerifyMetadataItem(BaseModel):
    """Single item in the /verify metadata array.

    Pairs positionally with files[i] in multipart upload.
    """

    stored_embeddings: list[float]


class ExtractIdsData(BaseModel):
    """Payload returned from POST /extract-ids."""

    raw_text: str
    potential_ids: list[str]


class HealthData(BaseModel):
    """Payload returned from GET /health."""

    status: str
    models_loaded: bool
```

- [ ] **Step 4.4: Run tests, confirm they pass**

```bash
pytest tests/test_schemas.py -v
```

Expected: PASS.

- [ ] **Step 4.5: Commit**

```bash
git add app/schemas.py tests/test_schemas.py
git commit -m "refactor: drop LLM-related schema fields and types"
```

---

## Task 5: Update `description.py` — new signature

**Files:**
- Modify: `app/description.py`
- Modify: `tests/test_description.py`

- [ ] **Step 5.1: Update `tests/test_description.py`**

Replace with:

```python
from app.description import build_description


def test_build_description_returns_bilingual_dict():
    result = build_description("suspicious", "91.0%")
    assert "id" in result
    assert "en" in result
    assert isinstance(result["id"], str)
    assert isinstance(result["en"], str)
    assert "91.0%" in result["en"]


def test_build_description_handles_all_verdicts():
    for verdict in ("tampered", "suspicious", "low_similarity", "not_similar"):
        result = build_description(verdict, "50.0%")
        assert result["id"] and result["en"]


def test_build_description_does_not_import_field_comparison_entry():
    import app.description as module
    src = open(module.__file__).read()
    assert "FieldComparisonEntry" not in src
```

- [ ] **Step 5.2: Run tests, confirm they fail**

```bash
pytest tests/test_description.py -v
```

Expected: FAIL — old signature requires more params.

- [ ] **Step 5.3: Replace `app/description.py`**

```python
"""Build bilingual verify descriptions from locale templates."""

from app.i18n import localize

SUPPORTED_LANGS = ("id", "en")


def build_description(verdict: str, similarity_percent: str) -> dict[str, str]:
    """Render bilingual description for a verify result using locale templates.

    Returns {"id": "...", "en": "..."} — no LLM involved.
    """
    key = f"verdict.{verdict.lower()}"
    fmt = {"percent": similarity_percent}
    return {lang: localize(key, lang, **fmt) for lang in SUPPORTED_LANGS}
```

- [ ] **Step 5.4: Commit (tests still failing — locale templates haven't been updated yet, addressed in Task 6)**

```bash
git add app/description.py tests/test_description.py
git commit -m "refactor: simplify build_description signature"
```

---

## Task 6: Update locale templates

**Files:**
- Modify: `locales/en.json`
- Modify: `locales/id.json`
- Modify: `tests/test_i18n.py` (if it asserts old keys)

- [ ] **Step 6.1: Replace `locales/en.json`**

```json
{
  "verdict.tampered": "This document looks almost identical to the one we have on file ({percent} similarity), which usually means it has been duplicated or tampered with. We recommend a closer review before accepting it.",
  "verdict.suspicious": "This document is a strong match for the one we have on file ({percent} similarity), but a few details look off. A manual review is recommended before accepting it.",
  "verdict.low_similarity": "This document only loosely resembles the one we have on file ({percent} similarity). It may be a different version, an outdated copy, or an unrelated document.",
  "verdict.not_similar": "This document does not appear to match the one we have on file ({percent} similarity). It is most likely a different document entirely."
}
```

- [ ] **Step 6.2: Replace `locales/id.json`**

```json
{
  "verdict.tampered": "Dokumen ini terlihat hampir identik dengan dokumen yang kami miliki (kemiripan {percent}), yang biasanya berarti dokumen ini telah diduplikasi atau dimanipulasi. Sebaiknya lakukan peninjauan lebih lanjut sebelum dokumen diterima.",
  "verdict.suspicious": "Dokumen ini cukup mirip dengan dokumen yang kami miliki (kemiripan {percent}), namun ada beberapa detail yang terlihat berbeda. Sebaiknya dilakukan peninjauan manual sebelum dokumen diterima.",
  "verdict.low_similarity": "Dokumen ini hanya sedikit menyerupai dokumen yang kami miliki (kemiripan {percent}). Kemungkinan ini adalah versi yang berbeda, salinan lama, atau dokumen yang tidak terkait.",
  "verdict.not_similar": "Dokumen ini tampaknya tidak cocok dengan dokumen yang kami miliki (kemiripan {percent}). Kemungkinan besar ini adalah dokumen yang sepenuhnya berbeda."
}
```

- [ ] **Step 6.3: Update `tests/test_i18n.py`** — drop any assertions that reference removed placeholders (`matched`, `mismatched`, `match_count`, `total_count`). Keep only the simple template-loading and `localize()` happy-path tests. If the test file currently asserts those placeholders exist, replace those test bodies with assertions that only `{percent}` is required.

- [ ] **Step 6.4: Run description + i18n tests**

```bash
pytest tests/test_description.py tests/test_i18n.py -v
```

Expected: PASS.

- [ ] **Step 6.5: Commit**

```bash
git add locales/en.json locales/id.json tests/test_i18n.py
git commit -m "refactor: simplify verdict locale templates (no field comparison)"
```

---

## Task 7: Update routes — drop LLM calls from `/extract` and `/verify`

**Files:**
- Modify: `app/routes.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 7.1: Update `tests/test_routes.py`**

Replace the file with a version that:
- Removes `llm` param from `_build_app()`
- Removes `app.state.llm` and `app.state.llm_lock` setup
- Drops all `monkeypatch.setattr(routes.llm, ...)` lines
- Asserts new response shapes
- Adds new tests: `test_extract_no_extracted_fields_in_response`, `test_verify_returns_lowercase_verdict`, `test_verify_no_field_comparison_in_response`, `test_verify_metadata_no_stored_fields_required`

Full new file:

```python
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
```

- [ ] **Step 7.2: Run tests, confirm they fail**

```bash
pytest tests/test_routes.py -v
```

Expected: FAIL — routes still call LLM.


- [ ] **Step 7.3: Replace `app/routes.py`**

Full new file:

```python
"""FastAPI router defining all four endpoints.

POST endpoints accept multi-file uploads. Response shape:
  {code, message, data: list[T | None], errors: {"files.<i>": [...]}}

Per-file failures surface in `errors` (Laravel-style); successful items
appear in `data` at the matching index. Top-level `code` reflects overall
outcome (success if any file succeeded, else error).
"""

import asyncio
import json

import easyocr
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer

from app import codes, comparison, embeddings, id_extractor, logger, ocr, schemas
from app import description as desc_module
from app.config import settings
from app.errors import AppError

__all__ = [
    "ALLOWED_MIME_TYPES",
    "MAX_UPLOAD_BYTES",
    "comparison",
    "desc_module",
    "embeddings",
    "id_extractor",
    "ocr",
    "router",
    "schemas",
]

router = APIRouter()
log = logger.get_logger("routes")

ALLOWED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
})
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def validate_file(file: UploadFile) -> tuple[bytes, str]:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise AppError(
            codes.CODE_AI_VALIDATION,
            errors={"file": [f"Unsupported MIME type: {file.content_type}"]},
        )
    contents = file.file.read()
    if not contents:
        raise AppError(codes.CODE_AI_VALIDATION, errors={"file": ["File is empty"]})
    if len(contents) > MAX_UPLOAD_BYTES:
        raise AppError(
            codes.CODE_AI_VALIDATION,
            errors={"file": [f"File too large: {len(contents)} bytes > {MAX_UPLOAD_BYTES}"]},
        )
    file.file.seek(0)
    return contents, file.content_type


def parse_verify_metadata(
    metadata_raw: str, expected_len: int
) -> list[schemas.VerifyMetadataItem]:
    try:
        parsed = json.loads(metadata_raw)
    except json.JSONDecodeError as exc:
        raise AppError(
            codes.CODE_AI_VERIFY_INVALID_INPUT,
            errors={"metadata": [str(exc)]},
        ) from exc
    if not isinstance(parsed, list):
        raise AppError(
            codes.CODE_AI_VERIFY_INVALID_INPUT,
            errors={"metadata": ["Must be a JSON array"]},
        )
    if len(parsed) != expected_len:
        raise AppError(
            codes.CODE_AI_VERIFY_INVALID_INPUT,
            errors={"metadata": [
                f"Length mismatch: {len(parsed)} metadata entries vs {expected_len} files"
            ]},
        )
    items: list[schemas.VerifyMetadataItem] = []
    for i, raw in enumerate(parsed):
        try:
            items.append(schemas.VerifyMetadataItem(**raw))
        except Exception as exc:
            raise AppError(
                codes.CODE_AI_VERIFY_INVALID_INPUT,
                errors={f"metadata.{i}": [str(exc)]},
            ) from exc
    return items


def validate_files(files: list[UploadFile]) -> None:
    if not files:
        raise AppError(
            codes.CODE_AI_VALIDATION,
            errors={"files": ["At least one file is required"]},
        )
    if len(files) > settings.max_files_per_request:
        raise AppError(
            codes.CODE_AI_VALIDATION,
            errors={"files": [
                f"Too many files: {len(files)} > {settings.max_files_per_request}"
            ]},
        )


def get_easyocr(request: Request) -> easyocr.Reader:
    return request.app.state.easyocr_reader


def get_embedding_model(request: Request) -> SentenceTransformer:
    return request.app.state.embedding_model  # type: ignore[no-any-return]


@router.post(
    "/extract",
    response_model=schemas.Response[list[schemas.ExtractData | None]],
    summary="OCR + embeddings (batch)",
)
async def extract(
    files: list[UploadFile] = File(...),
    reader: easyocr.Reader = Depends(get_easyocr),
    embed_model: SentenceTransformer = Depends(get_embedding_model),
) -> schemas.Response[list[schemas.ExtractData | None]]:
    validate_files(files)
    data: list[schemas.ExtractData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0
    for i, file in enumerate(files):
        try:
            file_bytes, mime_type = validate_file(file)
            raw_text = await asyncio.to_thread(ocr.extract_text, reader, file_bytes, mime_type)
            embeddings_list = await asyncio.to_thread(embeddings.encode, embed_model, raw_text)
            data.append(schemas.ExtractData(
                raw_text=raw_text,
                embeddings=embeddings_list,
            ))
            success_count += 1
        except AppError as exc:
            data.append(None)
            errors[f"files.{i}"] = [exc.message]
        except Exception:
            data.append(None)
            log.exception(
                "unhandled per-file error",
                extra={"extra_fields": {"file_index": i, "filename": file.filename}},
            )
            errors[f"files.{i}"] = ["Internal error processing file"]
    code = (
        codes.CODE_AI_EXTRACT_SUCCESS
        if success_count > 0
        else codes.CODE_AI_EXTRACT_OCR_FAILED
    )
    message = (
        "Document(s) extracted successfully"
        if success_count == len(files)
        else f"{success_count}/{len(files)} files extracted"
    )
    return schemas.Response(code=code, message=message, data=data, errors=errors or None)


@router.post(
    "/verify",
    response_model=schemas.Response[list[schemas.VerifyData | None]],
    summary="Batch similarity verification against stored embeddings",
)
async def verify(
    files: list[UploadFile] = File(...),
    metadata: str = Form(...),
    reader: easyocr.Reader = Depends(get_easyocr),
    embed_model: SentenceTransformer = Depends(get_embedding_model),
) -> schemas.Response[list[schemas.VerifyData | None]]:
    validate_files(files)
    items = parse_verify_metadata(metadata, expected_len=len(files))
    data: list[schemas.VerifyData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0
    for i, (file, item) in enumerate(zip(files, items, strict=True)):
        try:
            file_bytes, mime_type = validate_file(file)
            raw_text = await asyncio.to_thread(ocr.extract_text, reader, file_bytes, mime_type)
            embeddings_list = await asyncio.to_thread(embeddings.encode, embed_model, raw_text)
            similarity = embeddings.cosine_similarity(embeddings_list, item.stored_embeddings)
            verdict = comparison.verdict_for(similarity)
            sim_percent = comparison.format_percent(similarity)
            desc = desc_module.build_description(verdict, sim_percent)
            data.append(schemas.VerifyData(
                similarity_score=similarity,
                similarity_percent=sim_percent,
                verdict=verdict,
                description=schemas.VerifyDescription(id=desc["id"], en=desc["en"]),
            ))
            success_count += 1
        except AppError as exc:
            data.append(None)
            errors[f"files.{i}"] = [exc.message]
        except Exception:
            data.append(None)
            log.exception(
                "unhandled per-file error",
                extra={"extra_fields": {"file_index": i, "filename": file.filename}},
            )
            errors[f"files.{i}"] = ["Internal error processing file"]
    code = (
        codes.CODE_AI_VERIFY_SUCCESS
        if success_count > 0
        else codes.CODE_AI_VERIFY_OCR_FAILED
    )
    message = (
        "Verification(s) completed"
        if success_count == len(files)
        else f"{success_count}/{len(files)} files verified"
    )
    return schemas.Response(code=code, message=message, data=data, errors=errors or None)


@router.post(
    "/extract-ids",
    response_model=schemas.Response[list[schemas.ExtractIdsData | None]],
    summary="Batch extract potential IDs from documents (regex-only)",
)
async def extract_ids(
    files: list[UploadFile] = File(...),
    reader: easyocr.Reader = Depends(get_easyocr),
) -> schemas.Response[list[schemas.ExtractIdsData | None]]:
    validate_files(files)
    data: list[schemas.ExtractIdsData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0
    for i, file in enumerate(files):
        try:
            file_bytes, mime_type = validate_file(file)
            raw_text = await asyncio.to_thread(ocr.extract_text, reader, file_bytes, mime_type)
            potential_ids = id_extractor.extract_ids(raw_text)
            data.append(schemas.ExtractIdsData(
                raw_text=raw_text,
                potential_ids=potential_ids,
            ))
            success_count += 1
        except AppError as exc:
            data.append(None)
            errors[f"files.{i}"] = [exc.message]
        except Exception:
            data.append(None)
            log.exception(
                "unhandled per-file error",
                extra={"extra_fields": {"file_index": i, "filename": file.filename}},
            )
            errors[f"files.{i}"] = ["Internal error processing file"]
    code = (
        codes.CODE_AI_EXTRACT_IDS_SUCCESS
        if success_count > 0
        else codes.CODE_AI_EXTRACT_IDS_OCR_FAILED
    )
    message = (
        "Potential IDs extracted"
        if success_count == len(files)
        else f"{success_count}/{len(files)} files processed"
    )
    return schemas.Response(code=code, message=message, data=data, errors=errors or None)


@router.get("/health", summary="Liveness + model readiness check")
async def health(request: Request) -> JSONResponse:
    models_loaded = getattr(request.app.state, "models_loaded", False)
    code = codes.CODE_AI_HEALTH_SUCCESS if models_loaded else codes.CODE_AI_HEALTH_NOT_READY
    http_status = 200 if models_loaded else 503
    data = schemas.HealthData(
        status="ok" if models_loaded else "starting",
        models_loaded=models_loaded,
    )
    body = schemas.Response(
        code=code,
        message="Service is healthy" if models_loaded else "Models not yet loaded",
        data=data,
    ).model_dump(exclude_none=True)
    return JSONResponse(status_code=http_status, content=body)
```

- [ ] **Step 7.4: Run route tests, confirm they pass**

```bash
pytest tests/test_routes.py -v
```

Expected: PASS.

- [ ] **Step 7.5: Commit**

```bash
git add app/routes.py tests/test_routes.py
git commit -m "refactor: drop LLM calls from /extract and /verify"
```

---

## Task 8: Update `app/main.py` — drop Qwen lifespan loading

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 8.1: Update `tests/test_main.py`**

Drop any assertions that reference `app.state.llm`, `app.state.llm_lock`. Add new assertions that confirm only `easyocr_reader` and `embedding_model` are loaded:

```python
def test_lifespan_loads_only_two_models(monkeypatch):
    # Replace existing lifespan-loading test with the same pattern but
    # assert app.state has easyocr_reader and embedding_model, and does
    # NOT have llm or llm_lock.
    pass
```

(Adjust this stub to match the existing test style in `test_main.py`.)

- [ ] **Step 8.2: Run, confirm failure**

```bash
pytest tests/test_main.py -v
```

Expected: FAIL.

- [ ] **Step 8.3: Edit `app/main.py` lifespan function**

Remove these imports/lines:

```python
import asyncio
from llama_cpp import Llama
```

Remove from lifespan:

```python
app.state.llm = Llama(
    model_path=f"{settings.model_dir}/qwen/{settings.llm_model_file}",
    n_ctx=2048,
    n_threads=8,
    chat_format="chatml",
    verbose=False,
)
app.state.llm_lock = asyncio.Lock()
```

Replace `gpu=(settings.llm_device != "cpu")` with `gpu=False` in the `easyocr.Reader(...)` call.

Replace `device=settings.llm_device` with `device="cpu"` in the `SentenceTransformer(...)` call.

Final lifespan should look like:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load EasyOCR + LaBSE once at startup."""
    log.info(
        "loading models",
        extra={"extra_fields": {"phase": "startup", "model_dir": settings.model_dir}},
    )
    app.state.models_loaded = False

    import easyocr
    from sentence_transformers import SentenceTransformer

    app.state.easyocr_reader = easyocr.Reader(
        settings.easyocr_langs,
        gpu=False,
        model_storage_directory=f"{settings.model_dir}/easyocr",
    )
    app.state.embedding_model = SentenceTransformer(
        f"{settings.model_dir}/labse",
        device="cpu",
    )

    app.state.models_loaded = True
    log.info("models ready", extra={"extra_fields": {"phase": "ready"}})

    yield

    log.info("shutting down", extra={"extra_fields": {"phase": "shutdown"}})
```

Also remove `import asyncio` from the top-level imports — `asyncio.Lock()` was its only use.

- [ ] **Step 8.4: Run tests, confirm pass**

```bash
pytest tests/test_main.py -v
```

Expected: PASS.

- [ ] **Step 8.5: Commit**

```bash
git add app/main.py tests/test_main.py
git commit -m "refactor: drop Qwen loading from FastAPI lifespan"
```

---

## Task 9: Update `app/config.py` — drop LLM env vars

**Files:**
- Modify: `app/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 9.1: Update `tests/test_config.py`**

Drop assertions for `llm_max_new_tokens`, `llm_device`, `llm_timeout_seconds`, `llm_model_name`, `llm_model_file`. Add a guard:

```python
def test_settings_has_no_llm_attributes():
    from app.config import settings
    assert not hasattr(settings, "llm_max_new_tokens")
    assert not hasattr(settings, "llm_device")
    assert not hasattr(settings, "llm_timeout_seconds")
    assert not hasattr(settings, "llm_model_name")
    assert not hasattr(settings, "llm_model_file")
    assert not hasattr(settings, "embedding_model_name")
```

- [ ] **Step 9.2: Run, confirm failure**

```bash
pytest tests/test_config.py::test_settings_has_no_llm_attributes -v
```

Expected: FAIL.

- [ ] **Step 9.3: Edit `app/config.py`**

Delete these lines from the `Settings` class:

```python
llm_max_new_tokens: int = 512
llm_device: str = "cpu"
llm_timeout_seconds: int = 60
llm_model_name: str = "Qwen2.5-0.5B-Instruct"
llm_model_file: str = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
embedding_model_name: str = "LaBSE"
```

Delete the entire `validate_model_paths` validator method.

- [ ] **Step 9.4: Run tests**

```bash
pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 9.5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "refactor: drop LLM-related settings"
```

---

## Task 10: Delete `app/llm.py` and `tests/test_llm.py`

**Files:**
- Delete: `app/llm.py`
- Delete: `tests/test_llm.py`
- Modify: `tests/conftest.py`

- [ ] **Step 10.1: Remove `mock_llm` fixture from `tests/conftest.py`**

Delete the `mock_llm` fixture function (lines 28-40 of current `conftest.py`).

- [ ] **Step 10.2: Delete the LLM module and its test file**

```bash
rm app/llm.py tests/test_llm.py
```

- [ ] **Step 10.3: Run full test suite**

```bash
make test
```

Expected: PASS — all references to `llm.py` already removed in earlier tasks.

- [ ] **Step 10.4: Run lint and typecheck**

```bash
make lint && make typecheck
```

Expected: PASS.

- [ ] **Step 10.5: Commit**

```bash
git add -A app/llm.py tests/test_llm.py tests/conftest.py
git commit -m "refactor: delete app/llm.py and llm test module"
```

---

## Task 11: Update `pyproject.toml` — drop `llama-cpp-python`

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 11.1: Edit `pyproject.toml`**

Remove this line from the `dependencies` array:

```
"llama-cpp-python==0.3.4",
```

Update the `description` field from:

```
description = "CredChain AI service: OCR + embeddings + LLM extraction + similarity verdict"
```

to:

```
description = "CredChain AI service: OCR + embeddings + similarity verdict"
```

- [ ] **Step 11.2: Reinstall to verify dependency removal**

```bash
pip install -e ".[dev]"
```

Expected: succeeds without `llama-cpp-python`.

- [ ] **Step 11.3: Run full verification**

```bash
make lint && make typecheck && make test
```

Expected: all PASS.

- [ ] **Step 11.4: Commit**

```bash
git add pyproject.toml
git commit -m "build: drop llama-cpp-python dependency"
```

---

## Task 12: Update `Makefile` — drop `download-models` target

**Files:**
- Modify: `Makefile`

- [ ] **Step 12.1: Edit `Makefile`**

Remove from the `.PHONY` line:

```
download-models
```

Remove from the `help` target:

```
@echo "  make download-models - Download EasyOCR + LaBSE + Qwen2.5-1.5B-Instruct to host"
```

Delete the entire `download-models` target block (lines 38-47 of current Makefile):

```makefile
download-models:
	@echo ">>> Downloading EasyOCR (id+en) into ./models/easyocr..."
	.venv/bin/python -c "import easyocr; easyocr.Reader(['id', 'en'], model_storage_directory='./models/easyocr', download_enabled=True)"
	@echo ">>> Downloading LaBSE into ./models/labse..."
	.venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/LaBSE').save('./models/labse')"
	@echo ">>> Downloading Qwen2.5-0.5B-Instruct-Q4_K_M.gguf into ./models/qwen..."
	.venv/bin/huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct-GGUF \
		--local-dir ./models/qwen \
		--include "qwen2.5-0.5b-instruct-q4_k_m.gguf"
	@echo ">>> All models downloaded."
```

Update the `docker-up` help comment from:

```
@echo "  make docker-up       - docker compose up -d (requires download-models first)"
```

to:

```
@echo "  make docker-up       - docker compose up -d"
```

- [ ] **Step 12.2: Verify Makefile parses**

```bash
make help
```

Expected: prints help without errors; no `download-models` line shown.

- [ ] **Step 12.3: Commit**

```bash
git add Makefile
git commit -m "build: remove download-models target from Makefile"
```

---

## Task 13: Convert `Dockerfile` to multi-stage build

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 13.1: Replace `Dockerfile`**

```dockerfile
# Multi-stage build: models baked into image (no host volume mount).
#
# Stage 1 downloads EasyOCR + LaBSE weights (~1.95 GB) once.
# Stage 2 is the lean runtime image, copying weights from stage 1.

FROM python:3.11-slim AS model-downloader

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 wget build-essential && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir easyocr==1.7.2 sentence-transformers==3.3.1

WORKDIR /models

RUN python -c "import easyocr; easyocr.Reader(['id','en'], \
    model_storage_directory='/models/easyocr', download_enabled=True)"

RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/LaBSE').save('/models/labse')"


FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 wget && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 \
       --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir .

COPY --from=model-downloader /models /models
COPY app/ ./app/
COPY locales/ ./locales/

RUN chown -R app:app /app /models
USER app

ENV MODEL_DIR=/models
ENV PYTHONUNBUFFERED=1

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD wget -qO- http://localhost:8081/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "1"]
```

- [ ] **Step 13.2: Build the image to confirm it works**

```bash
docker build -t credchain-python:test .
```

Expected: builds successfully. First build takes 10-20 min (model downloads). Subsequent builds use cache.

- [ ] **Step 13.3: Commit**

```bash
git add Dockerfile
git commit -m "build: multi-stage Dockerfile with baked-in models"
```

---

## Task 14: Update `docker-compose.yml` — drop volume mount

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 14.1: Edit `docker-compose.yml`**

Delete this block:

```yaml
volumes:
  - ./models:/models:ro
```

- [ ] **Step 14.2: Run docker compose to verify**

```bash
docker compose config
```

Expected: valid config printed without `volumes:` block under `python-ai`.

- [ ] **Step 14.3: Commit**

```bash
git add docker-compose.yml
git commit -m "build: remove host model volume mount"
```

---

## Task 15: Update env files — drop LLM env vars

**Files:**
- Modify: `.env.example`
- Modify: `.env.docker`

- [ ] **Step 15.1: Read current `.env.example`**

```bash
cat .env.example
```

Note current contents.

- [ ] **Step 15.2: Edit `.env.example`**

Remove any lines matching:

```
LLM_MAX_NEW_TOKENS=
LLM_DEVICE=
LLM_TIMEOUT_SECONDS=
LLM_MODEL_NAME=
LLM_MODEL_FILE=
EMBEDDING_MODEL_NAME=
```

Keep all other env var entries.

- [ ] **Step 15.3: Edit `.env.docker`**

Apply the same removals to `.env.docker`.

- [ ] **Step 15.4: Verify the service still starts with the trimmed env**

```bash
make serve &
sleep 8
curl -s http://localhost:8081/health
kill %1
```

Expected: `/health` returns `{"code": 500900, ..., "data": {"status": "ok", "models_loaded": true}}`. (Requires models present locally for non-Docker run.)

If running this step locally is impractical (no models on host), skip this curl check — the Docker integration in Task 17 will catch any startup failure.

- [ ] **Step 15.5: Commit**

```bash
git add .env.example .env.docker
git commit -m "build: remove LLM env vars from sample env files"
```

---

## Task 16: Update `CredChain_Python/AGENTS.md`

**Files:**
- Modify: `AGENTS.md`

This task has multiple targeted edits per the spec §10. Each edit is small and surgical. Apply them in order.

- [ ] **Step 16.1: Update opening paragraph (line ~3)**

Replace:

```
Performs OCR, field extraction, semantic similarity, bilingual description generation, and regex-based ID extraction.
```

With:

```
Performs OCR, semantic similarity, bilingual description generation, and regex-based ID extraction.
```

- [ ] **Step 16.2: Update Critical Commands block**

Remove the line:

```
make download-models                                      # one-time: download EasyOCR + LaBSE + Qwen to host
```

- [ ] **Step 16.3: Update Environment Setup block**

Remove the `make download-models` line and its inline comment. Update the size total:

Replace `~2.5 GB total: EasyOCR (150 MB) + LaBSE (1.8 GB) + Qwen2.5-0.5B Q4_K_M (0.4 GB)` with `~1.95 GB total: EasyOCR (150 MB) + LaBSE (1.8 GB), baked into Docker image`.

Add a one-line note: `Models are baked into the Docker image via a multi-stage Dockerfile — no host download required.`

- [ ] **Step 16.4: Update Project Architecture file tree**

Remove these lines:

```
    llm.py              → llama-cpp-python wrapper: extract_fields only (with retry)
  models/qwen/          → gitignored, ~0.4 GB Qwen 0.5B Q4_K_M GGUF (mounted)
```

Update the architecture description from "14 source modules" to "13 source modules".

Update the comment lines for `models/easyocr/` and `models/labse/` from `(mounted)` to `(baked into image)`.

- [ ] **Step 16.5: Update Endpoints table**

Replace:

```
| POST | `/extract` | Batch OCR + LaBSE embedding + Qwen field extraction | 500100 |
```

With:

```
| POST | `/extract` | Batch OCR + LaBSE embedding | 500100 |
```

The `/verify` row stays the same (already accurate).

- [ ] **Step 16.6: Update Multi-file Response Envelope example**

Replace the JSON example to remove `extracted_fields`:

```json
{
  "code": 500100,
  "message": "Document(s) extracted successfully",
  "data": [
    { "raw_text": "...", "embeddings": [...] },
    null,
    { "raw_text": "...", "embeddings": [...] }
  ],
  "errors": {
    "files.1": ["OCR failed: corrupted PDF"]
  }
}
```

- [ ] **Step 16.7: Update `/verify` Metadata Blob example**

Replace:

```
metadata: [
  {"stored_embeddings": [0.1, ...], "stored_fields": {"name": "John"}},
  {"stored_embeddings": [0.3, ...], "stored_fields": {"name": "Jane"}}
]
```

With:

```
metadata: [
  {"stored_embeddings": [0.1, ...]},
  {"stored_embeddings": [0.3, ...]}
]
```

- [ ] **Step 16.8: Update Models Loaded Once via Lifespan section**

Change the opening sentence from `Three heavyweight models are loaded once...` to `Two heavyweight models are loaded once...`.

Delete the Qwen row from the model table:

```
| Qwen 2.5 0.5B Instruct (llama-cpp-python, Q4_K_M GGUF) | LLM-based field extraction | ~0.4 GB |
```

Replace `after all three load successfully` with `after both load successfully`.

Update the next paragraph: replace `Models are NOT baked into the Docker image — they are mounted from host` with `Models ARE baked into the Docker image via a multi-stage build`. Remove the `make download-models must run on the host` sentence.

- [ ] **Step 16.9: Update Single-Worker Concurrency section**

Replace `LaBSE and Qwen are CPU-bound and not thread-safe` with `LaBSE is CPU-bound`.

Replace `while one client invokes /extract, no other client can call any endpoint until that request completes` with `while one client invokes /extract or /verify, others wait on the LaBSE encoding step`.

- [ ] **Step 16.10: Lowercase the verdict labels in the table**

Find the verdict thresholds table:

```
| Verdict | Similarity Range |
|---|---|
| `TAMPERED` | ≥ 0.95 ... |
| `SUSPICIOUS` | ≥ 0.75 |
| `LOW_SIMILARITY` | ≥ 0.40 |
| `NOT_SIMILAR` | < 0.40 |
```

Replace with:

```
| Verdict | Similarity Range |
|---|---|
| `tampered` | ≥ 0.95 (suspiciously near-perfect — likely copy with minor edits) |
| `suspicious` | ≥ 0.75 |
| `low_similarity` | ≥ 0.40 |
| `not_similar` | < 0.40 |
```

Replace the "computed from BOTH embedding cosine similarity AND field similarity" sentence with: `The verdict is computed from embedding cosine similarity alone.`

- [ ] **Step 16.11: Remove the LLM Retry on JSON Parse Failure section**

Delete the entire `### LLM Retry on JSON Parse Failure` heading and its body paragraph.

- [ ] **Step 16.12: Update Configuration / Env Vars table**

Remove these rows:

```
| `LLM_MAX_NEW_TOKENS` | `512` | cap on Qwen generation length |
| `LLM_DEVICE` | `cpu` | `cpu` only currently |
| `LLM_MODEL_NAME` | `Qwen2.5-0.5B-Instruct` | display name in responses |
| `LLM_MODEL_FILE` | `qwen2.5-0.5b-instruct-q4_k_m.gguf` | actual GGUF file loaded |
| `EMBEDDING_MODEL_NAME` | `LaBSE` | display name in responses |
```

- [ ] **Step 16.13: Update Testing section**

Replace `~123 tests across 14 test files` with `~110 tests across 13 test files` (verify exact number after running tests in Task 17 and update accordingly).

Drop `mock_llm` from the conftest fixture list.

- [ ] **Step 16.14: Update Tech Stack table**

Remove these rows:

```
| LLM runtime | llama-cpp-python | 0.3.4 |
| LLM model | Qwen2.5-0.5B-Instruct Q4_K_M GGUF | ~0.4 GB |
```

- [ ] **Step 16.15: Add Cross-Repo Integration note**

Append to the Cross-Repo Integration section:

```
**Wire format change (2026-05-31):** `/extract` no longer returns `extracted_fields`. `/verify` no longer accepts `metadata[].stored_fields` and no longer returns `field_comparison` or `processing`. Verdict strings (`tampered`, `suspicious`, `low_similarity`, `not_similar`) are now lowercase. The Go backend must be updated separately to align — tracked in a Go-side spec.
```

- [ ] **Step 16.16: Field Comparison & Verdict Thresholds — section title rename**

Rename the `### Field Comparison & Verdict Thresholds` heading to `### Verdict Thresholds`. Drop the paragraph about `compare_fields` matching keys with `rapidfuzz.token_set_ratio` (now removed). Keep only the threshold table and the "verdict computed from embedding similarity" sentence.

- [ ] **Step 16.17: Locale-Based Description Generation — minor update**

In that section, update the example function signature reference to match the new `build_description(verdict, similarity_percent)` signature.

- [ ] **Step 16.18: Verify the file still renders**

```bash
head -50 AGENTS.md
```

Expected: clean Markdown, no obvious dangling fragments.

- [ ] **Step 16.19: Commit**

```bash
git add AGENTS.md
git commit -m "docs: update AGENTS.md to reflect LLM removal"
```

---

## Task 17: Final verification

**Files:**
- None (verification only)

- [ ] **Step 17.1: Run full test suite**

```bash
make test
```

Expected: all tests pass. Note the final test count and update AGENTS.md §Testing if it differs from the estimate.

- [ ] **Step 17.2: Run lint**

```bash
make lint
```

Expected: zero warnings.

- [ ] **Step 17.3: Run typecheck**

```bash
make typecheck
```

Expected: zero errors.

- [ ] **Step 17.4: Confirm `app/llm.py` is gone**

```bash
ls app/llm.py 2>&1
```

Expected: `No such file or directory`.

- [ ] **Step 17.5: Confirm `llama-cpp-python` not in installed packages**

```bash
pip show llama-cpp-python 2>&1
```

Expected: `WARNING: Package(s) not found: llama-cpp-python`.

- [ ] **Step 17.6: Confirm verdict strings are lowercase in comparison module**

```bash
python -c "from app.comparison import verdict_for; print(verdict_for(0.91))"
```

Expected: `suspicious`.

- [ ] **Step 17.7: Confirm `extracted_fields` not in ExtractData**

```bash
python -c "from app.schemas import ExtractData; print(ExtractData.model_fields.keys())"
```

Expected: `dict_keys(['raw_text', 'embeddings'])`.

- [ ] **Step 17.8: Confirm `field_comparison` not in VerifyData**

```bash
python -c "from app.schemas import VerifyData; print(VerifyData.model_fields.keys())"
```

Expected: `dict_keys(['similarity_score', 'similarity_percent', 'verdict', 'description'])`.

- [ ] **Step 17.9: Final commit — update test count in AGENTS.md if needed**

If the actual test count differs from the estimate in AGENTS.md, update it now:

```bash
# get actual count
make test 2>&1 | grep "passed"
# update AGENTS.md if needed, then:
git add AGENTS.md
git commit -m "docs: update test count in AGENTS.md"
```

---

## Task 18: Commit plan and spec docs

**Files:**
- `docs/superpowers/specs/2026-05-31-remove-llm-from-python-design.md`
- `docs/superpowers/plans/2026-05-31-remove-llm-from-python.md`

- [ ] **Step 18.1: Commit the spec and plan**

```bash
git add docs/superpowers/specs/2026-05-31-remove-llm-from-python-design.md
git add docs/superpowers/plans/2026-05-31-remove-llm-from-python.md
git commit -m "docs: add LLM removal spec and implementation plan"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Task 2 — codes.py + errors.py (spec §5.1)
- ✅ Task 3 — comparison.py lowercase verdicts (spec §7.1)
- ✅ Task 4 — schemas.py field removal (spec §5.1)
- ✅ Task 5 — description.py signature (spec §7.3)
- ✅ Task 6 — locale templates (spec §7.2)
- ✅ Task 7 — routes.py LLM removal (spec §4, §5.1)
- ✅ Task 8 — main.py lifespan (spec §5.1)
- ✅ Task 9 — config.py LLM settings (spec §5.3)
- ✅ Task 10 — delete llm.py + test_llm.py (spec §5.1, §5.4)
- ✅ Task 11 — pyproject.toml (spec §5.3)
- ✅ Task 12 — Makefile (spec §5.3)
- ✅ Task 13 — Dockerfile multi-stage (spec §6)
- ✅ Task 14 — docker-compose.yml volume (spec §6)
- ✅ Task 15 — env files (spec §5.3)
- ✅ Task 16 — AGENTS.md (spec §10)
- ✅ Task 17 — final verification (spec §2 success criteria)
- ✅ Task 18 — commit docs

**No placeholders found.**
**Type consistency verified** — `build_description(verdict, similarity_percent)` used consistently in Tasks 5, 6, 7.
**All commands include expected output.**
PLANEOF
