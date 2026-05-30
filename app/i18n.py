"""Locale loader + localizer for CredChain Python service.

Mirrors the Go backend's locales/{en,id}.json pattern. Templates use
Python str.format placeholders like {percent}, {matched}, etc.
"""

import json
from pathlib import Path
from typing import Any

from app.config import settings

_LOCALES: dict[str, dict[str, str]] = {}


def _load_locales() -> None:
    """Load all *.json files in settings.locales_dir into _LOCALES.

    Called once at module import. Maps language code (e.g., 'id', 'en')
    to a dict of key -> template string.
    """
    locales_path = Path(settings.locales_dir)
    if not locales_path.exists():
        return
    for json_file in locales_path.glob("*.json"):
        lang = json_file.stem
        with open(json_file, encoding="utf-8") as f:
            _LOCALES[lang] = json.load(f)


def localize(key: str, lang: str, **vars: Any) -> str:
    """Return the localized template for `key` in `lang`, formatted with `vars`.

    Raises KeyError if the language or key is missing. Raises KeyError if a
    template placeholder is not provided in `vars`. These are programmer
    errors, not user-facing — test_i18n.py validates locale files at test
    time so production never sees them.
    """
    template = _LOCALES[lang][key]
    return template.format(**vars)


_load_locales()
