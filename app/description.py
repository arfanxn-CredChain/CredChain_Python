"""Build bilingual verify descriptions from locale templates."""

from app.i18n import localize

SUPPORTED_LANGS = ("id", "en")


def build_description(verdict: str, similarity_percent: str) -> dict[str, str]:
    """Render bilingual description for a verify result using locale templates.

    Returns {"id": "...", "en": "..."} — no LLM involved.
    """
    key = f"verdict.{verdict.lower()}"
    fmt = {"percent": similarity_percent}
    return {lang: localize(key, lang, **fmt) for lang in SUPPORTED_LANGS}
