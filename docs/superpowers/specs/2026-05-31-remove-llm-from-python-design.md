# Remove LLM from CredChain_Python — Design Spec

**Date:** 2026-05-31
**Status:** Approved
**Scope:** `CredChain_Python/` only (Go backend updates tracked separately)

## 1. Goal & Scope

Remove the Qwen LLM (field extraction) from `CredChain_Python` entirely. The LLM is the single largest contributor to per-request latency (~3–15s on CPU per file) and adds ~0.4 GB to the model footprint. Removing it produces a faster, simpler, deterministic verification pipeline that relies only on OCR + LaBSE embedding similarity.

Aggressive cleanup of all dead code is part of this change — we will not retain disabled stubs. Models change from host-volume-mounted to baked-in via a multi-stage Dockerfile. Verdict strings are lowercased.

This spec covers Python only. Wire-format changes affect the Go backend; those updates will be tracked in a separate spec on the Go side.

## 2. Success Criteria

- `/extract` returns only `{raw_text, embeddings}` per file
- `/verify` returns only `{similarity_score, similarity_percent, verdict, description}` per file (no `field_comparison`, no `processing`)
- Verdicts are lowercase: `tampered`, `suspicious`, `low_similarity`, `not_similar`
- `/extract-ids` and `/health` unchanged
- `make lint && make typecheck && make test` all pass
- Service starts in seconds (no LLM weight load)
- Docker image carries EasyOCR + LaBSE weights baked in via multi-stage build
- `llama-cpp-python` no longer in dependencies
- `make download-models` removed from Makefile
- `app/llm.py` deleted
- `tests/test_llm.py` deleted
- `CredChain_Python/AGENTS.md` updated to reflect new architecture

## 3. Background & Context

### 3.1 Current state

`CredChain_Python` loads three models at startup via FastAPI lifespan:

| Model | Purpose | Size |
|---|---|---|
| EasyOCR | OCR fallback for scanned PDFs / images | ~150 MB |
| LaBSE | Multilingual sentence embeddings | ~1.8 GB |
| Qwen 2.5 0.5B Q4_K_M (llama-cpp-python) | Structured field extraction | ~0.4 GB |

The Qwen model is the slowest component on CPU. `/extract` calls it for every file. `/verify` calls it only when similarity ≥ 0.40 (the `NOT_SIMILAR` threshold).

Models live on the host at `./models/{easyocr,labse,qwen}/` and are mounted into the Docker container at `/models` via `docker-compose.yml`. `make download-models` populates them.

### 3.2 Why LLM removal is safe

The core verification pipeline does not depend on the LLM:

1. OCR (PyMuPDF → EasyOCR fallback) extracts text
2. LaBSE encodes the text into a 768-dim vector
3. Cosine similarity against a stored embedding produces a score in `[-1, 1]`
4. `verdict_for(similarity)` maps the score to one of four labels
5. `description.build_description(...)` renders a bilingual description from locale templates (no LLM)

The LLM was only used for one feature: comparing extracted fields (`name`, `id_number`, etc.) between stored and uploaded documents. With option B (schemas removed entirely), this feature is dropped along with its inputs and outputs.

## 4. Endpoint Behavior (after change)

### 4.1 `POST /extract`

**Steps:**
1. Validate files (MIME, size, count)
2. OCR each file (PyMuPDF → EasyOCR fallback)
3. Encode with LaBSE
4. Return `{raw_text, embeddings}` per file

**Response:**

```json
{
  "code": 500100,
  "message": "Document(s) extracted successfully",
  "data": [
    { "raw_text": "...", "embeddings": [0.1, 0.2, ...] },
    null
  ],
  "errors": { "files.1": ["..."] }
}
```

### 4.2 `POST /verify`

**Steps:**
1. Validate files + parse `metadata` (only `stored_embeddings` per item; `stored_fields` removed)
2. OCR each file
3. Encode with LaBSE → cosine similarity against `stored_embeddings`
4. Map to verdict (lowercase)
5. Build bilingual description from locale templates
6. Return `{similarity_score, similarity_percent, verdict, description}` per file

**Request metadata:**

```
metadata: [
  {"stored_embeddings": [0.1, ...]},
  {"stored_embeddings": [0.3, ...]}
]
```

**Response:**

```json
{
  "code": 500200,
  "message": "Verification(s) completed",
  "data": [
    {
      "similarity_score": 0.91,
      "similarity_percent": "91.0%",
      "verdict": "suspicious",
      "description": { "id": "...", "en": "..." }
    }
  ]
}
```

### 4.3 `POST /extract-ids` — unchanged

### 4.4 `GET /health` — unchanged (still returns `models_loaded` flag, but only checks two models)

## 5. Files Changed

### 5.1 Application code

| File | Action |
|---|---|
| `app/llm.py` | **Delete** |
| `app/main.py` | Remove Qwen import + lifespan loading + `llm_lock`; force `easyocr.Reader(gpu=False)` |
| `app/routes.py` | Remove `get_llm`, `get_llm_lock`, `threading`, `llm` imports; simplify `/extract` and `/verify` handlers; remove `llm_lock`-related logic |
| `app/schemas.py` | Drop `extracted_fields` from `ExtractData`; drop `field_comparison` and `processing` from `VerifyData`; delete `FieldComparisonEntry` and `VerifyProcessing`; drop `stored_fields` from `VerifyMetadataItem` |
| `app/comparison.py` | Delete `compare_fields`, `_best_key_match`, `KEY_MATCH_THRESHOLD`, `VALUE_MATCH_THRESHOLD`; lowercase return strings in `verdict_for` |
| `app/config.py` | Remove `llm_max_new_tokens`, `llm_device`, `llm_timeout_seconds`, `llm_model_name`, `llm_model_file`, and `validate_model_paths` validator |
| `app/codes.py` | Remove `CODE_AI_EXTRACT_LLM_FAILED`, `CODE_AI_LLM_TIMEOUT`, and any other LLM-only codes |
| `app/description.py` | If verdict-key lookups reference uppercase strings, update to lowercase |
| `app/errors.py` | Remove `DEFAULT_MESSAGES` entries for deleted codes |

### 5.2 Locale files

| File | Action |
|---|---|
| `locales/en.json` | Lowercase verdict description keys if currently uppercase; remove any LLM-specific error keys |
| `locales/id.json` | Same as above |

### 5.3 Build / config

| File | Action |
|---|---|
| `pyproject.toml` | Remove `llama-cpp-python` dependency |
| `Makefile` | Remove `download-models` target and reference in `help` |
| `Dockerfile` | Convert to multi-stage: `model-downloader` stage + `runtime` stage (see §6) |
| `docker-compose.yml` | Remove `./models:/models` volume mount |
| `.env.example` | Remove `LLM_*` env vars |
| `.env.docker` | Remove `LLM_*` env vars |

### 5.4 Tests

| File | Action |
|---|---|
| `tests/test_llm.py` | **Delete** |
| `tests/conftest.py` | Remove `mock_llm` fixture |
| `tests/test_routes.py` | Remove `llm` from `_build_app`; drop `routes.llm` monkeypatches; assert new response shapes; assert lowercase verdicts |
| `tests/test_comparison.py` | Drop tests for deleted functions; assert lowercase verdict return values |
| `tests/test_config.py` | Drop assertions for removed LLM env vars |
| `tests/test_main.py` | Drop assertions for `app.state.llm`, `app.state.llm_lock` |
| `tests/test_schemas.py` | Drop assertions for deleted schema fields/types |

### 5.5 Documentation

| File | Action |
|---|---|
| `CredChain_Python/AGENTS.md` | Comprehensive update — see §10 for the per-section list |

## 6. Docker Architecture (Multi-Stage Build)

**Current:** Models live on host (`./models/{easyocr,labse,qwen}/`), mounted into container via `docker-compose.yml`.

**New:** Models baked into the image via multi-stage Dockerfile. No host directory needed. Volume mount removed from `docker-compose.yml`.

### 6.1 Dockerfile structure

```dockerfile
# Stage 1: download models
FROM python:3.11-slim AS model-downloader
RUN pip install --no-cache-dir easyocr sentence-transformers
WORKDIR /models
RUN python -c "import easyocr; easyocr.Reader(['id','en'], \
    model_storage_directory='/models/easyocr', download_enabled=True)"
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/LaBSE').save('/models/labse')"

# Stage 2: runtime
FROM python:3.11-slim AS runtime
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .
COPY --from=model-downloader /models /models
COPY app/ ./app/
COPY locales/ ./locales/
ENV MODEL_DIR=/models
EXPOSE 8081
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "1"]
```

### 6.2 Trade-offs

- **Image size:** ~2.1 GB final (1.95 GB models + Python + deps). Acceptable since service runs on a private network.
- **Build time:** Longer on cache miss (~1.95 GB downloaded); fast on cache hit since the model layer rarely changes.
- **Runtime:** Faster startup (no first-time download), simpler operations (no `make download-models` step).
- **Model swap:** Requires image rebuild. Acceptable because models are pinned versions.


## 7. Verdict & Description Logic

### 7.1 Verdict thresholds (unchanged thresholds, lowercase labels)

`comparison.verdict_for(similarity)` returns lowercase strings:

| Similarity Range | Verdict |
|---|---|
| ≥ 0.95 | `tampered` |
| ≥ 0.75 | `suspicious` |
| ≥ 0.40 | `low_similarity` |
| < 0.40 | `not_similar` |

Threshold constants (`VERDICT_TAMPERED_MIN`, `VERDICT_SUSPICIOUS_MIN`, `VERDICT_LOW_SIMILARITY_MIN`) stay the same.

### 7.2 Description templates

Current `locales/{en,id}.json` templates reference matched/mismatched field counts (because the LLM produced field comparisons). After this change, those template variables (`matched`, `mismatched`, `match_count`, `total_count`) are no longer available.

**Action:** Update locale templates to drop field-comparison variables. New templates describe only the similarity-based verdict.

**New templates (human-friendly, no verdict label in text, no dash placeholders):**

`locales/en.json`:

```json
{
  "verdict.tampered": "This document looks almost identical to the one we have on file ({percent} similarity), which usually means it has been duplicated or tampered with. We recommend a closer review before accepting it.",
  "verdict.suspicious": "This document is a strong match for the one we have on file ({percent} similarity), but a few details look off. A manual review is recommended before accepting it.",
  "verdict.low_similarity": "This document only loosely resembles the one we have on file ({percent} similarity). It may be a different version, an outdated copy, or an unrelated document.",
  "verdict.not_similar": "This document does not appear to match the one we have on file ({percent} similarity). It is most likely a different document entirely."
}
```

`locales/id.json`:

```json
{
  "verdict.tampered": "Dokumen ini terlihat hampir identik dengan dokumen yang kami miliki (kemiripan {percent}), yang biasanya berarti dokumen ini telah diduplikasi atau dimanipulasi. Sebaiknya lakukan peninjauan lebih lanjut sebelum dokumen diterima.",
  "verdict.suspicious": "Dokumen ini cukup mirip dengan dokumen yang kami miliki (kemiripan {percent}), namun ada beberapa detail yang terlihat berbeda. Sebaiknya dilakukan peninjauan manual sebelum dokumen diterima.",
  "verdict.low_similarity": "Dokumen ini hanya sedikit menyerupai dokumen yang kami miliki (kemiripan {percent}). Kemungkinan ini adalah versi yang berbeda, salinan lama, atau dokumen yang tidak terkait.",
  "verdict.not_similar": "Dokumen ini tampaknya tidak cocok dengan dokumen yang kami miliki (kemiripan {percent}). Kemungkinan besar ini adalah dokumen yang sepenuhnya berbeda."
}
```

The verdict label is no longer embedded in the description text — consumers read the wire-format `verdict` field for the label and the `description` field for the human-readable explanation. The template lookup key (`verdict.tampered`) is already lowercase via `verdict.lower()` in `description.py:24`.

### 7.3 `description.build_description` signature change

Current signature:

```python
def build_description(verdict, score, similarity_percent, field_comparison) -> dict[str, str]
```

New signature:

```python
def build_description(verdict, similarity_percent) -> dict[str, str]
```

`field_comparison` parameter and `score` parameter both removed (the `score` parameter was always passed alongside `similarity_percent`, both derived from the same value).

`FieldComparisonEntry` import removed from `description.py`.

## 8. Testing Approach

### 8.1 Test files updated/deleted

| File | Change |
|---|---|
| `tests/test_llm.py` | **Deleted** |
| `tests/conftest.py` | Remove `mock_llm` fixture |
| `tests/test_routes.py` | `_build_app()` no longer takes `llm` param; remove `app.state.llm`/`llm_lock`; drop `routes.llm` monkeypatches; new assertions on response shapes; assert lowercase verdicts |
| `tests/test_comparison.py` | Drop tests for `compare_fields` and `_best_key_match`; update `verdict_for` tests to expect lowercase return values |
| `tests/test_config.py` | Drop assertions for `llm_max_new_tokens`, `llm_device`, `llm_timeout_seconds`, `llm_model_name`, `llm_model_file` |
| `tests/test_main.py` | Drop assertions for `app.state.llm`, `app.state.llm_lock` |
| `tests/test_schemas.py` | Drop `FieldComparisonEntry`, `VerifyProcessing` tests; update `ExtractData`, `VerifyData`, `VerifyMetadataItem` shape tests |
| `tests/test_description.py` | Update for new `build_description` signature; drop field-comparison fixtures |

### 8.2 New tests to add

- `test_verify_returns_lowercase_verdict` — verifies wire-format change
- `test_verify_no_field_comparison_in_response` — verifies field is gone from response
- `test_extract_no_extracted_fields_in_response` — verifies field is gone from response
- `test_verify_metadata_no_stored_fields_required` — `/verify` accepts metadata items with only `stored_embeddings`
- `test_verdict_for_returns_lowercase` — all four branches in `comparison.verdict_for`

### 8.3 Verification commands

Per `AGENTS.md`:

```bash
make lint && make typecheck && make test
```

All three must pass. Test count is expected to decrease from ~123 to roughly ~110–115 after `test_llm.py` deletion and removed fixtures.

## 9. Migration & Risk

### 9.1 Breaking wire-format changes (Go backend impact)

These changes break the existing contract with the Go backend. Go updates are tracked in a separate spec.

1. `/extract` response: `extracted_fields` removed from each `data` item
2. `/verify` request: `metadata[].stored_fields` no longer accepted (Go must stop sending)
3. `/verify` response:
   - `field_comparison` removed
   - `processing` removed
   - `verdict` is lowercase

### 9.2 Coordinated deploy

Python rollout must align with Go backend rollout. Recommended order:

1. Land Go backend update that tolerates new shape (optional fields, lowercase parsing)
2. Land Python change in this spec
3. Land Go backend cleanup (remove unused field handling)

If Python deploys first without Go preparation, Go callers will fail JSON parsing on `/extract` and `/verify` responses.

### 9.3 Data migration (Go side)

Stored credentials likely cache `extracted_fields` / `stored_fields` in Postgres. Go side must decide:

- Drop the columns
- Keep them but stop writing
- Migrate to embedding-only verification

This decision belongs in the separate Go-side spec.

### 9.4 Locale impact

`locales/{en,id}.json` templates currently reference variables that won't exist anymore (`matched`, `mismatched`, `match_count`, `total_count`). Templates must be rewritten — see §7.2.

These locale files are kept in sync with `CredChain_Golang/locales/` and `CredChain_React/src/shared/i18n/`. Sync is a separate task on those repos. The Go-side spec must include locale propagation.

### 9.5 Rollback

Revert the merge commit. Old `make download-models` flow + LLM are recoverable from git history. Note: Docker volume mount must also be re-added if rolled back.

### 9.6 First-time Docker build

The new multi-stage build downloads ~1.95 GB of models during the first build. Subsequent builds use the layer cache and are fast. CI/CD pipelines must accommodate the longer initial build window.

## 10. AGENTS.md Update Scope

Sections to update in `CredChain_Python/AGENTS.md`:

| AGENTS.md Section | Change |
|---|---|
| Opening paragraph | Remove "field extraction" from purpose statement |
| Critical Commands | Remove `make download-models` line + Qwen comment |
| Environment Setup | Drop `make download-models` step; update model-size total (~2.5 GB → ~1.95 GB); note models are baked into Docker image |
| Project Architecture (file tree) | Remove `app/llm.py`; remove `models/qwen/` line |
| Endpoints table | Update `/extract` purpose; update `/verify` purpose |
| Multi-file Response Envelope | Update example to remove `extracted_fields` |
| `/verify` Metadata Blob | Update example: items only have `stored_embeddings` |
| Models Loaded Once via Lifespan | Drop Qwen row; "Three" → "Two"; remove "0.4 GB" |
| Single-Worker Concurrency | Update reasoning (LaBSE only); still single worker for memory |
| Field Comparison & Verdict Thresholds | Remove field-comparison paragraph; keep verdict thresholds; lowercase the verdict labels in the table |
| Locale-Based Description Generation | Note verdict keys are lowercase |
| LLM Retry on JSON Parse Failure | **Delete entire section** |
| Configuration / Env Vars table | Remove `LLM_*` rows, `EMBEDDING_MODEL_NAME` |
| Testing | Update test count (~123 → ~110–115); remove `test_llm.py` reference |
| Tech Stack table | Remove `llama-cpp-python`, `LLM model` (Qwen GGUF), `LLM runtime` rows |
| Cross-Repo Integration | Add note: `/extract` and `/verify` wire format changed; Go backend has follow-up work |

## 11. Out of Scope

The following are explicitly NOT covered by this spec:

- Go backend (`CredChain_Golang/`) updates — separate spec
- React frontend (`CredChain_React/`) updates — no impact expected
- Solidity contract changes — no impact
- Database migration on Go side — separate spec
- Replacement field extraction (no alternative is being introduced)
- Making the LLM optional / pluggable — explicitly rejected during brainstorming
- Performance tuning of LaBSE encoding — no changes to encoding logic
- Changing OCR fallback heuristics — no changes to `is_text_useful()`
- Custom ID pattern logic — no changes to `id_extractor.py`

