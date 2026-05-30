"""Tests for app/id_extractor.py — regex-based ID extraction."""

import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.id_extractor import BUILTIN_PATTERNS, _load_custom_patterns, extract_ids


def test_empty_string_returns_empty():
    assert extract_ids("") == []


def test_no_matches_returns_empty():
    assert extract_ids("hello world this is plain prose") == []


def test_indonesian_nik_16_digits():
    text = "NIK: 3171012345678901 ditulis di bawah"
    out = extract_ids(text)
    assert "3171012345678901" in out


def test_indonesian_nip_18_digits():
    text = "NIP. 198501012010012003 sebagai pengajar"
    out = extract_ids(text)
    assert "198501012010012003" in out


def test_indonesian_nim_short():
    text = "Mahasiswa nomor 2019051234 lulus"
    out = extract_ids(text)
    assert "2019051234" in out


def test_credential_full_text():
    text = (
        "UNIVERSITAS INDONESIA\n"
        "Name: John Doe Pratama\n"
        "Student Number: 2019051234\n"
        "Date of Birth: 1998-05-15\n"
        "Date Issued: 2023-07-20\n"
        "Certificate ID: UI-CS-2023-001234\n"
        "Registration Number: REG-IJZ-2023-051234\n"
        "Verification Code: 7G9K-2X8M-AB12\n"
    )
    out = extract_ids(text)
    assert "2019051234" in out
    assert "UI-CS-2023-001234" in out
    assert "REG-IJZ-2023-051234" in out
    assert "7G9K-2X8M-AB12" in out


def test_hyphenated_code_pattern():
    text = "Cert ID: ABC-XYZ-2024-9876"
    out = extract_ids(text)
    assert "ABC-XYZ-2024-9876" in out


def test_grouped_alnum_pattern():
    text = "Code: 7G9K-2X8M-AB12 valid"
    out = extract_ids(text)
    assert "7G9K-2X8M-AB12" in out


def test_prefixed_alnum_pattern():
    text = "ID IJZ20210042 issued"
    out = extract_ids(text)
    assert "IJZ20210042" in out


def test_uuid_pattern():
    text = "Reference: 550e8400-e29b-41d4-a716-446655440000 stored"
    out = extract_ids(text)
    assert "550e8400-e29b-41d4-a716-446655440000" in out


def test_dedupe_across_patterns():
    text = "ID 2019051234 and again 2019051234"
    out = extract_ids(text)
    assert out.count("2019051234") == 1


def test_preserves_order():
    text = "First UI-CS-2023-001 then 2019051234 then 7G9K-2X8M-AB12"
    out = extract_ids(text)
    idx_first = out.index("UI-CS-2023-001")
    idx_nim = out.index("2019051234")
    idx_grouped = out.index("7G9K-2X8M-AB12")
    assert idx_first < idx_nim
    assert idx_nim < idx_grouped


def test_ulid_pattern_matches():
    text = "Reference: 01ARZ3NDEKTSV4RRFFQ69G5FAV stored"
    out = extract_ids(text)
    assert "01ARZ3NDEKTSV4RRFFQ69G5FAV" in out


def test_load_custom_patterns_from_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_file = Path(tmpdir) / "patterns.txt"
        custom_file.write_text(
            "# Custom institution patterns\n"
            r"\bSTU-\d{6}\b" + "\n"
            "\n"
            r"\bMRN-\d{8}\b" + "\n"
        )
        with patch("app.id_extractor.settings.custom_id_patterns_file", str(custom_file)):
            patterns = _load_custom_patterns()
    assert len(patterns) == 2


def test_load_custom_patterns_invalid_regex_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        custom_file = Path(tmpdir) / "bad.txt"
        custom_file.write_text("[unclosed_bracket\n")
        patch_path = "app.id_extractor.settings.custom_id_patterns_file"
        with patch(patch_path, str(custom_file)), pytest.raises(re.error):
            _load_custom_patterns()


def test_missing_custom_file_returns_empty_tuple():
    with patch("app.id_extractor.settings.custom_id_patterns_file", "/nonexistent_file.txt"):
        patterns = _load_custom_patterns()
    assert patterns == ()


def test_builtin_patterns_count():
    assert len(BUILTIN_PATTERNS) == 9


def test_extract_ids_with_custom_pattern_monkeypatched(monkeypatch):
    import app.id_extractor as ix
    custom = (re.compile(r"\bSTU-\d{6}\b"),)
    monkeypatch.setattr(ix, "PATTERNS", custom)
    out = ix.extract_ids("Student STU-123456 enrolled")
    assert "STU-123456" in out
    assert len(out) == 1


def test_npwp_dotted_format():
    text = "NPWP: 12.345.678.9-012.345 wajib pajak"
    out = extract_ids(text)
    assert any("12" in s and "345" in s for s in out)
