"""Regex-based ID extraction for credential documents.

Built-in patterns ship with the service. Custom patterns can be loaded
from a file (one regex per line). Set OVERRIDE_BUILTIN_ID_PATTERNS=true
to skip built-ins entirely (custom-only mode).
"""

import re
from pathlib import Path

from app.config import settings

# Indonesian-specific patterns
PATTERN_NIK = re.compile(r"\b\d{16}\b")
# KTP / NIK = 16 digits
PATTERN_NPWP = re.compile(
    r"\b\d{2}[.\-]?\d{3}[.\-]?\d{3}[.\-]?\d{1}[.\-]?\d{3}[.\-]?\d{3}\b"
)
# NPWP = 15 digits, often dot/hyphen separated
PATTERN_NIP = re.compile(r"\b\d{18}\b")
# NIP (civil servant) = 18 digits
PATTERN_NIM = re.compile(r"\b\d{8,12}\b")
# NIM (student) = 8-12 digits

# 1. Hyphenated/underscored codes (e.g. UI-CS-2023-001234)
PATTERN_HYPHENATED_CODE = re.compile(
    r"\b[A-Za-z]{2,}[-_][A-Za-z0-9]+(?:[-_][A-Za-z0-9]+){0,3}\b"
)

# 2. Grouped alphanumeric codes with equal-length groups (e.g. 7G9K-2X8M-AB12)
PATTERN_GROUPED_ALNUM = re.compile(
    r"\b(?:"
    r"[A-Za-z0-9]{3}(?:-[A-Za-z0-9]{3}){1,5}"
    r"|[A-Za-z0-9]{4}(?:-[A-Za-z0-9]{4}){1,5}"
    r"|[A-Za-z0-9]{5}(?:-[A-Za-z0-9]{5}){1,5}"
    r"|[A-Za-z0-9]{6}(?:-[A-Za-z0-9]{6}){1,5}"
    r")\b"
)

# 3. Prefixed alphanumeric codes (e.g. IJZ20210042)
PATTERN_PREFIXED_ALNUM = re.compile(r"\b[A-Za-z]{2,6}\d{6,12}\b")

# 4. UUID (e.g. 550e8400-e29b-41d4-a716-446655440000)
PATTERN_UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)

# 5. ULID (e.g. 01ARZ3NDEKTSV4RRFFQ69G5FAV)
PATTERN_ULID = re.compile(
    r"\b[0-9A-HJKMNP-TV-Za-hjkmnp-tv-z]{26}\b"
)

BUILTIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    PATTERN_NIK,
    PATTERN_NPWP,
    PATTERN_NIP,
    PATTERN_NIM,
    PATTERN_HYPHENATED_CODE,
    PATTERN_GROUPED_ALNUM,
    PATTERN_PREFIXED_ALNUM,
    PATTERN_UUID,
    PATTERN_ULID,
)


def _load_custom_patterns() -> tuple[re.Pattern[str], ...]:
    """Read custom regex patterns from settings.custom_id_patterns_file.

    File format: one regex per line; blank lines and lines starting with '#'
    are ignored. Returns empty tuple if file doesn't exist. Raises
    re.error if any line has invalid regex (fail fast at module import).
    """
    path = Path(settings.custom_id_patterns_file)
    if not path.exists():
        return ()
    patterns: list[re.Pattern[str]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            patterns.append(re.compile(line))
        except re.error as exc:
            raise re.error(
                f"Invalid regex in {path}:{lineno}: {line!r} -- {exc}"
            ) from exc
    return tuple(patterns)


CUSTOM_PATTERNS: tuple[re.Pattern[str], ...] = _load_custom_patterns()

if settings.override_builtin_id_patterns:
    PATTERNS: tuple[re.Pattern[str], ...] = CUSTOM_PATTERNS
else:
    PATTERNS = (*CUSTOM_PATTERNS, *BUILTIN_PATTERNS)


def extract_ids(text: str) -> list[str]:
    """Extract all pattern-matching ID candidates from text.

    Returns deduplicated list, preserving text-position order (earliest
    occurrence first). Custom patterns take priority over built-ins via
    PATTERNS ordering.
    """
    if not text:
        return []
    matches: list[tuple[int, str]] = []
    for pattern in PATTERNS:
        for m in pattern.finditer(text):
            matches.append((m.start(), m.group()))
    matches.sort(key=lambda pair: pair[0])
    seen: set[str] = set()
    out: list[str] = []
    for _, value in matches:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
