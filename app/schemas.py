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
    text: str
    ids: list[dict[str, str]]
    embedding: list[float]


class VerifyData(BaseModel):
    """Payload returned from POST /verify. Descriptions are bilingual {en, id}."""
    similarity_score: float
    similarity_percent: str
    verdict: str
    descriptions: dict[str, str]


class ExtractIdsData(BaseModel):
    """Payload returned from POST /extract-ids. ID-only, no raw_text."""
    ids: list[dict[str, str]]
