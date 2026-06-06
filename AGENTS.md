# CredChain Python - Agent Instructions

Python AI service called by the Go backend over HTTP. Uses Google Gemini (Files API + direct upload) for document extraction and EmbeddingGemma (sentence-transformers) for semantic similarity embeddings. Requires a Gemini API key — no longer fully offline. Reachable only inside the Docker backend network — **never expose to public internet** (no auth, no rate limiting).

This file is the authoritative reference for AI assistants and engineers working in `CredChain_Python/`.

## Repo Position

Sibling to `CredChain_Golang/` (backend, sole HTTP caller), `CredChain_Solidity/` (contracts), and `CredChain_React_Demo/` (deprecated).

- **Consumer:** the Go backend is the only intended caller. Requests flow `React → Go API → Python AI`. The frontend never talks to this service directly.
- **Locales:** `locales/{en,id}.json` are tracked and kept in sync with the corresponding files in `CredChain_Golang/locales/`.
- **Network isolation:** the service binds inside the Docker backend network only. There is no auth middleware, no rate limiter, no CORS protection beyond the configurable `CORS_ALLOW_ORIGINS` — exposing it publicly would allow arbitrary Gemini execution against arbitrary input.

## Critical Commands

```bash
python3.11 -m venv .venv && source .venv/bin/activate    # one-time
make install                                              # install deps + dev extras
make serve                                                # run uvicorn locally on :8081 (single worker)
make dev                                                  # uvicorn with --reload
make test                                                 # pytest tests/ -v
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
make serve              # binds :8081 by default
```

**Required API keys:**
- `GEMINI_API_KEY` — Google Gemini API key (fatal if empty; extraction calls will fail)
- `HF_TOKEN` — HuggingFace token for gated model access (required for EmbeddingGemma download)

EmbeddingGemma is downloaded at startup from HuggingFace Hub via `sentence-transformers`. No baked-in model files.

## Tech Stack

Pinned in `pyproject.toml`:

| Layer | Tool | Version |
|---|---|---|
| Language | Python | ≥3.11, <3.13 |
| Web framework | FastAPI | 0.115.5 |
| ASGI server | uvicorn[standard] | 0.32.1 |
| Gemini SDK | google-genai | — |
| Embeddings | sentence-transformers (EmbeddingGemma) | ≥3.3.1 |
| HuggingFace | huggingface-hub | — |
| Math | numpy | — |
| Image | Pillow | 11.0.0 |
| Test | pytest | 8.3.4 |
| Async test | pytest-asyncio | 0.24.0 |
| HTTP test | httpx | 0.28.1 |
| Lint | ruff | 0.8.4 |
| Type check | mypy | 1.13.0 |

## Project Architecture

Flat layout under `app/`. 12 source modules + `tests/`:

```
CredChain_Python/
  app/
    main.py             → FastAPI app + lifespan (loads EmbeddingGemma + initializes Gemini client) + i18n middleware + error handlers
    routes.py           → 4 endpoints: /extract /verify /extract-ids /health (all Gemini-piped)
    schemas.py          → Pydantic Response[T] envelope + per-endpoint payloads
    config.py           → pydantic-settings .env loader + custom CSV env source
    codes.py            → 50xxxx response codes (System/Extract/Verify/ExtractIds/Health)
    errors.py           → AppError + http_status_for
    logger.py           → structured JSON logger (mirrors Go's zap shape)
    gemini.py           → GeminiClient — Files API (batch) + direct upload (single) + retry logic
    embeddings.py       → EmbeddingGemma encode + cosine_similarity helper
    description.py      → single-language description from locales/ templates (no LLM call)
    i18n.py             → locale loader + localize(key, lang, **vars)
    verdict.py          → similarity → verdict mapping (configurable thresholds)
    prompts.py          → Gemini prompt constants (PROMPT_EXTRACT_DOCUMENT, PROMPT_EXTRACT_IDS)
  tests/                → conftest.py + test files (fully mocked)
    fixtures/           → shared test data
  locales/              → tracked, JSON locale files (id, en) for description templates
  pyproject.toml        → pinned deps + ruff + mypy + pytest config
  Makefile              → all critical commands
  Dockerfile            → multi-stage Python 3.11-slim build
  docker-compose.yml    → AI service + backend network attach
  .env / .env.docker / .env.example
  README.md
  AGENTS.md             → this file
```

## Key Patterns & Conventions

### Endpoints

All POST endpoints accept `files: list[UploadFile]` (multi-file batch). Hard cap `MAX_FILES_PER_REQUEST=100`.

| Method | Path | Purpose | Code |
|---|---|---|---|
| POST | `/extract` | Gemini Files API extraction, returns `{raw_text, ids, embeddings}` | 500100 |
| POST | `/verify` | Gemini direct upload + EmbeddingGemma similarity, returns `{similarity_score, similarity_percent, verdict, description}` | 500200 |
| POST | `/extract-ids` | Gemini ID extraction, returns `{ids}` only | 500300 |
| GET | `/health` | Liveness, returns `"healthy"` or `"model loading"` | 500900 / 500950 |

Upload limit: 10 MB per file. Allowed MIME: `application/pdf`, `image/{jpeg,png,webp,tiff}`. `validate_file` enforces both limits before any processing.

### Multi-file Response Envelope

```json
{
  "code": 500100,
  "message": "Document(s) extracted successfully",
  "data": [
    { "raw_text": "...", "ids": [...], "embeddings": [...] },
    null,
    { "raw_text": "...", "ids": [...], "embeddings": [...] }
  ],
  "errors": {
    "files.1": ["Gemini extraction failed"]
  }
}
```

- `data` is always a list of length `len(files)`. Failed files = `null`.
- `errors` keys use `files.<index>` notation (mirrors Go's field-error convention).
- Top-level `code` is the success code when ≥1 file succeeded; an error code when all failed.
- Shape mirrors the Go backend's `{code, message, data, errors}` envelope — same wire contract.

### `/verify` Metadata Blob

`/verify` uses a single `metadata` JSON form field pairing each file with its stored embeddings:

```
POST /verify
files: <file0.pdf>
files: <file1.pdf>
metadata: [
  {"stored_embeddings": [0.1, ...]},
  {"stored_embeddings": [0.3, ...]}
]
```

`len(files) == len(metadata)` is required; mismatch returns HTTP 400 code `500241`. `parse_verify_metadata` in `routes.py` validates the JSON shape and raises `AppError` on malformed input.

### Gemini Pipeline (Files API vs Direct Upload)

Two extraction paths in `app/gemini.py`:

- **Files API** (used by `/extract`): Upload files → poll until ACTIVE → generate content. Better for batch, supports larger files via Gemini's server-side processing.
- **Direct upload** (used by `/verify` and `/extract-ids`): Bytes inlined in the prompt. Simpler per-file flow, no polling overhead.

`GeminiClient` wraps both with built-in retry logic: up to 3 attempts for 429/RESOURCE_EXHAUSTED errors, with configurable `RETRY_WAIT_SECONDS` delay.

### Models Loaded via Lifespan

EmbeddingGemma (`google/embeddinggemma-300M`) is loaded once via FastAPI `lifespan` and accessed in handlers via `Depends(get_embedding_model)`. The Gemini client is initialized at startup and injected via `Depends(get_gemini_client)`.

The lifespan handler sets `app.state.models_loaded = True` after both initialize successfully. `/health` returns code `500900` (loaded, HTTP 200) or `500950` (not yet ready, HTTP 503).

### Single-Worker Concurrency

Uvicorn runs with a single worker (`--workers 1`). EmbeddingGemma is CPU-bound and not thread-safe; running multiple workers would multiply memory usage by N without throughput gain.

**Consequence:** while one client invokes `/extract` or `/verify`, others wait on the encoding step. Operators should size connection pool and request timeout accordingly. The Go backend should serialize calls to this service.

### Gemini Prompts

Extraction prompts are module-level constants in `app/prompts.py`:

- `PROMPT_EXTRACT_DOCUMENT` — extracts raw text + IDs, returns `{raw_text: str, ids: [{type: str, value: str}]}`
- `PROMPT_EXTRACT_IDS` — extracts IDs only, returns `{ids: [{type: str, value: str}]}`

Gemini is configured with `response_mime_type="application/json"` for structured JSON output. Non-JSON responses are caught and returned as empty dicts (with a warning printed).

### Verdict Thresholds

Verdict thresholds are configurable via env vars (defined in `app/verdict.py` and `app/config.py`):

| Verdict | Default Threshold | Description |
|---|---|---|
| `tampered` | ≥ 0.95 | Suspiciously near-perfect — likely copy with minor edits |
| `suspicious` | ≥ 0.75 | High similarity suggesting a derivative |
| `low_similarity` | ≥ 0.55 | Some overlap but uncertain |
| `not_similar` | < 0.55 | Unrelated documents |

Env vars: `VERDICT_TAMPERED_THRESHOLD`, `VERDICT_SUSPICIOUS_THRESHOLD`, `VERDICT_LOW_SIMILARITY_THRESHOLD`.

**Important:** Very high similarity (≥0.95) implies "tampered" because authentic re-issued documents always have natural OCR variance. A near-perfect match with a stored embedding suggests the same digital artifact was reused with minor edits.

The verdict is computed from embedding cosine similarity alone (EmbeddingGemma). Similarity is formatted as `"XX.X%"` via `verdict.format_percent()`.

### Locale-Based Description Generation

`/verify` returns a single-language human-readable description for each verdict (language resolved from `Accept-Language` header via i18n middleware). Descriptions are rendered from `locales/{en,id}.json` templates — **no LLM call** for descriptions. This keeps `/verify` fast and deterministic.

`app/i18n.localize(key, lang, **vars)` resolves the template and substitutes variables. `app/description.build_description(verdict, similarity_percent, lang)` orchestrates the lookup.

### i18n Middleware

`main.py` registers an i18n middleware (mirrors Go backend pattern):

```python
@app.middleware("http")
async def i18n_middleware(request, call_next):
    accept_lang = request.headers.get("Accept-Language", "").strip()
    lang = accept_lang.split(",")[0].split(";")[0].strip().lower()
    request.state.lang = lang if lang in {"id", "en"} else "id"
    return await call_next(request)
```

Supported languages: `id` (Indonesian, default), `en` (English). Unknown or missing `Accept-Language` falls back to `id`. Handlers read the resolved language via `get_lang(request)` → `request.state.lang`.

### Custom Env CSV Source

`pydantic-settings 2.6.1` does not export `NoDecode`, which breaks list-of-string env parsing. `app/config.py` defines `_CsvEnvSettingsSource` and `_CsvDotEnvSettingsSource` that pre-split comma-separated values for `cors_allow_origins` before pydantic-settings sees them.

## Configuration / Env Vars

| Var | Default | Purpose |
|---|---|---|
| `FASTAPI_PORT` | `8081` | HTTP port |
| `LOG_LEVEL` | `info` | `debug` / `info` / `warn` / `error` |
| `LOG_OUTPUT` | `stdout` | `stdout` or file path |
| `GEMINI_API_KEY` | — | Google Gemini API key (required) |
| `EXTRACTION_MODEL` | `gemini-3.1-flash-lite` | Gemini model for extraction |
| `RETRY_WAIT_SECONDS` | `60` | Delay between Gemini rate-limit retries |
| `HF_TOKEN` | — | HuggingFace token for gated model access |
| `EMBEDDING_MODEL_ID` | `google/embeddinggemma-300M` | HuggingFace model ID for embeddings |
| `VERDICT_TAMPERED_THRESHOLD` | `0.95` | Cosine similarity ≥ this → tampered |
| `VERDICT_SUSPICIOUS_THRESHOLD` | `0.75` | Cosine similarity ≥ this → suspicious |
| `VERDICT_LOW_SIMILARITY_THRESHOLD` | `0.55` | Cosine similarity ≥ this → low_similarity |
| `LOCALES_DIR` | `./locales` | Parent dir for locale JSON files |
| `MAX_FILES_PER_REQUEST` | `100` | Hard cap on multi-file upload |
| `CORS_ALLOW_ORIGINS` | `*` | Comma-separated origins |

## Testing

- **Framework:** pytest 8.3.4 + pytest-asyncio 0.24.0 + httpx 0.28.1 (for FastAPI TestClient)
- **Fixtures:** `tests/conftest.py` provides mocked `embedding_model` and `gemini_client` dependencies.
- **Coverage layout:** every `app/*.py` module has a matching `tests/test_*.py`.
- **mypy:** strict mode on `app/`; relaxed on `tests/` (allows missing return type annotations on test functions).
- **ruff config:** select `E,F,I,N,UP,B,SIM,RET,PT`; line-length 100; `B008` ignored in `app/routes.py` (FastAPI `Depends()` / `File()` defaults are idiomatic).
- **pytest config:** `testpaths=["tests"]`, asyncio mode auto.

When adding a new endpoint or module, add at least: one happy-path test, one validation-failure test, one downstream-failure test (mock the model raising), and one mypy-clean signature.

## Cross-Repo Integration

- **`../CredChain_Golang/AGENTS.md`** — sole HTTP caller. The Go backend serializes requests to this service. Response envelope `{code, message, data, errors}` matches the Go format exactly.
- **`../CredChain_Solidity/AGENTS.md`** — no integration; this service never touches the chain.

Response codes use a 6-digit `AABBCC` format. This service owns category `50` (AI). The Go backend uses categories `10` (system), `20` (auth), `30` (user), `40` (credential). When the Go side surfaces a Python error to the frontend, it preserves the original `50xxxx` code.

Locale files in `locales/{en,id}.json` provide the description templates rendered by `/verify`. Keep keys in lockstep with backend locale files.

## Deployment

**Push to master branch only when build succeeds. Do not create feature branches, bugfix branches, or any other branch types — commit directly to master.**

Before pushing, run the repo's canonical verification command and confirm it passes:

```bash
make lint && make typecheck && make test
```

## See Also

- `README.md` — quick-start for human contributors
- `Makefile` — canonical commands
- `pyproject.toml` — frozen dependency pins + tool config
- `../AGENTS.md` (workspace root, uncommitted) — multi-repo reference
- `../CredChain_Golang/AGENTS.md` — backend contract reference
