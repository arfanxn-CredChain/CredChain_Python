# CredChain Python AI Service

Internal FastAPI service for document OCR, field extraction (Gemini),
semantic similarity (EmbeddingGemma), and bilingual description rendering.

**Not for public exposure.** Reachable only inside the Docker `backend`
network by the Go backend at `http://credchain-python:8081`.

## Architecture

- **OCR + extraction:** Google Gemini (`gemini-3.1-flash-lite`)
- **Embeddings:** `google/embeddinggemma-300M` via sentence-transformers
- **ID extraction:** Gemini-native (no regex-only fallback)
- **Descriptions:** Rendered from locale templates in `./locales/{id,en}.json`

## Quickstart (local)

    cp .env.example .env
    # Edit .env: fill in GEMINI_API_KEY and HF_TOKEN
    make install
    make serve

## Quickstart (Docker)

    cp .env.example .env.docker
    # Edit .env.docker: fill in GEMINI_API_KEY and HF_TOKEN
    # Set LOCALES_DIR=/app/locales in .env.docker
    make docker-generate-api-key
    make docker-up-build

EmbeddingGemma (~300M params) downloads automatically on first startup.
The healthcheck waits up to 240s for model download.

## Endpoints

All POST endpoints accept **multiple files** (`files: list[UploadFile]`).
Response shape: `{code, message, data: list[T|null], errors: {"files.<i>": [...]}}`

| Method | Path | Purpose |
|--------|------|---------|
| POST | /extract | Batch OCR + Gemini field extraction + EmbeddingGemma embedding |
| POST | /verify | Batch similarity + verdict + bilingual description |
| POST | /extract-ids | Batch ID extraction (Gemini-native) |
| GET | /health | Liveness + model readiness |

### POST /extract

Upload one or more credential documents. Returns OCR text, 768-dim
EmbeddingGemma embedding, and Gemini-extracted field key-value pairs
per file.

```bash
curl -X POST http://localhost:8081/extract \
  -F "files=@doc1.pdf" -F "files=@doc2.pdf"
```

### POST /verify

Verify uploaded documents against stored embeddings and fields.
Accepts an `embeddings` JSON form field — an array of float arrays,
one per file, indexed by position.

```bash
curl -X POST http://localhost:8081/verify \
  -F "files=@doc.pdf" \
  -F 'embeddings=[[0.1,0.2,...],[0.3,0.4,...]]'
```

`len(files)` must equal `len(embeddings)`. Mismatch returns HTTP 400.

Verdicts: `TAMPERED` (≥0.95) | `SUSPICIOUS` (≥0.75) | `LOW_SIMILARITY` (≥0.55) | `NOT_SIMILAR` (<0.55)

Descriptions are rendered from `locales/{id,en}.json` templates.

### POST /extract-ids

Extract ID-like values from documents using Gemini (not regex-only).
Returns all ID-like values found in each document. Empty list is a
valid result (not an error).

```bash
curl -X POST http://localhost:8081/extract-ids \
  -F "files=@doc.pdf"
```

## Commands

    make test          # run pytest (mocked)
    make lint          # ruff check
    make typecheck     # mypy
    make format        # ruff format
    make docker-fresh  # down + rebuild + ps

## Key Env Vars

| Var | Default | Purpose |
|---|---|---|
| `FASTAPI_PORT` | 8081 | HTTP port |
| `GEMINI_API_KEY` | — | Google Gemini API key (required) |
| `HF_TOKEN` | — | HuggingFace token for EmbeddingGemma (required) |
| `API_KEY` | — | X-API-Key secret (empty = auth disabled) |
| `LOCALES_DIR` | ./locales | locale JSON files for descriptions |
| `MAX_FILES_PER_REQUEST` | 100 | hard cap on multi-file upload |

See `.env.example` for the full list.

## Postman Collection

Import `CredChain_Python_postman_collection.json` into Postman for
ready-to-use request examples for all endpoints.

## Spec

`docs/superpowers/specs/2026-05-30-credchain-python-regex-only-extract-ids-and-multifile.md`
