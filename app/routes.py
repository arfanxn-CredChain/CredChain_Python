"""FastAPI router defining all four endpoints.

POST endpoints accept multi-file uploads. Response shape:
  {code, message, data: list[T | None], errors: {"files.<i>": [...]}}

Per-file failures surface in `errors` (Laravel-style); successful items
appear in `data` at the matching index. Top-level `code` reflects overall
outcome (success if any file succeeded, else error).
"""

import asyncio
import json

import easyocr
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer

from app import codes, comparison, embeddings, id_extractor, logger, ocr, schemas
from app import description as desc_module
from app.config import settings
from app.errors import AppError

__all__ = [
    "ALLOWED_MIME_TYPES",
    "MAX_UPLOAD_BYTES",
    "comparison",
    "desc_module",
    "embeddings",
    "id_extractor",
    "ocr",
    "router",
    "schemas",
]

router = APIRouter()
log = logger.get_logger("routes")

ALLOWED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
})
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


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
            errors={"file": [f"File too large: {len(contents)} bytes > {MAX_UPLOAD_BYTES}"]},
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


def get_easyocr(request: Request) -> easyocr.Reader:
    return request.app.state.easyocr_reader


def get_embedding_model(request: Request) -> SentenceTransformer:
    return request.app.state.embedding_model  # type: ignore[no-any-return]


@router.post(
    "/extract",
    response_model=schemas.Response[list[schemas.ExtractData | None]],
    summary="OCR + embeddings (batch)",
)
async def extract(
    files: list[UploadFile] = File(...),
    reader: easyocr.Reader = Depends(get_easyocr),
    embed_model: SentenceTransformer = Depends(get_embedding_model),
) -> schemas.Response[list[schemas.ExtractData | None]]:
    validate_files(files)
    data: list[schemas.ExtractData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0
    for i, file in enumerate(files):
        try:
            file_bytes, mime_type = validate_file(file)
            raw_text = await asyncio.to_thread(ocr.extract_text, reader, file_bytes, mime_type)
            embeddings_list = await asyncio.to_thread(embeddings.encode, embed_model, raw_text)
            data.append(schemas.ExtractData(
                raw_text=raw_text,
                embeddings=embeddings_list,
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
        codes.CODE_AI_EXTRACT_SUCCESS
        if success_count > 0
        else codes.CODE_AI_EXTRACT_OCR_FAILED
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
    reader: easyocr.Reader = Depends(get_easyocr),
    embed_model: SentenceTransformer = Depends(get_embedding_model),
) -> schemas.Response[list[schemas.VerifyData | None]]:
    validate_files(files)
    items = parse_verify_metadata(metadata, expected_len=len(files))
    data: list[schemas.VerifyData | None] = []
    errors: dict[str, list[str]] = {}
    success_count = 0
    for i, (file, item) in enumerate(zip(files, items, strict=True)):
        try:
            file_bytes, mime_type = validate_file(file)
            raw_text = await asyncio.to_thread(ocr.extract_text, reader, file_bytes, mime_type)
            embeddings_list = await asyncio.to_thread(embeddings.encode, embed_model, raw_text)
            similarity = embeddings.cosine_similarity(embeddings_list, item.stored_embeddings)
            verdict = comparison.verdict_for(similarity)
            sim_percent = comparison.format_percent(similarity)
            lang = request.headers.get("Accept-Language", "id")
            desc = desc_module.build_description(verdict, sim_percent, lang)
            data.append(schemas.VerifyData(
                similarity_score=similarity,
                similarity_percent=sim_percent,
                verdict=verdict,
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
    summary="Batch extract potential IDs from documents (regex-only)",
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
            raw_text = await asyncio.to_thread(ocr.extract_text, reader, file_bytes, mime_type)
            potential_ids = id_extractor.extract_ids(raw_text)
            data.append(schemas.ExtractIdsData(
                raw_text=raw_text,
                potential_ids=potential_ids,
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


@router.get("/health", summary="Liveness + model readiness check")
async def health(request: Request) -> JSONResponse:
    models_loaded = getattr(request.app.state, "models_loaded", False)
    code = codes.CODE_AI_HEALTH_SUCCESS if models_loaded else codes.CODE_AI_HEALTH_NOT_READY
    http_status = 200 if models_loaded else 503
    data = schemas.HealthData(
        status="ok" if models_loaded else "starting",
        models_loaded=models_loaded,
    )
    body = schemas.Response(
        code=code,
        message="Service is healthy" if models_loaded else "Models not yet loaded",
        data=data,
    ).model_dump(exclude_none=True)
    return JSONResponse(status_code=http_status, content=body)
