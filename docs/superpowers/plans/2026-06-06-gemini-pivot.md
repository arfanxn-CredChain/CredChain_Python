# CredChain Python — Gemini Pivot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the offline OCR+embedding pipeline with Google Gemini for extraction and EmbeddingGemma-300M for embeddings, following the notebook at `notebooks/credchain-python.ipynb`.

**Architecture:** Complete rewrite of `app/`. Four endpoints preserved (`/extract`, `/verify`, `/extract-ids`, `/health`) but rewired to Gemini + EmbeddingGemma. i18n middleware added globally (mirrors Go backend pattern). Docker single-stage build, no baked models. All tests fully mocked.

**Tech Stack:** FastAPI 0.115.5, `google-genai`, `sentence-transformers` (EmbeddingGemma), `huggingface-hub`, `numpy`, Python >=3.11,<3.13.

**Spec:** `docs/superpowers/specs/2026-06-06-gemini-pivot-design.md`

---

### Task 1: Delete Old Code & Stale Artifacts

**Files:**
- Remove: `app/ocr.py`, `app/id_extractor.py`, `app/comparison.py`
- Remove: `tests/` (all files), `tests/fixtures/` (all files)
- Remove: `models/`, `custom_id_patterns.txt`, `CredChain_Python_postman_collection.json`
- Remove: `credchain_python.egg-info/`, root `__pycache__/`

- [ ] **Step 1: Delete old source modules**

```bash
rm /Users/arfanxn/Developments/credchain/CredChain_Python/app/ocr.py
rm /Users/arfanxn/Developments/credchain/CredChain_Python/app/id_extractor.py
rm /Users/arfanxn/Developments/credchain/CredChain_Python/app/comparison.py
```

- [ ] **Step 2: Delete old test files and fixtures**

```bash
rm -rf /Users/arfanxn/Developments/credchain/CredChain_Python/tests/
```

- [ ] **Step 3: Delete stale directories and files**

```bash
rm -rf /Users/arfanxn/Developments/credchain/CredChain_Python/models/
rm -f /Users/arfanxn/Developments/credchain/CredChain_Python/custom_id_patterns.txt
rm -f /Users/arfanxn/Developments/credchain/CredChain_Python/CredChain_Python_postman_collection.json
rm -rf /Users/arfanxn/Developments/credchain/CredChain_Python/credchain_python.egg-info/
rm -rf /Users/arfanxn/Developments/credchain/CredChain_Python/__pycache__/
```

- [ ] **Step 4: Recreate tests directory structure**

```bash
mkdir -p /Users/arfanxn/Developments/credchain/CredChain_Python/tests/
```

- [ ] **Step 5: Verify deletions**

```bash
ls /Users/arfanxn/Developments/credchain/CredChain_Python/app/
# Expected: __init__.py, codes.py, config.py, description.py, embeddings.py, errors.py, i18n.py, logger.py, main.py, routes.py, schemas.py
```

- [ ] **Step 6: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add -A && git commit -m "chore: remove old OCR/LaBSE pipeline modules and stale artifacts"
```

---

### Task 2: Update Dependencies & Env Files

**Files:**
- Modify: `pyproject.toml`
- Modify: `.env.example`, `.env`, `.env.docker`

- [ ] **Step 1: Update pyproject.toml dependencies**

Read `/Users/arfanxn/Developments/credchain/CredChain_Python/pyproject.toml`, replace the `[project]` section's `dependencies` and `optional-dependencies`:

```toml
[project]
name = "credchain-python"
version = "0.2.0"
description = "CredChain AI service: Gemini extraction + EmbeddingGemma embeddings"
requires-python = ">=3.11,<3.13"
dependencies = [
    "fastapi==0.115.5",
    "uvicorn[standard]==0.32.1",
    "python-multipart==0.0.17",
    "pydantic==2.10.3",
    "pydantic-settings==2.6.1",
    "sentence-transformers>=3.3.1",
    "google-genai",
    "huggingface-hub",
    "numpy",
    "Pillow==11.0.0",
]
[project.optional-dependencies]
dev = [
    "pytest==8.3.4",
    "pytest-asyncio==0.24.0",
    "httpx==0.28.1",
    "ruff==0.8.4",
    "mypy==1.13.0",
]
```

Keep all `[tool.*]` sections unchanged (ruff, mypy, pytest config).

- [ ] **Step 2: Write .env.example**

```bash
cat > /Users/arfanxn/Developments/credchain/CredChain_Python/.env.example << 'ENVEOF'
# ── Server ───────────────────────────────────────────────
FASTAPI_PORT=8081
LOG_LEVEL=info
LOG_OUTPUT=stdout

# ── Gemini AI ────────────────────────────────────────────
GEMINI_API_KEY=
EXTRACTION_MODEL=gemini-3.1-flash-lite
RETRY_WAIT_SECONDS=60

# ── Embeddings ───────────────────────────────────────────
HF_TOKEN=
EMBEDDING_MODEL_ID=google/embeddinggemma-300M

# ── Verdict Thresholds ───────────────────────────────────
VERDICT_TAMPERED_THRESHOLD=0.95
VERDICT_SUSPICIOUS_THRESHOLD=0.75
VERDICT_LOW_SIMILARITY_THRESHOLD=0.55

# ── i18n ─────────────────────────────────────────────────
LOCALES_DIR=./locales

# ── Limits ───────────────────────────────────────────────
MAX_FILES_PER_REQUEST=100

# ── CORS ─────────────────────────────────────────────────
CORS_ALLOW_ORIGINS=*
ENVEOF
```

- [ ] **Step 3: Write .env (from existing, keep real keys if present)**

First read the existing `.env` to preserve any real `GEMINI_API_KEY` or `HF_TOKEN` values, then overwrite with new template. The keys will need to be filled in.

```bash
cat > /Users/arfanxn/Developments/credchain/CredChain_Python/.env << 'ENVEOF'
# ── Server ───────────────────────────────────────────────
FASTAPI_PORT=8081
LOG_LEVEL=info
LOG_OUTPUT=stdout

# ── Gemini AI ────────────────────────────────────────────
GEMINI_API_KEY=<your-key>
EXTRACTION_MODEL=gemini-3.1-flash-lite
RETRY_WAIT_SECONDS=60

# ── Embeddings ───────────────────────────────────────────
HF_TOKEN=<your-hf-token>
EMBEDDING_MODEL_ID=google/embeddinggemma-300M

# ── Verdict Thresholds ───────────────────────────────────
VERDICT_TAMPERED_THRESHOLD=0.95
VERDICT_SUSPICIOUS_THRESHOLD=0.75
VERDICT_LOW_SIMILARITY_THRESHOLD=0.55

# ── i18n ─────────────────────────────────────────────────
LOCALES_DIR=./locales

# ── Limits ───────────────────────────────────────────────
MAX_FILES_PER_REQUEST=100

# ── CORS ─────────────────────────────────────────────────
CORS_ALLOW_ORIGINS=*
ENVEOF
```

- [ ] **Step 4: Write .env.docker**

```bash
cat > /Users/arfanxn/Developments/credchain/CredChain_Python/.env.docker << 'ENVEOF'
# ── Server ───────────────────────────────────────────────
FASTAPI_PORT=8081
LOG_LEVEL=info
LOG_OUTPUT=stdout

# ── Gemini AI ────────────────────────────────────────────
GEMINI_API_KEY=<your-key>
EXTRACTION_MODEL=gemini-3.1-flash-lite
RETRY_WAIT_SECONDS=60

# ── Embeddings ───────────────────────────────────────────
HF_TOKEN=<your-hf-token>
EMBEDDING_MODEL_ID=google/embeddinggemma-300M

# ── Verdict Thresholds ───────────────────────────────────
VERDICT_TAMPERED_THRESHOLD=0.95
VERDICT_SUSPICIOUS_THRESHOLD=0.75
VERDICT_LOW_SIMILARITY_THRESHOLD=0.55

# ── i18n ─────────────────────────────────────────────────
LOCALES_DIR=/app/locales

# ── Limits ───────────────────────────────────────────────
MAX_FILES_PER_REQUEST=100

# ── CORS ─────────────────────────────────────────────────
CORS_ALLOW_ORIGINS=*
ENVEOF
```

- [ ] **Step 5: Reinstall dependencies**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && pip install -e ".[dev]"
```

Run: Expected to install new deps without errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add pyproject.toml .env.example .env .env.docker && git commit -m "feat: update deps and env files for Gemini pivot"
```

---

### Task 3: Update Config, Codes & Errors

**Files:**
- Modify: `app/config.py`
- Modify: `app/codes.py`
- Modify: `app/errors.py`

- [ ] **Step 1: Rewrite app/config.py**

```python
"""Application settings loaded from environment / .env file."""

from typing import Any

from pydantic import Field, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_CSV_FIELDS: frozenset[str] = frozenset({"cors_allow_origins"})


def _split_csv_if_csv_field(
    field_name: str, value: Any
) -> tuple[Any, bool]:
    if field_name in _CSV_FIELDS and isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()], True
    return value, False


class _CsvEnvSettingsSource(EnvSettingsSource):
    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        parsed, was_csv = _split_csv_if_csv_field(field_name, value)
        if was_csv:
            return parsed
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class _CsvDotEnvSettingsSource(DotEnvSettingsSource):
    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,
        value_is_complex: bool,
    ) -> Any:
        parsed, was_csv = _split_csv_if_csv_field(field_name, value)
        if was_csv:
            return parsed
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    fastapi_port: int = 8081
    log_level: str = "info"
    log_output: str = "stdout"

    gemini_api_key: str = ""
    extraction_model: str = "gemini-3.1-flash-lite"
    retry_wait_seconds: int = 60

    hf_token: str = ""
    embedding_model_id: str = "google/embeddinggemma-300M"

    verdict_tampered_threshold: float = 0.95
    verdict_suspicious_threshold: float = 0.75
    verdict_low_similarity_threshold: float = 0.55

    locales_dir: str = "./locales"
    max_files_per_request: int = 100

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def split_csv(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            _CsvEnvSettingsSource(settings_cls),
            _CsvDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()
```

- [ ] **Step 2: Add CODE_AI_GEMINI_FAILED to app/codes.py**

Insert after the existing import/comment header, add one line after `CODE_AI_EXTRACT_OCR_FAILED`:

```python
CODE_AI_EXTRACT_OCR_FAILED = 500140
CODE_AI_GEMINI_FAILED = 500150
```

- [ ] **Step 3: Add default message to app/errors.py**

Add to the `DEFAULT_MESSAGES` dict after the extract OCR line:

```python
codes.CODE_AI_EXTRACT_OCR_FAILED: "OCR failed during extraction",
codes.CODE_AI_GEMINI_FAILED: "Gemini API request failed",
```

- [ ] **Step 4: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add app/config.py app/codes.py app/errors.py && git commit -m "feat: update config, add Gemini error code"
```

---

### Task 4: Create Core Modules — prompts.py + verdict.py (TDD)

**Files:**
- Create: `app/prompts.py`
- Create: `app/verdict.py`
- Create: `tests/test_verdict.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create tests/__init__.py**

```bash
touch /Users/arfanxn/Developments/credchain/CredChain_Python/tests/__init__.py
```

- [ ] **Step 2: Write the failing test for verdict.py**

Create `tests/test_verdict.py`:

```python
"""Tests for app/verdict.py — configurable verdict thresholds."""

from unittest.mock import patch

import pytest

from app.verdict import format_percent, verdict_for


class TestVerdictFor:
    def test_tampered_at_threshold(self):
        assert verdict_for(0.95) == "tampered"

    def test_tampered_above_threshold(self):
        assert verdict_for(0.98) == "tampered"

    def test_suspicious_at_threshold(self):
        assert verdict_for(0.75) == "suspicious"

    def test_suspicious_between_thresholds(self):
        assert verdict_for(0.85) == "suspicious"

    def test_low_similarity_at_threshold(self):
        assert verdict_for(0.55) == "low_similarity"

    def test_low_similarity_between_thresholds(self):
        assert verdict_for(0.60) == "low_similarity"

    def test_not_similar_below_threshold(self):
        assert verdict_for(0.30) == "not_similar"

    def test_not_similar_zero(self):
        assert verdict_for(0.0) == "not_similar"

    def test_negative_clamps_to_not_similar(self):
        assert verdict_for(-0.5) == "not_similar"

    def test_exactly_one_is_tampered(self):
        assert verdict_for(1.0) == "tampered"


class TestFormatPercent:
    def test_half_is_50(self):
        assert format_percent(0.5) == "50.0%"
        assert format_percent(0.5) == "50.0%"

    def test_near_perfect(self):
        assert format_percent(0.9876) == "98.8%"

    def test_zero(self):
        assert format_percent(0.0) == "0.0%"

    def test_one(self):
        assert format_percent(1.0) == "100.0%"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_verdict.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.verdict'`

- [ ] **Step 4: Create app/prompts.py**

```python
"""Extraction prompts for Gemini — module-level constants for easy editing.

Mirrors prompts from notebooks/credchain-python.ipynb.
"""

PROMPT_EXTRACT_DOCUMENT = (
    "Extract all textual content from this document. "
    "Omit headers, footers, boilerplate, and formatting artifacts. "
    "Also extract all document IDs, registration numbers, and identifier codes. "
    "For each ID, identify its type (e.g. passport, driver_license, tax_id, "
    "student_id, national_id, etc.). "
    "Return a JSON object with keys 'raw_text' (string) and 'ids' "
    "(array of {type: str, value: str} objects)."
)

PROMPT_EXTRACT_IDS = (
    "Extract all document IDs, registration numbers, and identifier codes "
    "from this document. "
    "For each ID, identify its type (e.g. passport, driver_license, tax_id, "
    "student_id, national_id, etc.). "
    "Return a JSON object with key 'ids' containing an array of "
    "{type: str, value: str} objects."
)
```

- [ ] **Step 5: Create app/verdict.py**

```python
"""Verdict mapping for similarity-based document verification.

Thresholds are configurable via env vars with sensible defaults.
Counter-intuitively, very high similarity (>=0.95) implies "tampered",
because authentic re-issued documents always have natural OCR variance.
"""

from app.config import settings


def verdict_for(similarity: float) -> str:
    if similarity >= settings.verdict_tampered_threshold:
        return "tampered"
    if similarity >= settings.verdict_suspicious_threshold:
        return "suspicious"
    if similarity >= settings.verdict_low_similarity_threshold:
        return "low_similarity"
    return "not_similar"


def format_percent(similarity: float) -> str:
    return f"{similarity * 100:.1f}%"
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_verdict.py -v
```

Expected: PASS — all 12 tests pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add app/prompts.py app/verdict.py tests/__init__.py tests/test_verdict.py && git commit -m "feat: add prompts, verdict module with tests"
```

---

### Task 5: Rewrite Embeddings Module (TDD)

**Files:**
- Modify: `app/embeddings.py`
- Create: `tests/test_embeddings.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_embeddings.py`:

```python
"""Tests for app/embeddings.py — EmbeddingGemma wrapper."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from app import codes
from app.embeddings import cosine_similarity, encode
from app.errors import AppError


class TestEncode:
    def test_encode_returns_float_list(self):
        model = MagicMock()
        fixed = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        model.encode.return_value = fixed
        result = encode(model, "hello world")
        assert result == [0.1, 0.2, 0.3]
        assert all(isinstance(x, float) for x in result)

    def test_encode_empty_text_raises(self):
        model = MagicMock()
        with pytest.raises(AppError) as exc:
            encode(model, "")
        assert exc.value.code == codes.CODE_AI_INTERNAL

    def test_encode_whitespace_only_raises(self):
        model = MagicMock()
        with pytest.raises(AppError) as exc:
            encode(model, "   ")
        assert exc.value.code == codes.CODE_AI_INTERNAL


class TestCosineSimilarity:
    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        assert abs(cosine_similarity(a, b) - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert abs(cosine_similarity(a, b) - 0.0) < 1e-6

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6

    def test_mismatched_lengths_raises(self):
        with pytest.raises(AppError) as exc:
            cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])
        assert exc.value.code == codes.CODE_AI_INTERNAL

    def test_zero_magnitude_returns_zero(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
        assert cosine_similarity([1.0, 2.0], [0.0, 0.0]) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_embeddings.py -v
```

Expected: FAIL — `encode` + `cosine_similarity` may still exist but use old LaBSE behavior. Tests will fail because of module API changes.

- [ ] **Step 3: Rewrite app/embeddings.py**

```python
"""EmbeddingGemma sentence-embedding wrapper + cosine similarity helper.

Uses google/embeddinggemma-300M via sentence-transformers.
"""

import math
from typing import TYPE_CHECKING

import numpy as np

from app import codes
from app.errors import AppError

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


def encode(model: "SentenceTransformer", text: str) -> list[float]:
    if not text or not text.strip():
        raise AppError(codes.CODE_AI_INTERNAL, message="Cannot encode empty text")
    max_seq = int(getattr(model, "max_seq_length", 512) or 512)
    word_count = len(text.split())
    if word_count > max_seq:
        import logging as _logging
        _logging.getLogger("embeddings").warning(
            "text may exceed max_seq_length and will be truncated: "
            "word_count=%d max_seq=%d", word_count, max_seq,
        )
    arr = model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
    if isinstance(arr, np.ndarray):
        return [float(x) for x in arr.tolist()]
    return [float(x) for x in arr]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise AppError(
            codes.CODE_AI_INTERNAL,
            message=f"Vector length mismatch: {len(a)} vs {len(b)}",
        )
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_embeddings.py -v
```

Expected: PASS — all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add app/embeddings.py tests/test_embeddings.py && git commit -m "feat: rewrite embeddings for EmbeddingGemma with tests"
```

---

### Task 6: Create Gemini Client Module (TDD)

**Files:**
- Create: `app/gemini.py`
- Create: `tests/test_gemini.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_gemini.py`:

```python
"""Tests for app/gemini.py — Gemini client for document extraction."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from app.errors import AppError
from app.gemini import GeminiClient


@pytest.fixture
def mock_genai_client():
    client = MagicMock()
    return client


class TestGeminiClient:
    def test_extract_document_returns_parsed_json(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")
        mock_response = MagicMock()
        mock_response.text = json.dumps({"raw_text": "Hello", "ids": []})
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client._extract_document(["test content"])

        assert result == {"raw_text": "Hello", "ids": []}

    def test_extract_document_empty_response_returns_empty_dict(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")
        mock_response = MagicMock()
        mock_response.text = None
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client._extract_document(["test content"])

        assert result == {}

    def test_extract_document_invalid_json_returns_empty_dict(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")
        mock_response = MagicMock()
        mock_response.text = "not json"
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client._extract_document(["test content"])

        assert result == {}

    def test_extract_document_with_retry_succeeds(self, mock_genai_client):
        client = GeminiClient(
            mock_genai_client, extraction_model="gemini-test", retry_wait_seconds=0
        )
        mock_response = MagicMock()
        mock_response.text = json.dumps({"raw_text": "OK"})
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client._extract_document_with_retry(["test content"])

        assert result == {"raw_text": "OK"}

    def test_extract_document_with_retry_handles_rate_limit(self, mock_genai_client):
        client = GeminiClient(
            mock_genai_client, extraction_model="gemini-test", retry_wait_seconds=0
        )
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("429 RESOURCE_EXHAUSTED")
            mock_response = MagicMock()
            mock_response.text = json.dumps({"raw_text": "retry ok"})
            return mock_response

        mock_genai_client.models.generate_content.side_effect = side_effect

        result = client._extract_document_with_retry(["test content"])

        assert result == {"raw_text": "retry ok"}
        assert call_count[0] == 3

    def test_extract_document_with_retry_exhausts(self, mock_genai_client):
        client = GeminiClient(
            mock_genai_client, extraction_model="gemini-test", retry_wait_seconds=0,
            max_retries=2,
        )
        mock_genai_client.models.generate_content.side_effect = Exception(
            "429 RESOURCE_EXHAUSTED"
        )

        with pytest.raises(RuntimeError, match="Max retries exceeded"):
            client._extract_document_with_retry(["test content"])

    def test_extract_direct_single_file(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {"raw_text": "doc text", "ids": [{"type": "passport", "value": "X123"}]}
        )
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.extract_direct(
            file_bytes=b"fake pdf bytes",
            mime_type="application/pdf",
            prompt="extract all",
        )

        assert result == {
            "raw_text": "doc text",
            "ids": [{"type": "passport", "value": "X123"}],
        }

    def test_extract_ids_direct(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {"ids": [{"type": "nik", "value": "1234567890123456"}]}
        )
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.extract_ids_direct(
            file_bytes=b"fake image", mime_type="image/jpeg", prompt="extract ids"
        )

        assert result == [{"type": "nik", "value": "1234567890123456"}]

    def test_extract_ids_direct_no_ids(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")
        mock_response = MagicMock()
        mock_response.text = json.dumps({"ids": []})
        mock_genai_client.models.generate_content.return_value = mock_response

        result = client.extract_ids_direct(
            file_bytes=b"fake image", mime_type="image/jpeg", prompt="extract ids"
        )

        assert result == []

    def test_upload_file(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")
        mock_file = MagicMock()
        mock_file.state = "PROCESSING"
        mock_genai_client.files.upload.return_value = mock_file

        result = client.upload_file(
            file_bytes=b"test", mime_type="application/pdf", display_name="doc.pdf"
        )

        assert result == mock_file
        mock_genai_client.files.upload.assert_called_once()

    def test_poll_until_active(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")
        mock_file = MagicMock()
        mock_file.name = "files/abc"
        mock_file_info = MagicMock()
        mock_file_info.state = "ACTIVE"
        mock_genai_client.files.get.return_value = mock_file_info

        result = client.poll_until_active(mock_file)

        assert result.state == "ACTIVE"

    def test_poll_until_active_fails(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")
        mock_file = MagicMock()
        mock_file.name = "files/abc"
        mock_file_info = MagicMock()
        mock_file_info.state = "FAILED"
        mock_genai_client.files.get.return_value = mock_file_info

        with pytest.raises(RuntimeError, match="failed processing"):
            client.poll_until_active(mock_file)

    def test_extract_with_files_api(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")

        mock_uploaded_file = MagicMock()
        mock_uploaded_file.name = "files/abc"
        mock_uploaded_file.uri = "https://example.com/file"
        mock_uploaded_file.mime_type = "application/pdf"
        mock_genai_client.files.upload.return_value = mock_uploaded_file

        mock_file_info = MagicMock()
        mock_file_info.state = "ACTIVE"
        mock_genai_client.files.get.return_value = mock_file_info

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {"raw_text": "extracted", "ids": []}
        )
        mock_genai_client.models.generate_content.return_value = mock_response

        file_dict = {"doc.pdf": b"fake pdf bytes"}
        results = client.extract_with_files_api(file_dict, "extract prompt")

        assert len(results) == 1
        name, raw_dict = results[0]
        assert name == "doc.pdf"
        assert raw_dict == {"raw_text": "extracted", "ids": []}

    def test_extract_with_files_api_handles_failure(self, mock_genai_client):
        client = GeminiClient(mock_genai_client, extraction_model="gemini-test")

        mock_uploaded_file = MagicMock()
        mock_uploaded_file.name = "files/abc"
        mock_uploaded_file.uri = "https://example.com/file"
        mock_uploaded_file.mime_type = "application/pdf"
        mock_genai_client.files.upload.return_value = mock_uploaded_file

        mock_file_info = MagicMock()
        mock_file_info.state = "ACTIVE"
        mock_genai_client.files.get.return_value = mock_file_info

        mock_genai_client.models.generate_content.side_effect = RuntimeError(
            "Max retries exceeded"
        )

        file_dict = {"doc.pdf": b"fake pdf bytes"}
        results = client.extract_with_files_api(file_dict, "extract prompt")

        assert len(results) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_gemini.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.gemini'`

- [ ] **Step 3: Create app/gemini.py**

```python
"""Gemini client for document extraction — Files API + direct upload.

Mirrors the pipeline from notebooks/credchain-python.ipynb:
  - /extract: Files API (upload → poll ACTIVE → prompt)
  - /verify, /extract-ids: direct upload (bytes in prompt)
"""

import io
import json
import time

from google import genai
from google.genai import types

MIME_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


class GeminiClient:
    def __init__(
        self,
        client: genai.Client,
        extraction_model: str,
        retry_wait_seconds: int = 60,
        max_retries: int = 3,
    ) -> None:
        self._client = client
        self._extraction_model = extraction_model
        self._retry_wait_seconds = retry_wait_seconds
        self._max_retries = max_retries

    # ── Direct upload (used by /verify and /extract-ids) ────

    def extract_direct(
        self, file_bytes: bytes, mime_type: str, prompt: str
    ) -> dict:
        contents = [
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            types.Part.from_text(text=prompt),
        ]
        return self._extract_document_with_retry(contents)

    def extract_ids_direct(
        self, file_bytes: bytes, mime_type: str, prompt: str
    ) -> list[dict[str, str]]:
        raw = self.extract_direct(file_bytes, mime_type, prompt)
        return raw.get("ids", [])

    # ── Files API (used by /extract for batch uploads) ──────

    def upload_file(
        self, file_bytes: bytes, mime_type: str, display_name: str,
    ) -> types.File:
        return self._client.files.upload(
            file=io.BytesIO(file_bytes),
            config=types.UploadFileConfig(
                mime_type=mime_type, display_name=display_name
            ),
        )

    def poll_until_active(self, file: types.File) -> types.File:
        while True:
            info = self._client.files.get(name=file.name)
            if info.state == "ACTIVE":
                return info
            if info.state == "FAILED":
                raise RuntimeError(f"File '{file.name}' failed processing")
            time.sleep(1)

    def extract_with_files_api(
        self, file_dict: dict[str, bytes], prompt: str,
    ) -> list[tuple[str, dict]]:
        print(f"Uploading {len(file_dict)} file(s)...")
        uploaded = []
        for name, data in file_dict.items():
            ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            mime = MIME_TYPES.get(ext, "application/octet-stream")
            f = self.upload_file(data, mime, name)
            print(f"  Uploaded '{name}' ({f.state})")
            info = self.poll_until_active(f)
            uploaded.append((name, info))

        results: list[tuple[str, dict]] = []
        for name, info in uploaded:
            print(f"  Extracting '{name}'...")
            contents = [
                types.Part.from_uri(file_uri=info.uri, mime_type=info.mime_type),
                types.Part.from_text(text=prompt),
            ]
            try:
                raw = self._extract_document_with_retry(contents)
                results.append((name, raw))
                print("    Done")
            except RuntimeError:
                print(f"    Failed after retries, skipping '{name}'")
            time.sleep(1)

        return results

    # ── Internal helpers ────────────────────────────────────

    def _extract_document(self, contents: list) -> dict:
        response = self._client.models.generate_content(
            model=self._extraction_model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        if not response.text:
            return {}
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            print(f"  Warning: Gemini returned non-JSON: {response.text[:200]}")
            return {}

    def _extract_document_with_retry(
        self, contents: list, max_retries: int | None = None,
    ) -> dict:
        max_retries = max_retries or self._max_retries
        for attempt in range(max_retries):
            try:
                return self._extract_document(contents)
            except Exception as e:
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    print(
                        f"  Rate limited — retrying in {self._retry_wait_seconds}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(self._retry_wait_seconds)
                else:
                    raise
        raise RuntimeError("Max retries exceeded")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_gemini.py -v
```

Expected: PASS — all 15 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add app/gemini.py tests/test_gemini.py && git commit -m "feat: add Gemini client with Files API and direct upload, with tests"
```

---

### Task 7: Update Schemas (TDD)

**Files:**
- Modify: `app/schemas.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_schemas.py`:

```python
"""Tests for app/schemas.py — Pydantic models."""

from app.schemas import (
    ExtractData,
    ExtractIdsData,
    HealthData,
    Response,
    VerifyData,
    VerifyMetadataItem,
)


class TestResponse:
    def test_minimal_success(self):
        r = Response(code=500100, message="ok")
        assert r.code == 500100
        assert r.message == "ok"
        assert r.data is None
        assert r.errors is None

    def test_with_data(self):
        r = Response(code=500100, message="ok", data={"key": "val"})
        assert r.data == {"key": "val"}

    def test_with_errors(self):
        r = Response(
            code=500040, message="fail", errors={"file": ["bad"]}
        )
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
        d = ExtractIdsData(
            ids=[{"type": "nik", "value": "1234567890123456"}]
        )
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_schemas.py -v
```

Expected: FAIL — schemas have old shapes (bilingual `VerifyDescription`, `ExtractIdsData.raw_text`, etc.)

- [ ] **Step 3: Rewrite app/schemas.py**

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
    """Payload returned from POST /extract.

    Gemini extracts raw_text and ids; EmbeddingGemma produces embeddings.
    All three stored on MongoDB by the Go backend.
    """

    raw_text: str
    ids: list[dict[str, str]]
    embeddings: list[float]


class VerifyData(BaseModel):
    """Payload returned from POST /verify.

    Description is a single-language string resolved via i18n middleware.
    """

    similarity_score: float
    similarity_percent: str
    verdict: str
    description: str


class VerifyMetadataItem(BaseModel):
    """Single item in the /verify metadata array.

    Pairs positionally with files[i] in multipart upload.
    """

    stored_embeddings: list[float]


class ExtractIdsData(BaseModel):
    """Payload returned from POST /extract-ids.

    ID-only extraction — no raw_text. Returns typed ID objects.
    """

    ids: list[dict[str, str]]


class HealthData(BaseModel):
    """Payload returned from GET /health."""

    message: str
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_schemas.py -v
```

Expected: PASS — all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add app/schemas.py tests/test_schemas.py && git commit -m "feat: update schemas for Gemini pipeline with tests"
```

---

### Task 8: Update Description Module & Conftest

**Files:**
- Modify: `app/description.py`
- Create: `tests/test_description.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create tests/conftest.py**

```python
"""Shared pytest fixtures for the CredChain_Python test suite."""

from unittest.mock import MagicMock

import numpy as np
import pytest


@pytest.fixture
def mock_embedding_model() -> MagicMock:
    """Mocked SentenceTransformer that returns a deterministic float vector."""
    model = MagicMock()
    fixed_vector = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    model.encode.return_value = fixed_vector
    return model


@pytest.fixture
def mock_gemini_client() -> MagicMock:
    """Mocked google.genai.Client."""
    client = MagicMock()
    return client
```

- [ ] **Step 2: Write test for description.py**

Create `tests/test_description.py`:

```python
"""Tests for app/description.py — single-language description rendering."""

from app.description import build_description


class TestBuildDescription:
    def test_english_tampered(self):
        result = build_description("tampered", "97.5%", "en")
        assert "97.5%" in result
        assert "almost identical" in result.lower()

    def test_english_suspicious(self):
        result = build_description("suspicious", "85.0%", "en")
        assert "85.0%" in result
        assert "strong match" in result.lower()

    def test_english_not_similar(self):
        result = build_description("not_similar", "10.0%", "en")
        assert "10.0%" in result
        assert "not appear to match" in result.lower()

    def test_indonesian_tampered(self):
        result = build_description("tampered", "97.5%", "id")
        assert "97.5%" in result
        assert "hampir identik" in result.lower()

    def test_defaults_to_id_when_unknown_lang(self):
        result = build_description("tampered", "97.5%", "fr")
        assert "97.5%" in result
        assert "hampir identik" in result.lower()
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_description.py -v
```

Expected: FAIL — `build_description` has old signature (no `lang` param)

- [ ] **Step 4: Rewrite app/description.py**

```python
"""Build single-language verify descriptions from locale templates.

Language is resolved via i18n middleware (Accept-Language header).
Defaults to Indonesian ("id") when language is not recognized.
"""

from app.i18n import localize

SUPPORTED_LANGS = ("id", "en")


def build_description(verdict: str, similarity_percent: str, lang: str) -> str:
    key = f"verdict.{verdict.lower()}"
    fmt = {"percent": similarity_percent}
    resolved_lang = lang if lang in SUPPORTED_LANGS else "id"
    return localize(key, resolved_lang, **fmt)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_description.py -v
```

Expected: PASS — all 5 tests pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add app/description.py tests/test_description.py tests/conftest.py && git commit -m "feat: single-language description with i18n support, with tests"
```

---

### Task 9: Rewrite Routes (TDD)

**Files:**
- Modify: `app/routes.py`
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_routes.py`:

```python
"""Tests for app/routes.py — endpoint integration tests."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def test_app():
    app = create_app()
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


@pytest.fixture
def sample_pdf_bytes():
    return b"%PDF-1.4 fake pdf content for testing"


class TestHealthEndpoint:
    def test_health_returns_envelope(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "code" in body
        assert "message" in body


class TestExtractEndpoint:
    def test_extract_validation_no_files(self, client):
        response = client.post("/extract")
        assert response.status_code == 400
        body = response.json()
        assert body["code"] == 500040

    def test_extract_success_single_file(self, client, sample_pdf_bytes):
        mock_gc = MagicMock()
        mock_gc.extract_with_files_api.return_value = [
            ("test.pdf", {"raw_text": "hello world", "ids": []})
        ]
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1, 0.2, 0.3]

        with (
            patch.object(client.app.state, "gemini_client", mock_gc),
            patch.object(client.app.state, "embedding_model", mock_model),
        ):
            response = client.post(
                "/extract",
                files=[("files", ("test.pdf", sample_pdf_bytes, "application/pdf"))],
            )

        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 500100
        assert len(body["data"]) == 1
        assert body["data"][0]["raw_text"] == "hello world"

    def test_extract_failure_per_file(self, client, sample_pdf_bytes):
        mock_gc = MagicMock()
        mock_gc.extract_with_files_api.return_value = []

        with patch.object(client.app.state, "gemini_client", mock_gc):
            response = client.post(
                "/extract",
                files=[("files", ("test.pdf", sample_pdf_bytes, "application/pdf"))],
            )

        assert response.status_code == 500
        body = response.json()
        assert body["code"] == 500150


class TestVerifyEndpoint:
    def test_verify_success(self, client, sample_pdf_bytes):
        mock_gc = MagicMock()
        mock_gc.extract_direct.return_value = {
            "raw_text": "doc text", "ids": []
        }
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1, 0.2, 0.3]

        metadata = json.dumps([{"stored_embeddings": [0.1, 0.2, 0.3]}])

        with (
            patch.object(client.app.state, "gemini_client", mock_gc),
            patch.object(client.app.state, "embedding_model", mock_model),
        ):
            response = client.post(
                "/verify",
                files=[("files", ("test.pdf", sample_pdf_bytes, "application/pdf"))],
                data={"metadata": metadata},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 500200
        assert len(body["data"]) == 1
        assert "similarity_score" in body["data"][0]
        assert "verdict" in body["data"][0]
        assert "description" in body["data"][0]

    def test_verify_metadata_mismatch(self, client, sample_pdf_bytes):
        metadata = json.dumps([{"stored_embeddings": [0.1]}, {"stored_embeddings": [0.2]}])

        response = client.post(
            "/verify",
            files=[("files", ("test.pdf", sample_pdf_bytes, "application/pdf"))],
            data={"metadata": metadata},
        )

        assert response.status_code == 400
        body = response.json()
        assert body["code"] == 500241


class TestExtractIdsEndpoint:
    def test_extract_ids_success(self, client, sample_pdf_bytes):
        mock_gc = MagicMock()
        mock_gc.extract_ids_direct.return_value = [
            {"type": "nik", "value": "1234567890123456"}
        ]

        with patch.object(client.app.state, "gemini_client", mock_gc):
            response = client.post(
                "/extract-ids",
                files=[("files", ("test.pdf", sample_pdf_bytes, "application/pdf"))],
            )

        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 500300
        assert body["data"][0]["ids"] == [
            {"type": "nik", "value": "1234567890123456"}
        ]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_routes.py -v
```

Expected: FAIL — routes.py references old `ocr`, `id_extractor`, `comparison` modules.

- [ ] **Step 3: Rewrite app/routes.py**

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

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from app import codes, embeddings, schemas
from app import description as desc_module
from app import verdict
from app.config import settings
from app.errors import AppError
from app.logger import get_logger
from app.prompts import PROMPT_EXTRACT_DOCUMENT, PROMPT_EXTRACT_IDS

router = APIRouter()
log = get_logger("routes")

ALLOWED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
})
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


# ── Helpers ──────────────────────────────────────────────

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
            errors={"file": [
                f"File too large: {len(contents)} bytes > {MAX_UPLOAD_BYTES}"
            ]},
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


def get_embedding_model(request: Request):
    return request.app.state.embedding_model


def get_gemini_client(request: Request):
    return request.app.state.gemini_client


def get_lang(request: Request) -> str:
    return getattr(request.state, "lang", "id")


# ── Endpoints ────────────────────────────────────────────

@router.post(
    "/extract",
    response_model=schemas.Response[list[schemas.ExtractData | None]],
    summary="Batch extract documents via Gemini Files API",
)
async def extract(
    files: list[UploadFile] = File(...),
    gemini_client=Depends(get_gemini_client),
    embed_model=Depends(get_embedding_model),
) -> schemas.Response[list[schemas.ExtractData | None]]:
    validate_files(files)
    data: list[schemas.ExtractData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0

    file_dict: dict[str, bytes] = {}
    file_map: dict[str, int] = {}
    for i, file in enumerate(files):
        try:
            contents, _ = validate_file(file)
            name = file.filename or f"file_{i}"
            file_dict[name] = contents
            file_map[name] = i
        except AppError as exc:
            data.append(None)
            errors[f"files.{i}"] = [exc.message]

    if file_dict:
        try:
            results = await asyncio.to_thread(
                gemini_client.extract_with_files_api, file_dict, PROMPT_EXTRACT_DOCUMENT
            )

            result_map: dict[int, tuple[str, dict]] = {}
            for name, raw in results:
                result_map[file_map[name]] = (name, raw)

            for i in range(len(files)):
                if data[i] is not None:
                    continue
                if i in result_map:
                    _, raw = result_map[i]
                    raw_text = raw.get("raw_text", "")
                    ids = raw.get("ids", [])
                    emb = await asyncio.to_thread(embeddings.encode, embed_model, raw_text)
                    data[i] = schemas.ExtractData(
                        raw_text=raw_text, ids=ids, embeddings=emb,
                    )
                    success_count += 1
                else:
                    if data[i] is None:
                        data[i] = None
                    errors.setdefault(f"files.{i}", []).append("Gemini extraction failed")

        except Exception:
            log.exception("Gemini extraction failed")
            for i in range(len(files)):
                if data[i] is None and f"files.{i}" not in errors:
                    data[i] = None
                    errors[f"files.{i}"] = ["Internal error processing file"]

    code = (
        codes.CODE_AI_EXTRACT_SUCCESS
        if success_count > 0
        else codes.CODE_AI_GEMINI_FAILED
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
    request: Request,
    files: list[UploadFile] = File(...),
    metadata: str = Form(...),
    gemini_client=Depends(get_gemini_client),
    embed_model=Depends(get_embedding_model),
) -> schemas.Response[list[schemas.VerifyData | None]]:
    validate_files(files)
    items = parse_verify_metadata(metadata, expected_len=len(files))
    lang = get_lang(request)
    data: list[schemas.VerifyData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0

    for i, (file, item) in enumerate(zip(files, items, strict=True)):
        try:
            file_bytes, mime_type = validate_file(file)
            raw = await asyncio.to_thread(
                gemini_client.extract_direct,
                file_bytes,
                mime_type,
                PROMPT_EXTRACT_DOCUMENT,
            )
            raw_text = raw.get("raw_text", "")
            if not raw_text:
                data.append(None)
                errors[f"files.{i}"] = ["No text extracted from document"]
                continue

            embeddings_list = await asyncio.to_thread(
                embeddings.encode, embed_model, raw_text
            )
            similarity = embeddings.cosine_similarity(
                embeddings_list, item.stored_embeddings
            )
            verdict_label = verdict.verdict_for(similarity)
            sim_percent = verdict.format_percent(similarity)
            desc = desc_module.build_description(verdict_label, sim_percent, lang)

            data.append(schemas.VerifyData(
                similarity_score=similarity,
                similarity_percent=sim_percent,
                verdict=verdict_label,
                description=desc,
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
    summary="Batch extract document IDs via Gemini",
)
async def extract_ids(
    files: list[UploadFile] = File(...),
    gemini_client=Depends(get_gemini_client),
) -> schemas.Response[list[schemas.ExtractIdsData | None]]:
    validate_files(files)
    data: list[schemas.ExtractIdsData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0

    for i, file in enumerate(files):
        try:
            file_bytes, mime_type = validate_file(file)
            ids = await asyncio.to_thread(
                gemini_client.extract_ids_direct,
                file_bytes,
                mime_type,
                PROMPT_EXTRACT_IDS,
            )
            data.append(schemas.ExtractIdsData(ids=ids))
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


@router.get("/health", summary="Liveness check")
async def health(request: Request) -> JSONResponse:
    models_loaded = getattr(request.app.state, "models_loaded", False)
    code = codes.CODE_AI_HEALTH_SUCCESS if models_loaded else codes.CODE_AI_HEALTH_NOT_READY
    http_status = 200 if models_loaded else 503
    message = "healthy" if models_loaded else "model loading"
    data = schemas.HealthData(message=message)
    body = schemas.Response(
        code=code,
        message=message,
        data=data,
    ).model_dump(exclude_none=True)
    return JSONResponse(status_code=http_status, content=body)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && python -m pytest tests/test_routes.py -v
```

Expected: PASS — all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add app/routes.py tests/test_routes.py && git commit -m "feat: rewrite routes for Gemini pipeline with tests"
```

---

### Task 10: Rewrite Main App (Lifespan + i18n Middleware)

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Rewrite app/main.py**

```python
"""CredChain Python AI Service — FastAPI application factory.

Single uvicorn worker, EmbeddingGemma loaded once via lifespan, Gemini
client initialized at startup. i18n middleware mirrors Go backend pattern.
Structured JSON logging, unified error envelope.
Reachable only inside the Docker backend network — never exposed publicly.
"""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from huggingface_hub import login as hf_login
from google import genai
from sentence_transformers import SentenceTransformer

from app import codes
from app.config import settings
from app.errors import AppError, http_status_for
from app.gemini import GeminiClient
from app.logger import get_logger
from app.routes import router

log = get_logger("main")

SUPPORTED_LANGS = {"id", "en"}
DEFAULT_LANG = "id"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load EmbeddingGemma + initialize Gemini client at startup."""
    log.info(
        "loading models",
        extra={"extra_fields": {"phase": "startup"}},
    )
    app.state.models_loaded = False

    hf_login(token=settings.hf_token)
    app.state.gemini_raw_client = genai.Client(api_key=settings.gemini_api_key)
    app.state.gemini_client = GeminiClient(
        app.state.gemini_raw_client,
        extraction_model=settings.extraction_model,
        retry_wait_seconds=settings.retry_wait_seconds,
    )

    log.info(
        "loading embedding model",
        extra={"extra_fields": {"model": settings.embedding_model_id}},
    )
    app.state.embedding_model = SentenceTransformer(
        settings.embedding_model_id, device="cpu"
    )

    app.state.models_loaded = True
    log.info("models ready", extra={"extra_fields": {"phase": "ready"}})

    yield

    log.info("shutting down", extra={"extra_fields": {"phase": "shutdown"}})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=http_status_for(exc.code),
            content={
                "code": exc.code,
                "message": exc.message,
                "errors": exc.errors,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"][1:]) or "body"
            field_errors.setdefault(loc, []).append(err["msg"])
        return JSONResponse(
            status_code=400,
            content={
                "code": codes.CODE_AI_VALIDATION,
                "message": "Validation failed",
                "errors": field_errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception(
            "unhandled error",
            extra={"extra_fields": {"path": request.url.path}},
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": codes.CODE_AI_INTERNAL,
                "message": "Internal server error",
            },
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title="CredChain Python AI Service",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def i18n_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        accept_lang = request.headers.get("Accept-Language", "").strip()
        lang = accept_lang.split(",")[0].split(";")[0].strip().lower()
        request.state.lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
        return await call_next(request)

    @app.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.request_id = str(uuid.uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code
        outcome = (
            "success" if 200 <= status_code < 300
            else "client_error" if 400 <= status_code < 500
            else "server_error"
        )
        log.info(
            "request completed",
            extra={"extra_fields": {
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": round(latency_ms, 2),
                "outcome": outcome,
            }},
        )
        return response

    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
```

- [ ] **Step 2: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add app/main.py && git commit -m "feat: rewrite main app with i18n middleware and Gemini lifespan"
```

---

### Task 11: Update Docker & Makefile

**Files:**
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `.dockerignore`
- Modify: `Makefile`

- [ ] **Step 1: Rewrite Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends wget && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -e "."

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD wget -qO- http://localhost:8081/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "1"]
```

- [ ] **Step 2: Update docker-compose.yml**

Read existing, replace with:

```yaml
services:
  python-ai:
    build:
      context: .
    image: arfanxn/credchain-python:latest
    container_name: credchain-python
    env_file:
      - .env.docker
    ports:
      - "127.0.0.1:8081:8081"
    networks:
      - backend

networks:
  backend:
    external: true
```

- [ ] **Step 3: Update .dockerignore**

Read existing, replace `models/` with nothing (remove that line). Keep all other entries unchanged:

```dockerignore
.venv/
venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.git/
.gitignore
.env
.env.local
.env.docker
tests/
*.log
logs/
.DS_Store
README.md
docs/
```

- [ ] **Step 4: Update Makefile**

Read existing. Update the `install` command to remove `--force-reinstall` (no longer needed for torch), and ensure `make serve` uses correct environment:

```makefile
install:
	pip install -e ".[dev]"

serve:
	uvicorn app.main:app --host 0.0.0.0 --port 8081 --workers 1

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8081 --workers 1 --reload

test:
	pytest tests/ -v

lint:
	ruff check

typecheck:
	mypy

format:
	ruff format .

docker-up:
	docker compose up -d

docker-up-build:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-ps:
	docker compose ps

docker-fresh:
	docker compose down && docker compose up -d --build && docker compose ps
```

- [ ] **Step 5: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add Dockerfile docker-compose.yml .dockerignore Makefile && git commit -m "feat: update Docker (single-stage), docker-compose, and Makefile for Gemini"
```

---

### Task 12: Update Postman Collection

**Files:**
- Modify: `CredChain_Python_postman_collection.json`

- [ ] **Step 1: Rewrite Postman collection**

Create a new Postman collection reflecting the updated endpoints:
- `POST /extract` — Gemini-based extraction, returns `{raw_text, ids, embeddings}`
- `POST /verify` — direct upload, returns `{similarity_score, similarity_percent, verdict, description}` (single-language)
- `POST /extract-ids` — ID extraction, returns `{ids}` only
- `GET /health` — envelope, returns `{code, message, data: {message}}`
- Add collection variables: `BASE_URL`, `GEMINI_API_KEY`, `HF_TOKEN`
- Add response examples for success + error paths for each endpoint

- [ ] **Step 2: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add CredChain_Python_postman_collection.json && git commit -m "docs: update Postman collection for Gemini endpoints"
```

---

### Task 13: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Rewrite AGENTS.md** to reflect the new tech stack, removed offline models, added Gemini deps, i18n middleware, and updated endpoint descriptions. Replace the "Tech Stack" table and "Project Architecture" sections. Update all references from EasyOCR/LaBSE/PyMuPDF to Gemini/EmbeddingGemma.

- [ ] **Step 2: Commit**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add AGENTS.md && git commit -m "docs: update AGENTS.md for Gemini pivot"
```

---

### Task 14: Final Cleanup & Verification

- [ ] **Step 1: Clean stale Docker artifacts**

```bash
docker system prune -a --volumes --force
```

- [ ] **Step 2: Run lint**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && make lint
```

Expected: PASS (may have minor issues to fix).

- [ ] **Step 3: Run typecheck**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && make typecheck
```

Expected: PASS or minor issues to resolve.

- [ ] **Step 4: Run all tests**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && source .venv/bin/activate && make test
```

Expected: PASS — all tests pass.

- [ ] **Step 5: Final commit (if any fixes needed)**

```bash
cd /Users/arfanxn/Developments/credchain/CredChain_Python && git add -A && git commit -m "chore: final fixes and cleanup"
```
