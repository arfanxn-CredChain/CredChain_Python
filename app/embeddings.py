"""LaBSE sentence-embedding wrapper + cosine similarity helper."""

import math
from typing import TYPE_CHECKING

from app import codes
from app.errors import AppError

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


def encode(model: "SentenceTransformer", text: str) -> list[float]:
    """Encode text into a single document-level LaBSE embedding.

    Args:
        model: pre-loaded SentenceTransformer (LaBSE).
        text: OCR-extracted document text. Must be non-empty.

    Returns:
        Plain Python list of 768 floats. Model is configured to L2-normalize
        the output so cosine similarity is just a dot product downstream.

    Raises:
        AppError(CODE_AI_INTERNAL) if text is empty.
    """
    if not text or not text.strip():
        raise AppError(codes.CODE_AI_INTERNAL, message="Cannot encode empty text")
    arr = model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
    return [float(x) for x in arr.tolist()]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns a value in [-1, 1]. If either vector has zero magnitude, the
    similarity is defined as 0 (avoid division by zero).
    """
    if len(a) != len(b):
        raise AppError(
            codes.CODE_AI_INTERNAL,
            message=f"Vector length mismatch: {len(a)} vs {len(b)}",
        )
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
