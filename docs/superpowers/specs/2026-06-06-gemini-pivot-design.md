# CredChain Python — Gemini Pivot Design

**Date:** 2026-06-06
**Status:** Approved

## Summary

Replace the fully offline OCR + embedding pipeline (EasyOCR, PyMuPDF, LaBSE, rapidfuzz) with Google Gemini for document extraction and EmbeddingGemma-300M for embeddings. This follows the notebook at `notebooks/credchain-python.ipynb`. Complete rewrite — no fallback to the old pipeline.

## Motivation

- Gemini provides higher-quality extraction than regex-based ID parsing and OCR
- EmbeddingGemma-300M is significantly smaller than LaBSE (~300M params vs ~1.8 GB)
- Docker image shrinks dramatically (~2 GB of baked models removed)
- The notebook has been validated and shows the desired pipeline

## Architecture

### New Source Modules

```
app/
  gemini.py          → Gemini client, Files API upload, prompt execution
  embeddings.py      → EmbeddingGemma via sentence-transformers (rewritten, same API)
  verdict.py         → Configurable thresholds mapping similarity → verdict label
  prompts.py         → Extraction/ID prompts as module-level constants
  main.py            → i18n middleware added; lifespan loads Gemini + EmbeddingGemma
  routes.py          → Rewired to new pipeline
  schemas.py         → Updated response shapes
  config.py          → New/removed env vars
  description.py     → Single-language via request.state.lang
  codes.py           → Unchanged
  errors.py          → Unchanged
  logger.py          → Unchanged
  i18n.py            → Unchanged
```

### Removed Modules

```
app/ocr.py           → Replaced by gemini.py
app/id_extractor.py  → Replaced by gemini.py (Gemini prompt)
app/comparison.py    → Replaced by verdict.py
models/              → No more offline models
custom_id_patterns.txt → No more regex extraction
```

### Endpoint Behavior

All endpoints use the `{code, message, data?, errors?}` envelope.

| Method | Path | Change |
|---|---|---|
| POST | `/extract` | Gemini Files API (upload → poll ACTIVE → prompt). Returns `{raw_text, ids, embeddings}` per file. Go backend stores all three on MongoDB. |
| POST | `/verify` | Direct Gemini upload (no Files API). Extracts text, embeddings via EmbeddingGemma, cosine similarity comparison, single-language description via i18n middleware. Returns `{similarity_score, similarity_percent, verdict, description}`. |
| POST | `/extract-ids` | Direct Gemini upload. ID-only prompt. Returns `{ids}` only (no raw_text). |
| GET | `/health` | Returns `{code, message}` envelope. Message: `"model loading"` during startup, `"healthy"` when ready. |

### i18n Middleware

Mirrors the Go backend pattern:

1. Middleware reads `Accept-Language` header
2. Resolves to `"en"` or `"id"` (default: `"id"`)
3. Stores on FastAPI request state: `request.state.lang`
4. `description.py` reads `request.state.lang` and renders single-language description
5. Applied globally to all routes

### Verdict Thresholds (Configurable)

| Verdict | Default | Env Var |
|---|---|---|
| `tampered` | ≥ 0.95 | `VERDICT_TAMPERED_THRESHOLD` |
| `suspicious` | ≥ 0.75 | `VERDICT_SUSPICIOUS_THRESHOLD` |
| `low_similarity` | < 0.75, ≥ 0.55 | `VERDICT_LOW_SIMILARITY_THRESHOLD` |
| `not_similar` | < 0.55 | — |

### Prompts

Stored in `app/prompts.py` as module-level constants for easy editing. Mirrors the notebook:
- `PROMPT_EXTRACT_DOCUMENT` — extracts raw_text + ids
- `PROMPT_EXTRACT_IDS` — extracts ids only

## Dependency Changes

### Removed
- `easyocr==1.7.2`
- `pymupdf==1.25.1`
- `torch==2.5.1`
- `rapidfuzz==3.10.1`

### Added
- `google-genai` — Gemini SDK
- `huggingface-hub` — HF token auth for EmbeddingGemma
- `numpy` — cosine similarity math

### Updated
- `sentence-transformers>=3.3.1` — for EmbeddingGemma-300M

### Kept
- `fastapi`, `uvicorn[standard]`, `python-multipart`, `pydantic`, `pydantic-settings`, `Pillow`
- Dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`
- Python: `>=3.11,<3.13`

## Env Vars

### New
| Var | Default | Required |
|---|---|---|
| `GEMINI_API_KEY` | — | Yes |
| `HF_TOKEN` | — | Yes |
| `EXTRACTION_MODEL` | `gemini-3.1-flash-lite` | No |
| `EMBEDDING_MODEL_ID` | `google/embeddinggemma-300M` | No |
| `RETRY_WAIT_SECONDS` | `60` | No |
| `VERDICT_TAMPERED_THRESHOLD` | `0.95` | No |
| `VERDICT_SUSPICIOUS_THRESHOLD` | `0.75` | No |
| `VERDICT_LOW_SIMILARITY_THRESHOLD` | `0.55` | No |

### Removed
- `MODEL_DIR`, `EASYOCR_LANGS`, `OCR_MAX_IMAGE_PIXELS`, `CUSTOM_ID_PATTERNS_FILE`, `OVERRIDE_BUILTIN_ID_PATTERNS`

### Kept
- `FASTAPI_PORT`, `LOG_LEVEL`, `LOG_OUTPUT`, `LOCALES_DIR`, `MAX_FILES_PER_REQUEST`, `CORS_ALLOW_ORIGINS`

## Docker

- Single-stage `python:3.11-slim` build (no more multi-stage model bake)
- Install deps via `pip`, copy `app/` + `locales/`
- Expose port 8081
- Healthcheck unchanged
- EmbeddingGemma downloaded at startup from HuggingFace (requires `HF_TOKEN`)
- Run `docker system prune -a --volumes` to clean stale credchain-python artifacts

## Cleanup

- Delete `models/` directory
- Delete `custom_id_patterns.txt`
- Delete `tests/fixtures/` (now stale — old EasyOCR pipeline fixtures)
- Delete `CredChain_Python_postman_collection.json` (will be regenerated)
- Delete `credchain_python.egg-info/`
- Delete root `__pycache__/`
- Run `docker system prune -a --volumes` for stale images/volumes

## Testing

- All tests rewritten for new modules
- Mock Gemini client (mock `google.genai.Client`)
- Mock EmbeddingGemma (mock `SentenceTransformer`)
- Keep same test framework: pytest + pytest-asyncio + httpx
- Test count will differ significantly (fewer modules = fewer test files)
- Same ruff + mypy config retained

## Response Codes

Unchanged — same `50xxxx` category. Add one new code for Gemini API failures: `CODE_AI_GEMINI_FAILED=500150`.

## Files Not Touched

- `locales/en.json`, `locales/id.json` — same description templates
- `app/codes.py` — add one code, keep rest
- `app/errors.py` — add one default message
- `app/logger.py` — unchanged
- `app/i18n.py` — unchanged
- `Makefile` — commands stay, paths may need minor tweaks
- `.gitignore` — unchanged
- `.dockerignore` — remove `models/` exclusion (directory no longer exists)
