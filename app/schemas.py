"""Pydantic request/response models for every endpoint."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """Unified API response envelope. Mirrors Go's response.Response[T]."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    code: int
    message: str
    data: T | None = None
    errors: dict[str, list[str]] | None = None


class ExtractData(BaseModel):
    """Payload returned from POST /extract."""

    raw_text: str
    embeddings: list[float]
    extracted_fields: dict[str, str]


class FieldComparisonEntry(BaseModel):
    """Single stored-vs-uploaded field comparison row."""

    stored: str
    uploaded: str
    match: bool


class VerifyDescription(BaseModel):
    """Bilingual natural-language summary of the verify result."""

    id: str
    en: str


class VerifyProcessing(BaseModel):
    """Processing metadata for the verify response."""

    ocr_char_count: int
    model_used: str


class VerifyData(BaseModel):
    """Payload returned from POST /verify."""

    similarity_score: float
    similarity_percent: str
    verdict: str
    description: VerifyDescription
    field_comparison: dict[str, FieldComparisonEntry]
    processing: VerifyProcessing


class VerifyMetadataItem(BaseModel):
    """Single item in the /verify metadata array.

    Pairs positionally with files[i] in multipart upload.
    """

    stored_embeddings: list[float]
    stored_fields: dict[str, str]


class ExtractIdsData(BaseModel):
    """Payload returned from POST /extract-ids."""

    raw_text: str
    potential_ids: list[str]


class HealthData(BaseModel):
    """Payload returned from GET /health."""

    status: str
    models_loaded: bool
