"""Field-level fuzzy comparison and verdict mapping.

Two-phase comparison:
  Phase 1 (key matching):    stored key -> closest uploaded key by
                             rapidfuzz.fuzz.token_sort_ratio.
  Phase 2 (value matching):  matched key pair -> compared by
                             rapidfuzz.fuzz.partial_ratio.

Verdict thresholds map a cosine similarity in [0, 1] to a label.
Counter-intuitively, very high similarity (>=0.95) implies TAMPERED,
because authentic re-issued documents always have natural OCR variance.
"""

from rapidfuzz import fuzz

from app.schemas import FieldComparisonEntry

KEY_MATCH_THRESHOLD = 80
VALUE_MATCH_THRESHOLD = 85

VERDICT_TAMPERED_MIN = 0.95
VERDICT_SUSPICIOUS_MIN = 0.75
VERDICT_LOW_SIMILARITY_MIN = 0.40


def verdict_for(similarity: float) -> str:
    """Map a cosine similarity in [-1, 1] to one of four verdicts.

    Negative values clamp to NOT_SIMILAR. The 0.95+ band is TAMPERED
    (suspected copy/paste); 0.75-0.94 is SUSPICIOUS; 0.40-0.74 is
    LOW_SIMILARITY; below 0.40 is NOT_SIMILAR.
    """
    if similarity >= VERDICT_TAMPERED_MIN:
        return "TAMPERED"
    if similarity >= VERDICT_SUSPICIOUS_MIN:
        return "SUSPICIOUS"
    if similarity >= VERDICT_LOW_SIMILARITY_MIN:
        return "LOW_SIMILARITY"
    return "NOT_SIMILAR"


def format_percent(similarity: float) -> str:
    """Format a 0-1 similarity as a one-decimal percent string."""
    return f"{similarity * 100:.1f}%"


def compare_fields(
    stored: dict[str, str],
    uploaded: dict[str, str],
) -> dict[str, FieldComparisonEntry]:
    """Compare stored vs uploaded extracted fields.

    For each stored key, find the best uploaded key match by
    token_sort_ratio. If the match score >= KEY_MATCH_THRESHOLD, pair
    them and compare values by partial_ratio against
    VALUE_MATCH_THRESHOLD. Each uploaded key is consumed at most once
    so two stored keys cannot share the same uploaded match.

    Returns a dict keyed by the stored field name.
    """
    result: dict[str, FieldComparisonEntry] = {}
    available_uploaded_keys: list[str] = list(uploaded.keys())

    for stored_key, stored_value in stored.items():
        match_key = _best_key_match(stored_key, available_uploaded_keys)
        if match_key is None:
            result[stored_key] = FieldComparisonEntry(
                stored=stored_value, uploaded="", match=False
            )
            continue
        uploaded_value = uploaded[match_key]
        available_uploaded_keys.remove(match_key)
        value_score = fuzz.partial_ratio(stored_value, uploaded_value)
        result[stored_key] = FieldComparisonEntry(
            stored=stored_value,
            uploaded=uploaded_value,
            match=value_score >= VALUE_MATCH_THRESHOLD,
        )
    return result


def _best_key_match(stored_key: str, candidates: list[str]) -> str | None:
    best_key: str | None = None
    best_score = 0.0
    stored_normalized = stored_key.replace("_", " ")
    for cand in candidates:
        cand_normalized = cand.replace("_", " ")
        score = fuzz.token_set_ratio(stored_normalized, cand_normalized)
        if score > best_score:
            best_score = score
            best_key = cand
    if best_score >= KEY_MATCH_THRESHOLD:
        return best_key
    return None
