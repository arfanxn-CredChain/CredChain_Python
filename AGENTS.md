# CredChain Python - Agent Instructions

Python AI service called by the Go backend over HTTP. Performs OCR, field extraction, semantic similarity, bilingual description generation, and regex-based ID extraction. Runs fully offline (no external API calls). Reachable only inside the Docker backend network — **never expose to public internet** (no auth, no rate limiting).

This file is the authoritative reference for AI assistants and engineers working in `CredChain_Python/`.

## Repo Position

Sibling to `CredChain_Golang/` (backend, sole HTTP caller), `CredChain_React/` (frontend), and `CredChain_Solidity/` (contracts).

- **Consumer:** the Go backend is the only intended caller. Requests flow `React → Go API → Python AI`. The frontend never talks to this service directly.
- **Locales:** `locales/{en,id}.json` are tracked and kept in sync with the corresponding files in `CredChain_Golang/locales/` and `CredChain_React/src/shared/i18n/`. React enforces sync via `npm run check-locales`.
- **Network isolation:** the service binds inside the Docker backend network only. There is no auth middleware, no rate limiter, no CORS protection beyond the configurable `CORS_ALLOW_ORIGINS` — exposing it publicly would allow arbitrary OCR/LLM execution against arbitrary input.

## Critical Commands

```bash
python3.11 -m venv .venv && source .venv/bin/activate    # one-time
make install                                              # install deps + dev extras
make download-models                                      # one-time: download EasyOCR + LaBSE + Qwen to host
make serve                                                # run uvicorn locally on :8081 (single worker)
make dev                                                  # uvicorn with --reload
make test                                                 # pytest tests/ -v (mocked, ~5s for 123 tests)
make lint                                                 # ruff check
make typecheck                                            # mypy (strict mode on source, relaxed on tests)
make format                                               # ruff format
make docker-up-build                                      # docker compose up -d --build
make docker-down                                          # docker compose down
make docker-fresh                                         # down + up-build + ps
```

No CI pipeline is configured.

## Environment Setup

Copy `.env.example` → `.env` (or `.env.docker` for Docker-internal hostnames). Required steps before first run:

```bash
python3.11 -m venv .venv && source .venv/bin/activate
make install
make download-models    # ~2.5 GB total: EasyOCR (150 MB) + LaBSE (1.8 GB) + Qwen2.5-0.5B Q4_K_M (0.4 GB)
make serve              # binds :8081 by default
```

Models are downloaded to host (`./models/{easyocr,labse,qwen}/`) and mounted into the Docker container at runtime — **not baked into the image**. This keeps the image ~2.5 GB smaller and lets you swap models without rebuilding.

No external API keys required — the service runs fully offline.

## Project Architecture

Flat layout under `app/`. 14 source modules + `tests/`:

```
CredChain_Python/
  app/
    main.py             → FastAPI app + lifespan (loads 3 models) + middleware + error handlers
    routes.py           → 4 endpoints: /extract /verify /extract-ids /health
    schemas.py          → Pydantic Response[T] envelope + per-endpoint payloads
    config.py           → pydantic-settings .env loader + custom CSV env source
    codes.py            → 50xxxx response codes (System/Extract/Verify/Health/AI)
    errors.py           → AppError + DEFAULT_MESSAGES + http_status_for
    logger.py           → structured JSON logger (mirrors Go's zap shape)
    ocr.py              → PyMuPDF + EasyOCR fallback, is_text_useful() check
    embeddings.py       → LaBSE encode + cosine_similarity helper
    llm.py              → llama-cpp-python wrapper: extract_fields only (with retry)
    description.py      → bilingual description from locales/ templates (no LLM call)
    i18n.py             → locale loader + localize(key, lang, **vars)
    comparison.py       → rapidfuzz token_set_ratio key matching + verdict mapping
    id_extractor.py     → regex-based ID extraction (built-in + custom patterns)
  tests/                → conftest.py + 14 test files (~123 tests, fully mocked)
    fixtures/           → shared test data
  models/qwen/          → gitignored, ~0.4 GB Qwen 0.5B Q4_K_M GGUF (mounted)
  models/easyocr/       → gitignored, ~150 MB EasyOCR weights (mounted)
  models/labse/         → gitignored, ~1.8 GB LaBSE weights (mounted)
  locales/              → tracked, JSON locale files (id, en) for description templates
  custom_id_patterns.txt → optional, gitignored, one regex per line
  pyproject.toml        → pinned deps + ruff + mypy + pytest config
  Makefile              → all critical commands
  Dockerfile            → multi-stage Python 3.11-slim build
  docker-compose.yml    → AI service + backend network attach
  CredChain_Python_postman_collection.json → endpoint testing collection
  .env / .env.docker / .env.example
  README.md
  AGENTS.md             → this file
```

## Key Patterns & Conventions

### Endpoints

All POST endpoints accept `files: list[UploadFile]` (multi-file batch). Hard cap `MAX_FILES_PER_REQUEST=100`.

| Method | Path | Purpose | Code |
|---|---|---|---|
| POST | `/extract` | Batch OCR + LaBSE embedding + Qwen field extraction | 500100 |
| POST | `/verify` | Batch cosine similarity + verdict + bilingual description | 500200 |
| POST | `/extract-ids` | Batch extract document/registration IDs (regex-only) | 500300 |
| GET | `/health` | Liveness + `models_loaded` flag | 500900 / 500950 |

Upload limit: 10 MB per file. Allowed MIME: `application/pdf`, `image/{jpeg,png,webp,tiff}`. `validate_files` enforces both limits before any processing.

### Multi-file Response Envelope

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
- `errors` keys use `files.<index>` notation (mirrors Go's field-error convention).
- Top-level `code` is the success code when ≥1 file succeeded; an error code when all failed.
- Shape mirrors the Go backend's `{code, message, data, errors}` envelope — same wire contract.

### `/verify` Metadata Blob (Option B)

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

`len(files) == len(metadata)` is required; mismatch returns HTTP 400 code `500241`. `parse_verify_metadata` in `routes.py` validates the JSON shape and raises `AppError` on malformed input.

### Custom ID Patterns

`/extract-ids` uses regex-only extraction (no LLM). Built-in patterns cover Indonesian IDs (NIK, NPWP, NIP, NIM) and generic codes (hyphenated, grouped alnum, prefixed alnum, UUID, ULID).

- Custom patterns are loaded from `CUSTOM_ID_PATTERNS_FILE` (default `./custom_id_patterns.txt`). File format: one regex per line, `#` for comments.
- Invalid regex → service refuses to start (fail fast at lifespan startup).
- `OVERRIDE_BUILTIN_ID_PATTERNS=true` skips built-in patterns entirely (custom-only mode).
- Pattern ordering: custom first, then built-in (when enabled).

### Models Loaded Once via Lifespan

Three heavyweight models are loaded once via FastAPI `lifespan` and accessed in handlers via `Depends()`:

| Module | Purpose | Approx Size |
|---|---|---|
| EasyOCR | OCR fallback when PyMuPDF text extraction is insufficient | ~150 MB |
| LaBSE (sentence-transformers) | multilingual embeddings for semantic similarity | ~1.8 GB |
| Qwen 2.5 0.5B Instruct (llama-cpp-python, Q4_K_M GGUF) | LLM-based field extraction | ~0.4 GB |

The lifespan handler sets `app.state.models_loaded = True` after all three load successfully. `/health` returns code `500900` (loaded) or `500950` (not yet ready).

Models are NOT baked into the Docker image — they are mounted from host (`./models` → `/models`). `make download-models` must run on the host once before first `docker-up-build`.

### Single-Worker Concurrency

Uvicorn runs with a single worker (`--workers 1`). LaBSE and Qwen are CPU-bound and not thread-safe; running multiple workers would multiply memory usage by N without throughput gain.

**Consequence:** while one client invokes `/extract`, no other client can call any endpoint until that request completes. Operators should size connection pool and request timeout accordingly. The Go backend should serialize calls to this service.

### OCR Fallback Chain (PyMuPDF → EasyOCR)

`app/ocr.py` extracts text using PyMuPDF first (fast, text-layer PDFs). Then `is_text_useful(text)` checks two heuristics:

- text length ≥ 50 characters, AND
- ≥ 80% of characters are printable

If either fails, the page is re-processed via EasyOCR (slower, image-based). This handles scanned PDFs and image uploads without paying the EasyOCR cost for clean text PDFs.

### Field Comparison & Verdict Thresholds

`app/comparison.py` matches keys with `rapidfuzz.token_set_ratio` (≥80 threshold), values with `rapidfuzz.partial_ratio` (≥85 threshold). Field similarity is averaged across matched keys; missing keys count as 0.

Verdict thresholds (named constants in `comparison.py`):

| Verdict | Similarity Range |
|---|---|
| `TAMPERED` | ≥ 0.95 (suspiciously near-perfect — likely copy with minor edits) |
| `SUSPICIOUS` | ≥ 0.75 |
| `LOW_SIMILARITY` | ≥ 0.40 |
| `NOT_SIMILAR` | < 0.40 |

The verdict is computed from BOTH embedding cosine similarity AND field similarity — see `comparison.compute_verdict` for the exact decision logic.

### Locale-Based Description Generation

`/verify` returns a bilingual human-readable description for each verdict. Descriptions are rendered from `locales/{en,id}.json` templates — **no LLM call** for descriptions. This keeps `/verify` fast and deterministic.

`app/i18n.localize(key, lang, **vars)` resolves the template and substitutes variables. `app/description.build_description(verdict, similarity, lang)` orchestrates the lookup.

### LLM Retry on JSON Parse Failure

`app/llm.extract_fields` retries once on JSON parse failure (Qwen occasionally emits trailing commas or unbalanced braces). On the second failure, raises `AppError(CODE_AI_EXTRACT_LLM_FAILED)` and the file's slot in the response is set to `null` with the error pushed under `files.<i>`.

### Custom Env CSV Source

`pydantic-settings 2.6.1` does not export `NoDecode`, which breaks list-of-string env parsing. `app/config.py` defines `_CsvEnvSettingsSource` and `_CsvDotEnvSettingsSource` that pre-split comma-separated values for `easyocr_langs` and `cors_allow_origins` before pydantic-settings sees them.

When adding a new CSV env var, register it in both sources or pydantic will treat the raw string as a single-element list.

## Configuration / Env Vars

| Var | Default | Purpose |
|---|---|---|
| `FASTAPI_PORT` | `8081` | HTTP port |
| `LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |
| `LOG_OUTPUT` | `stdout` | `stdout` or file path |
| `MODEL_DIR` | `/models` | parent dir for model subdirs |
| `EASYOCR_LANGS` | `id,en` | comma-separated languages |
| `LLM_MAX_NEW_TOKENS` | `512` | cap on Qwen generation length |
| `LLM_DEVICE` | `cpu` | `cpu` only currently |
| `LLM_MODEL_NAME` | `Qwen2.5-0.5B-Instruct` | display name in responses |
| `LLM_MODEL_FILE` | `qwen2.5-0.5b-instruct-q4_k_m.gguf` | actual GGUF file loaded |
| `EMBEDDING_MODEL_NAME` | `LaBSE` | display name in responses |
| `LOCALES_DIR` | `./locales` | parent dir for locale JSON files |
| `CUSTOM_ID_PATTERNS_FILE` | `./custom_id_patterns.txt` | optional regex patterns file |
| `OVERRIDE_BUILTIN_ID_PATTERNS` | `false` | `true` = skip built-in ID patterns |
| `MAX_FILES_PER_REQUEST` | `100` | hard cap on multi-file upload |
| `CORS_ALLOW_ORIGINS` | `*` | comma-separated origins |

## Testing

- **Framework:** pytest 8.3.4 + pytest-asyncio 0.24.0 + httpx 0.28.1 (for FastAPI TestClient)
- **Count:** ~123 tests across 14 test files. All mocked — no real model loads, no real network calls. Runs in <15s.
- **Fixtures:** `tests/conftest.py` provides `mock_easyocr_reader`, `mock_embedding_model`, `mock_llm`.
- **Coverage layout:** every `app/*.py` module has a matching `tests/test_*.py`.
- **mypy:** strict mode on `app/`; relaxed on `tests/` (allows missing return type annotations on test functions).
- **ruff config:** select `E,F,I,N,UP,B,SIM,RET,PT`; line-length 100; `B008` ignored in `app/routes.py` (FastAPI `Depends()` / `File()` defaults are idiomatic).
- **pytest config:** `testpaths=["tests"]`, asyncio mode auto.

When adding a new endpoint or module, add at least: one happy-path test, one validation-failure test, one downstream-failure test (mock the model raising), and one mypy-clean signature.

## Tech Stack

Pinned in `pyproject.toml`:

| Layer | Tool | Version |
|---|---|---|
| Language | Python | ≥3.11, <3.13 |
| Web framework | FastAPI | 0.115.5 |
| ASGI server | uvicorn[standard] | 0.32.1 |
| Multipart parser | python-multipart | 0.0.17 |
| Validation | pydantic | 2.10.3 |
| Settings | pydantic-settings | 2.6.1 |
| PDF | PyMuPDF | 1.25.1 |
| OCR | EasyOCR | 1.7.2 (id+en) |
| Embeddings | sentence-transformers (LaBSE) | 3.3.1 |
| LLM runtime | llama-cpp-python | 0.3.4 |
| LLM model | Qwen2.5-0.5B-Instruct Q4_K_M GGUF | ~0.4 GB |
| ML backend | torch (CPU) | 2.5.1 |
| Fuzzy match | rapidfuzz | 3.10.1 |
| Image | Pillow | 11.0.0 |
| Test | pytest | 8.3.4 |
| Async test | pytest-asyncio | 0.24.0 |
| HTTP test | httpx | 0.28.1 |
| Lint | ruff | 0.8.4 |
| Type check | mypy | 1.13.0 |

## Cross-Repo Integration

- **`../CredChain_Golang/AGENTS.md`** — sole HTTP caller. The Go backend serializes requests to this service. Response envelope `{code, message, data, errors}` matches the Go format exactly.
- **`../CredChain_React/AGENTS.md`** — never talks to this service directly. All AI flows go through the Go API.
- **`../CredChain_Solidity/AGENTS.md`** — no integration; this service never touches the chain.

Response codes use a 6-digit `AABBCC` format. This service owns category `50` (AI). The Go backend uses categories `10` (system), `20` (auth), `30` (user), `40` (credential). When the Go side surfaces a Python error to the frontend, it preserves the original `50xxxx` code so the React `CODE_TO_MESSAGE_KEY` map can look up the i18n key.

Locale files in `locales/{en,id}.json` provide the description templates rendered by `/verify`. Keep keys in lockstep with backend and frontend locale files — there is no automated sync check on the Python side, so the Go and React side checks act as the canary.

## Deployment

**Push to master branch only when build succeeds. Do not create feature branches, bugfix branches, or any other branch types — commit directly to master.**

Before pushing, run the repo's canonical verification command and confirm it passes:

- `CredChain_Golang`: `go test ./... && go vet ./... && gofmt -l .` (last must produce zero output)
- `CredChain_Solidity`: `npx hardhat compile && npx hardhat test`
- `CredChain_Python`: `make lint && make typecheck && make test`
- `CredChain_React`: `npm run lint && npm run build && npm run test && npm run check-locales`

## See Also

- `README.md` — quick-start for human contributors
- `Makefile` — canonical commands
- `CredChain_Python_postman_collection.json` — endpoint testing collection
- `pyproject.toml` — frozen dependency pins + tool config
- `../AGENTS.md` (workspace root, uncommitted) — multi-repo reference
- `../CredChain_Golang/AGENTS.md` — backend contract reference
