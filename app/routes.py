"""FastAPI router defining all four endpoints.

POST endpoints accept multi-file uploads. Response shape:
  {code, message, data: list[T | None], errors: {"files.<i>": [...]}}

Per-file failures surface in `errors` (Laravel-style); successful items
appear in `data` at the matching index. Top-level `code` reflects overall
outcome (success if any file succeeded, else error).
"""

import json
from typing import TYPE_CHECKING

import easyocr
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sentence_transformers import SentenceTransformer

from app import codes, comparison, embeddings, id_extractor, llm, logger, ocr, schemas
from app import description as desc_module
from app.config import settings
from app.errors import AppError

if TYPE_CHECKING:
    from llama_cpp import Llama

__all__ = [
    "ALLOWED_MIME_TYPES",
    "MAX_UPLOAD_BYTES",
    "comparison",
    "desc_module",
    "embeddings",
    "id_extractor",
    "llm",
    "ocr",
    "router",
    "schemas",
]

router = APIRouter()
log = logger.get_logger("routes")

# ---- constants ----
ALLOWED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
})
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


# ---- helpers ----
def validate_file(file: UploadFile) -> tuple[bytes, str]:
    """Check MIME type and size. Returns (bytes, mime_type) on success."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise AppError(
            codes.CODE_AI_VALIDATION,
            errors={"file": [f"Unsupported MIME type: {file.content_type}"]},
        )
    contents = file.file.read()
    if not contents:
        raise AppError(
            codes.CODE_AI_VALIDATION,
            errors={"file": ["File is empty"]},
        )
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
    """Parse metadata JSON form field into a list of VerifyMetadataItem.

    metadata_raw must be a JSON list of objects, each with stored_embeddings
    (list of floats) and stored_fields (dict of str to str). Length must
    equal expected_len (== len(files)).
    """
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
            errors={
                "metadata": [
                    f"Length mismatch: {len(parsed)} metadata entries vs {expected_len} files"
                ]
            },
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
    """Check files list size against MAX_FILES_PER_REQUEST."""
    if not files:
        raise AppError(
            codes.CODE_AI_VALIDATION,
            errors={"files": ["At least one file is required"]},
        )
    if len(files) > settings.max_files_per_request:
        raise AppError(
            codes.CODE_AI_VALIDATION,
            errors={
                "files": [
                    f"Too many files: {len(files)} > {settings.max_files_per_request}"
                ]
            },
        )


def log_request_outcome(request: Request, status_code: int, outcome: str) -> None:
    """Emit one structured log line per request (called by middleware)."""
    log.info(
        "request completed",
        extra={
            "extra_fields": {
                "request_id": getattr(request.state, "request_id", ""),
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": getattr(request.state, "latency_ms", 0),
                "outcome": outcome,
            }
        },
    )


# ---- dependency providers ----
def get_easyocr(request: Request) -> easyocr.Reader:
    return request.app.state.easyocr_reader


def get_embedding_model(request: Request) -> SentenceTransformer:
    return request.app.state.embedding_model  # type: ignore[no-any-return]


def get_llm(request: Request) -> "Llama":
    return request.app.state.llm  # type: ignore[no-any-return]


# ---- endpoints ----
@router.post(
    "/extract",
    response_model=schemas.Response[list[schemas.ExtractData | None]],
    summary="OCR + embeddings + field extraction (batch)",
)
async def extract(
    files: list[UploadFile] = File(...),
    reader: easyocr.Reader = Depends(get_easyocr),
    embed_model: SentenceTransformer = Depends(get_embedding_model),
    llm_inst: "Llama" = Depends(get_llm),
) -> schemas.Response[list[schemas.ExtractData | None]]:
    validate_files(files)
    data: list[schemas.ExtractData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0
    for i, file in enumerate(files):
        try:
            file_bytes, mime_type = validate_file(file)
            raw_text = ocr.extract_text(reader, file_bytes, mime_type)
            embeddings_list = embeddings.encode(embed_model, raw_text)
            fields = llm.extract_fields(llm_inst, raw_text)
            data.append(schemas.ExtractData(
                raw_text=raw_text,
                embeddings=embeddings_list,
                extracted_fields=fields,
            ))
            success_count += 1
        except AppError as exc:
            data.append(None)
            errors[f"files.{i}"] = [exc.message]
        except Exception as exc:
            data.append(None)
            errors[f"files.{i}"] = [f"Internal error: {exc}"]
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
    return schemas.Response(
        code=code,
        message=message,
        data=data,
        errors=errors or None,
    )


@router.post(
    "/verify",
    response_model=schemas.Response[list[schemas.VerifyData | None]],
    summary="Batch verify uploaded docs against per-file stored embeddings/fields",
)
async def verify(
    files: list[UploadFile] = File(...),
    metadata: str = Form(...),
    reader: easyocr.Reader = Depends(get_easyocr),
    embed_model: SentenceTransformer = Depends(get_embedding_model),
    llm_inst: "Llama" = Depends(get_llm),
) -> schemas.Response[list[schemas.VerifyData | None]]:
    validate_files(files)
    items = parse_verify_metadata(metadata, expected_len=len(files))
    data: list[schemas.VerifyData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0
    for i, (file, item) in enumerate(zip(files, items, strict=True)):
        try:
            file_bytes, mime_type = validate_file(file)
            raw_text = ocr.extract_text(reader, file_bytes, mime_type)
            embeddings_list = embeddings.encode(embed_model, raw_text)
            similarity = embeddings.cosine_similarity(embeddings_list, item.stored_embeddings)
            verdict = comparison.verdict_for(similarity)
            if verdict == "NOT_SIMILAR":
                comparison_dict: dict[str, schemas.FieldComparisonEntry] = {}
            else:
                fields_uploaded = llm.extract_fields(llm_inst, raw_text)
                comparison_dict = comparison.compare_fields(item.stored_fields, fields_uploaded)
            sim_percent = comparison.format_percent(similarity)
            desc = desc_module.build_description(verdict, similarity, sim_percent, comparison_dict)
            data.append(schemas.VerifyData(
                similarity_score=similarity,
                similarity_percent=sim_percent,
                verdict=verdict,
                description=schemas.VerifyDescription(id=desc["id"], en=desc["en"]),
                field_comparison=comparison_dict,
                processing=schemas.VerifyProcessing(
                    ocr_char_count=len(raw_text),
                    model_used="LaBSE",
                ),
            ))
            success_count += 1
        except AppError as exc:
            data.append(None)
            errors[f"files.{i}"] = [exc.message]
        except Exception as exc:
            data.append(None)
            errors[f"files.{i}"] = [f"Internal error: {exc}"]
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
    return schemas.Response(
        code=code,
        message=message,
        data=data,
        errors=errors or None,
    )


@router.post(
    "/extract-ids",
    response_model=schemas.Response[list[schemas.ExtractIdsData | None]],
    summary="Batch extract potential IDs from documents (regex-only, tier-2 flow)",
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
            raw_text = ocr.extract_text(reader, file_bytes, mime_type)
            potential_ids = id_extractor.extract_ids(raw_text)
            data.append(schemas.ExtractIdsData(
                raw_text=raw_text,
                potential_ids=potential_ids,
            ))
            success_count += 1
        except AppError as exc:
            data.append(None)
            errors[f"files.{i}"] = [exc.message]
        except Exception as exc:
            data.append(None)
            errors[f"files.{i}"] = [f"Internal error: {exc}"]
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
    return schemas.Response(
        code=code,
        message=message,
        data=data,
        errors=errors or None,
    )


@router.get(
    "/health",
    response_model=schemas.Response[schemas.HealthData],
    summary="Liveness + model readiness check",
)
async def health(request: Request) -> schemas.Response[schemas.HealthData]:
    models_loaded = getattr(request.app.state, "models_loaded", False)
    return schemas.Response(
        code=codes.CODE_AI_HEALTH_SUCCESS if models_loaded else codes.CODE_AI_HEALTH_NOT_READY,
        message="Service is healthy" if models_loaded else "Models not yet loaded",
        data=schemas.HealthData(
            status="ok" if models_loaded else "starting",
            models_loaded=models_loaded,
        ),
    )
