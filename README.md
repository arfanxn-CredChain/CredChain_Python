# CredChain Python AI Service

Internal FastAPI service for OCR, field extraction, semantic similarity,
and bilingual description generation on credential documents.

**Not for public exposure.** Reachable only inside the Docker `backend`
network by the Go backend at `http://credchain-python:8081`.

## Quickstart (local)

    cp .env.example .env
    make install
    make serve

## Quickstart (Docker)

Models are NOT baked into the Docker image — they live on the host and
are mounted as read-only volumes at runtime. Run `make download-models`
once before the first build:

    make install
    make download-models

This downloads three models into host directories (gitignored):

| Directory | Model | Size |
|---|---|---|
| `./models/easyocr/` | EasyOCR (id + en) | ~150 MB |
| `./models/labse/` | LaBSE (sentence-transformers) | ~1.8 GB |
| `./models/qwen/` | Qwen2.5-0.5B-Instruct Q4_K_M GGUF | ~0.4 GB |

The download is resumable — re-run `make download-models` if it fails
partway. Already-downloaded files are skipped automatically.

Once models are downloaded:

    make docker-up-build

## Endpoints

All POST endpoints accept **multiple files** (`files: list[UploadFile]`).
Response shape: `{code, message, data: list[T|null], errors: {"files.<i>": [...]}}`

| Method | Path | Purpose |
|--------|------|---------|
| POST | /extract | Batch OCR + LaBSE embedding + Qwen field extraction |
| POST | /verify | Batch similarity + verdict + bilingual description |
| POST | /extract-ids | Batch regex-based ID extraction (no LLM) |
| GET | /health | Liveness + model readiness |

### POST /extract

Upload one or more credential documents. Returns OCR text, 768-dim
LaBSE embedding, and Qwen-extracted field key-value pairs per file.

```bash
curl -X POST http://localhost:8081/extract \
  -F "files=@doc1.pdf" -F "files=@doc2.pdf"
```

### POST /verify

Verify uploaded documents against stored embeddings and fields.
Uses **Option B metadata blob** — a single `metadata` JSON form field
pairing each file with its stored data by index.

```bash
curl -X POST http://localhost:8081/verify \
  -F "files=@doc.pdf" \
  -F 'metadata=[{"stored_embeddings":[0.1,...],"stored_fields":{"name":"John"}}]'
```

`len(files)` must equal `len(metadata)`. Mismatch returns HTTP 400.

Verdicts: `TAMPERED` (≥0.95) | `SUSPICIOUS` (≥0.75) | `LOW_SIMILARITY` (≥0.40) | `NOT_SIMILAR` (<0.40)

Descriptions are rendered from `locales/{id,en}.json` templates — no LLM call.

### POST /extract-ids

Regex-only ID extraction (no LLM). Returns all ID-like values found
in each document. Empty list is a valid result (not an error).

```bash
curl -X POST http://localhost:8081/extract-ids \
  -F "files=@doc.pdf"
```

Built-in patterns: Indonesian NIK (16-digit), NIP (18-digit), NIM (8-12 digit),
NPWP, plus generic hyphenated codes, grouped alnum, UUID, ULID.

Custom patterns: create `./custom_id_patterns.txt` (one regex per line).
Set `OVERRIDE_BUILTIN_ID_PATTERNS=true` to use only custom patterns.

## Commands

    make test          # run pytest (mocked, ~15s, 123 tests)
    make lint          # ruff check
    make typecheck     # mypy
    make format        # ruff format
    make docker-fresh  # down + rebuild + ps

## Models (mounted at runtime)

- EasyOCR (id + en)
- LaBSE (sentence-transformers)
- Qwen2.5-0.5B-Instruct Q4_K_M GGUF (via llama-cpp-python)

The LLM layer uses llama.cpp with 4-bit quantization (Q4_K_M GGUF) for fast
CPU inference. `/extract` completes in ~10-30 seconds; `/verify` in ~25-30
seconds. Bilingual descriptions for `/verify` are rendered from locale
templates in `./locales/{id,en}.json` (no LLM call for descriptions).

## Key Env Vars

| Var | Default | Purpose |
|---|---|---|
| `FASTAPI_PORT` | 8081 | HTTP port |
| `MODEL_DIR` | /models | parent dir for model subdirs |
| `CUSTOM_ID_PATTERNS_FILE` | ./custom_id_patterns.txt | optional regex patterns |
| `OVERRIDE_BUILTIN_ID_PATTERNS` | false | true = skip built-in ID patterns |
| `MAX_FILES_PER_REQUEST` | 100 | hard cap on multi-file upload |
| `LOCALES_DIR` | ./locales | locale JSON files for descriptions |

See `.env.example` for the full list.

## Postman Collection

Import `CredChain_Python_postman_collection.json` into Postman for
ready-to-use request examples for all endpoints.

## Spec

`docs/superpowers/specs/2026-05-30-credchain-python-regex-only-extract-ids-and-multifile.md`
