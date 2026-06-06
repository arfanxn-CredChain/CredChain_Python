"""Verdict mapping for similarity-based document verification.

Verdict thresholds map a cosine similarity in [-1, 1] to a lowercase label.
Counter-intuitively, very high similarity (>=0.95) implies "tampered",
because authentic re-issued documents always have natural OCR variance.
"""

VERDICT_TAMPERED_MIN = 0.95
VERDICT_SUSPICIOUS_MIN = 0.75
VERDICT_LOW_SIMILARITY_MIN = 0.40


def verdict_for(similarity: float) -> str:
    """Map a cosine similarity in [-1, 1] to one of four lowercase verdicts.

    Negative values clamp to "not_similar". The 0.95+ band is "tampered"
    (suspected copy/paste); 0.75-0.94 is "suspicious"; 0.40-0.74 is
    "low_similarity"; below 0.40 is "not_similar".
    """
    if similarity >= VERDICT_TAMPERED_MIN:
        return "tampered"
    if similarity >= VERDICT_SUSPICIOUS_MIN:
        return "suspicious"
    if similarity >= VERDICT_LOW_SIMILARITY_MIN:
        return "low_similarity"
    return "not_similar"


def format_percent(similarity: float) -> str:
    """Format a 0-1 similarity as a one-decimal percent string."""
    return f"{similarity * 100:.1f}%"
