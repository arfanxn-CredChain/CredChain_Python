"""Verdict mapping for similarity-based document verification.

Thresholds are configurable via env vars with sensible defaults.
Counter-intuitively, very high similarity (>=0.95) implies "tampered",
because authentic re-issued documents always have natural OCR variance.
"""

from app.config import settings


def verdict_for(similarity: float) -> str:
    if similarity >= settings.verdict_tampered_threshold:
        return "tampered"
    if similarity >= settings.verdict_suspicious_threshold:
        return "suspicious"
    if similarity >= settings.verdict_low_similarity_threshold:
        return "low_similarity"
    return "not_similar"


def format_percent(similarity: float) -> str:
    return f"{similarity * 100:.1f}%"
