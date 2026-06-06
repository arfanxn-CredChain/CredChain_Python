"""EmbeddingGemma sentence-embedding wrapper + cosine similarity helper.

Uses google/embeddinggemma-300M via sentence-transformers.
"""

import math
from typing import TYPE_CHECKING

import numpy as np

from app import codes
from app.errors import AppError

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


def encode(model: "SentenceTransformer", text: str) -> list[float]:
    if not text or not text.strip():
        raise AppError(codes.CODE_AI_INTERNAL, message="Cannot encode empty text")
    max_seq = int(getattr(model, "max_seq_length", 512) or 512)
    word_count = len(text.split())
    if word_count > max_seq:
        import logging as _logging
        _logging.getLogger("embeddings").warning(
            "text may exceed max_seq_length and will be truncated: "
            "word_count=%d max_seq=%d", word_count, max_seq,
        )
    arr = model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
    if isinstance(arr, np.ndarray):
        return [float(x) for x in arr.tolist()]
    return [float(x) for x in arr]  # type: ignore[unreachable]


def cosine_similarity(a: list[float], b: list[float]) -> float:
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
