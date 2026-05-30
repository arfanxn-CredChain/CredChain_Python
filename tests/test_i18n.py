"""Tests for app/i18n.py — locale loader and localizer."""

import re

import pytest

from app import i18n


def test_load_locales_loads_id_and_en():
    assert "id" in i18n._LOCALES
    assert "en" in i18n._LOCALES


def test_both_files_have_same_keys():
    id_keys = set(i18n._LOCALES["id"].keys())
    en_keys = set(i18n._LOCALES["en"].keys())
    assert id_keys == en_keys, f"Drift: id-only={id_keys-en_keys} en-only={en_keys-id_keys}"


def test_all_4_verdict_keys_present():
    expected_keys = {
        "verdict.tampered",
        "verdict.suspicious",
        "verdict.low_similarity",
        "verdict.not_similar",
    }
    assert expected_keys <= set(i18n._LOCALES["id"].keys())
    assert expected_keys <= set(i18n._LOCALES["en"].keys())


def test_placeholders_are_known():
    known = {"percent", "matched", "mismatched", "match_count", "total_count"}
    pattern = re.compile(r"\{(\w+)\}")
    for lang in ("id", "en"):
        for key, template in i18n._LOCALES[lang].items():
            placeholders = set(pattern.findall(template))
            unknown = placeholders - known
            assert not unknown, f"{lang}/{key}: unknown placeholders {unknown}"


def test_localize_returns_formatted_string():
    out = i18n.localize(
        "verdict.tampered", "id",
        percent="91.0%",
        matched="name, year",
        mismatched="dob",
        match_count=2,
        total_count=3,
    )
    assert "91.0%" in out
    assert "name, year" in out
    assert "TAMPERED" in out


def test_localize_unknown_lang_raises():
    with pytest.raises(KeyError):
        i18n.localize("verdict.tampered", "fr",
                      percent="0%", matched="-", mismatched="-",
                      match_count=0, total_count=0)


def test_localize_unknown_key_raises():
    with pytest.raises(KeyError):
        i18n.localize("verdict.unknown", "id",
                      percent="0%", matched="-", mismatched="-",
                      match_count=0, total_count=0)
