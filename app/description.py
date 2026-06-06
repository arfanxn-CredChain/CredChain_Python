"""Build single-language verify descriptions from locale templates.

Language is resolved via i18n middleware (Accept-Language header).
Defaults to Indonesian ("id") when language is not recognized.
"""

from app.i18n import localize

SUPPORTED_LANGS = ("id", "en")


def build_description(verdict: str, similarity_percent: str, lang: str) -> str:
    key = f"verdict.{verdict.lower()}"
    fmt = {"percent": similarity_percent}
    resolved_lang = lang if lang in SUPPORTED_LANGS else "id"
    return localize(key, resolved_lang, **fmt)
