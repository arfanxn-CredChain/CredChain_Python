# CredChain Python (AI Service)

Python AI service called by the Go backend over HTTP. Performs OCR, field
extraction, semantic similarity, bilingual description generation. Runs
fully offline (no external API calls). Reachable only inside the Docker
backend network — **never expose to public internet** (no auth, no rate
limiting).

## Critical Commands

```bash
cd CredChain_Python
python3.11 -m venv .venv && source .venv/bin/activate  # one-time
make install                                            # install deps + dev extras
make download-models                                    # one-time: download EasyOCR + LaBSE + Qwen to host
make serve                                              # run uvicorn locally on :8081
make dev                                                # uvicorn with --reload
make test                                               # pytest tests/ -v (mocked, <10s)
make lint                                               # ruff check
make typecheck                                          # mypy
make format                                             # ruff format
make docker-up-build                                    # docker compose up -d --build
make docker-fresh                                       # down + up-build + ps
```

## Architecture

Flat layout under `app/` package. 14 source modules + `tests/`:

```
CredChain_Python/
  app/
    main.py           → FastAPI app + lifespan (loads 3 models) + middleware + error handlers
    routes.py         → 4 endpoints: /extract /verify /extract-ids /health
    schemas.py        → Pydantic Response[T] envelope + per-endpoint payloads
    config.py         → pydantic-settings .env loader, custom CSV env source
    codes.py          → 50xxxx response codes (System/Extract/Verify/Health)
    errors.py         → AppError + DEFAULT_MESSAGES + http_status_for
    logger.py         → structured JSON logger (mirrors Go's zap shape)
    ocr.py            → PyMuPDF + EasyOCR fallback, is_text_useful() check
    embeddings.py     → LaBSE encode + cosine_similarity helper
    llm.py            → llama-cpp-python wrapper: extract_fields only
    description.py    → bilingual description from locales/ templates
    i18n.py           → locale loader + localize(key, lang, **vars)
    comparison.py     → rapidfuzz token_set_ratio key matching + verdict mapping
    id_extractor.py   → regex-based ID extraction (built-in + custom patterns)
  tests/              → conftest.py + test files (~123 tests, fully mocked)
  models/qwen/        → gitignored, ~0.4 GB Qwen 0.5B Q4_K_M GGUF (mounted)
  models/easyocr/     → gitignored, ~150 MB EasyOCR weights (mounted)
  models/labse/       → gitignored, ~1.8 GB LaBSE weights (mounted)
  locales/            → tracked, JSON locale files (id, en) for description templates
  custom_id_patterns.txt → optional, gitignored, one regex per line
```

## Endpoints

All POST endpoints accept `files: list[UploadFile]` (multi-file batch).

| Method | Path | Purpose | Code |
|---|---|---|---|
| POST | /extract | Batch OCR + LaBSE embedding + Qwen field extraction | 500100 |
| POST | /verify | Batch cosine similarity + verdict + bilingual description | 500200 |
| POST | /extract-ids | Batch extract document/registration IDs (regex-only) | 500300 |
| GET | /health | Liveness + `models_loaded` flag | 500900 / 500950 |

## Multi-file response envelope

```json
{
  "code": 500100,
  "message": "Document(s) extracted successfully",
  "data": [
    { "raw_text": "...", "embeddings": [...], "extracted_fields": {...} },
    null,
    { "raw_text": "...", "embeddings": [...], "extracted_fields": {...} }
  ],
  "errors": {
    "files.1": ["OCR failed: corrupted PDF"]
  }
}
```

- `data` is always a list of length `len(files)`. Failed files = `null`.
- `errors` keys use `files.<index>` notation (mirrors Go's field error convention).
- Top-level `code` is success code when ≥1 file succeeded; error code when all failed.
- Hard limit: `MAX_FILES_PER_REQUEST=100`.

## /verify metadata blob (Option B)

`/verify` uses a single `metadata` JSON form field pairing each file with its stored data:

```
POST /verify
files: <file0.pdf>
files: <file1.pdf>
metadata: [
  {"stored_embeddings": [0.1, ...], "stored_fields": {"name": "John"}},
  {"stored_embeddings": [0.3, ...], "stored_fields": {"name": "Jane"}}
]
```

`len(files) == len(metadata)` is required; mismatch returns HTTP 400 code 500241.

## Custom ID patterns

`/extract-ids` uses regex-only extraction (no LLM). Built-in patterns cover
Indonesian IDs (NIK, NPWP, NIP, NIM) and generic codes (hyphenated, grouped
alnum, prefixed alnum, UUID, ULID).

Custom patterns are loaded from `CUSTOM_ID_PATTERNS_FILE` (default
`./custom_id_patterns.txt`). File format: one regex per line, `#` for comments.
Invalid regex → service refuses to start (fail fast).

`OVERRIDE_BUILTIN_ID_PATTERNS=true` skips built-in patterns entirely (custom-only mode).

Pattern ordering: custom first, then built-in (when enabled).

## Key patterns

- **Response envelope** matches Go's `{code, message, data, errors}` shape — code category 50 (AI), 6-digit AABBCC format.
- **Models loaded once** via FastAPI lifespan, accessed via `Depends()`. Single uvicorn worker.
- **Models NOT baked into Docker image** — mounted as read-only volume (`./models`). Image is ~2.5 GB.
- **`make download-models`** must run on host once before first `docker-up-build`.
- **Verdict thresholds** (named constants in `comparison.py`): TAMPERED ≥0.95, SUSPICIOUS ≥0.75, LOW_SIMILARITY ≥0.40, NOT_SIMILAR <0.40.
- **OCR fallback**: PyMuPDF first; if `is_text_useful()` returns False (<50 chars OR <80% printable), fall back to EasyOCR.
- **Field comparison**: rapidfuzz `token_set_ratio` for keys (≥80 threshold), `partial_ratio` for values (≥85 threshold).
- **LLM retry**: `extract_fields` retries once on JSON parse failure; raises `AppError(CODE_AI_EXTRACT_LLM_FAILED)` after second failure.
- **Locale descriptions**: `/verify` descriptions rendered from `locales/{id,en}.json` templates — no LLM call for descriptions.
- **Single-worker concurrency**: While one client invokes `/extract`, no other client can call any endpoint until that request completes. Operators should size connection pool accordingly.
- **Custom env CSV source**: `pydantic-settings 2.6.1` doesn't export `NoDecode`; `config.py` defines `_CsvEnvSettingsSource` + `_CsvDotEnvSettingsSource` for `easyocr_langs` and `cors_allow_origins`.

## Testing

- ~123 tests, all mocked. `pytest tests/ -v` runs in <15s.
- `tests/conftest.py` provides `mock_easyocr_reader`, `mock_embedding_model`, `mock_llm` fixtures.
- mypy strict mode for source; relaxed for tests.
- ruff: `B008` ignored in `app/routes.py` (FastAPI `Depends()`/`File()` defaults are idiomatic).

## Tech Stack (pinned in `pyproject.toml`)

- FastAPI 0.115.5, Pydantic 2.10.3, pydantic-settings 2.6.1
- PyMuPDF 1.25.1, EasyOCR 1.7.2 (id+en)
- sentence-transformers 3.3.1 (LaBSE)
- llama-cpp-python 0.3.4 (Qwen2.5-0.5B-Instruct Q4_K_M GGUF, ~0.4 GB)
- torch 2.5.1 CPU (required by easyocr + sentence-transformers)
- rapidfuzz 3.10.1
- Dev: pytest 8.3.4, ruff 0.8.4, mypy 1.13.0

## Env Vars

| Var | Default | Purpose |
|---|---|---|
| `FASTAPI_PORT` | 8081 | HTTP port |
| `LOG_LEVEL` | info | debug/info/warn/error |
| `LOG_OUTPUT` | stdout | stdout or file path |
| `MODEL_DIR` | /models | parent dir for model subdirs |
| `EASYOCR_LANGS` | id,en | comma-separated languages |
| `LLM_MAX_NEW_TOKENS` | 512 | cap on Qwen generation length |
| `LLM_DEVICE` | cpu | cpu only currently |
| `LLM_MODEL_NAME` | Qwen2.5-0.5B-Instruct | display name |
| `LLM_MODEL_FILE` | qwen2.5-0.5b-instruct-q4_k_m.gguf | actual GGUF file loaded |
| `EMBEDDING_MODEL_NAME` | LaBSE | display name |
| `LOCALES_DIR` | ./locales | parent dir for locale JSON files |
| `CUSTOM_ID_PATTERNS_FILE` | ./custom_id_patterns.txt | optional regex patterns file |
| `OVERRIDE_BUILTIN_ID_PATTERNS` | false | true = skip built-in ID patterns |
| `MAX_FILES_PER_REQUEST` | 100 | hard cap on multi-file upload |
| `CORS_ALLOW_ORIGINS` | * | comma-separated origins |

## Spec / Plan

- Spec: `docs/superpowers/specs/2026-05-30-credchain-python-regex-only-extract-ids-and-multifile.md`
- Plan: `docs/superpowers/plans/2026-05-30-credchain-python-regex-only-extract-ids-and-multifile.md`

