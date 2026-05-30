"""Build bilingual verify descriptions from locale templates."""

from app.i18n import localize
from app.schemas import FieldComparisonEntry

SUPPORTED_LANGS = ("id", "en")


def build_description(
    verdict: str,
    score: float,
    similarity_percent: str,
    field_comparison: dict[str, FieldComparisonEntry],
) -> dict[str, str]:
    """Render bilingual description for a verify result using locale templates.

    Returns {"id": "...", "en": "..."} — no LLM involved.
    Field names are kept as extracted (no translation).
    Empty lists render as "-" to avoid trailing colons in templates.
    """
    matched = [k for k, v in field_comparison.items() if v.match]
    mismatched = [k for k, v in field_comparison.items() if not v.match]
    total = len(field_comparison)
    key = f"verdict.{verdict.lower()}"
    fmt = {
        "percent": similarity_percent,
        "matched": ", ".join(matched) if matched else "-",
        "mismatched": ", ".join(mismatched) if mismatched else "-",
        "match_count": len(matched),
        "total_count": total,
    }
    return {lang: localize(key, lang, **fmt) for lang in SUPPORTED_LANGS}
