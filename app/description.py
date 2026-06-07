"""Build bilingual verify descriptions from locale templates.

Always returns both English and Indonesian descriptions — no language
selection needed. Rendered from locales/{en,id}.json templates.
"""

from app.i18n import localize


def build_description(verdict: str, similarity_percent: str) -> dict[str, str]:
    key = f"verdict.{verdict.lower()}"
    fmt = {"percent": similarity_percent}
    return {
        "en": localize(key, "en", **fmt),
        "id": localize(key, "id", **fmt),
    }
