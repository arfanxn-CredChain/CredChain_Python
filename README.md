# CredChain — Python AI Service

Internal FastAPI service for document OCR, field extraction (Gemini), semantic similarity (EmbeddingGemma), and bilingual description rendering.

Not for public exposure. Reachable only inside the Docker `backend` network at `http://python:8081`.

## Stack

Python 3.11 · FastAPI 0.115.5 · Uvicorn 0.32.1 · Google Gemini (genai 2.8.0) · EmbeddingGemma via sentence-transformers · torch 2.12.0 (CPU-only) · slowapi 0.1.9

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/extract` | Batch OCR + Gemini extraction + EmbeddingGemma embedding |
| POST | `/verify` | Batch similarity + verdict + bilingual description |
| POST | `/extract-ids` | Batch ID extraction (Gemini-native) |
| GET | `/health` | Liveness + model readiness |

All POST endpoints accept multiple files. Response shape: `{code, message, data, errors}`.
`/verify` accepts an `embeddings` JSON form field (array of float arrays), one per file.
POST endpoints require `X-API-Key` header (disabled when `API_KEY` is empty).

### Verdicts

| Verdict | Threshold |
|---|---|
| `tampered` | similarity ≥ 0.95 |
| `suspicious` | similarity ≥ 0.75 |
| `low_similarity` | similarity ≥ 0.55 |
| `not_similar` | similarity < 0.55 |

## Quick Start

```bash
# Local
cp .env.example .env
# Set GEMINI_API_KEY and HF_TOKEN
make install
make serve

# Docker
cp .env.example .env.docker
# Set GEMINI_API_KEY and HF_TOKEN
make docker-generate-api-key
make docker-up-build
```

The health check waits up to 600s for the embedding model to download on first start.

## Project Structure

```
app/
├── main.py           # FastAPI app, lifespan (model loading), middleware
├── routes.py         # 4 endpoints
├── schemas.py        # Pydantic response models
├── config.py         # Pydantic-settings env loader
├── codes.py          # 50xxxx response codes
├── errors.py         # AppError + HTTP status mapping
├── gemini.py         # Gemini client (Files API + direct upload + retry)
├── embeddings.py     # EmbeddingGemma encode + cosine_similarity
├── verdict.py        # Similarity → verdict mapping
├── description.py    # Bilingual description from locale templates
├── i18n.py           # Locale loader + localize()
├── prompts.py        # Gemini prompt constants
├── middleware.py      # slowapi rate limiter
├── cli.py            # Typer CLI (generate-api-key)
└── logger.py         # Structured JSON logger
```

## Key Commands

| Command | Purpose |
|---|---|
| `make serve` | Start dev server |
| `make test` | Run tests |
| `make lint` | Ruff lint |
| `make typecheck` | Mypy |
| `make docker-up` | Start Docker containers |
| `make generate-api-key` | Generate a 64-char hex API key |

## Related Docs

- [AGENTS.md](AGENTS.md) — Full architecture, middleware details, cross-repo integration
