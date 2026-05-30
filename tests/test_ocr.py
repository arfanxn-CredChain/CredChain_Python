from unittest.mock import MagicMock, patch

import pytest

from app import ocr
from app.errors import AppError


def test_is_text_useful_empty_string():
    assert ocr.is_text_useful("") is False


def test_is_text_useful_whitespace_only():
    assert ocr.is_text_useful("   \n\t  ") is False


def test_is_text_useful_short_text_below_min_chars():
    assert ocr.is_text_useful("short") is False


def test_is_text_useful_long_clean_text():
    text = "This is a perfectly clean line of credential text. " * 5
    assert ocr.is_text_useful(text) is True


def test_is_text_useful_low_printable_ratio():
    text = "a" * 50 + "\x00" * 200
    assert ocr.is_text_useful(text) is False


def test_is_text_useful_unicode_ascii_mix():
    text = "Sertifikat Bachelor of Science untuk John Doe nomor 12345 tanggal 2024."
    assert ocr.is_text_useful(text) is True


def test_extract_text_image_uses_easyocr_directly():
    reader = MagicMock()
    reader.readtext.return_value = [
        ([[0, 0], [10, 0], [10, 10], [0, 10]], "Hello", 0.99),
        ([[0, 20], [10, 20], [10, 30], [0, 30]], "World", 0.98),
    ]
    text = ocr.extract_text(reader, b"\xff\xd8\xff\xe0fakejpegbytes", "image/jpeg")
    assert "Hello" in text
    assert "World" in text
    reader.readtext.assert_called_once()


def test_extract_text_pdf_with_useful_text_skips_easyocr():
    reader = MagicMock()
    long_text = "This document contains substantial readable text. " * 5
    fake_doc = MagicMock()
    fake_page = MagicMock()
    fake_page.get_text.return_value = long_text
    fake_doc.__iter__.return_value = iter([fake_page])
    fake_doc.__enter__.return_value = fake_doc
    fake_doc.__exit__.return_value = False
    with patch("app.ocr.fitz.open", return_value=fake_doc):
        text = ocr.extract_text(reader, b"%PDF-1.4 fakebytes", "application/pdf")
    assert long_text.strip() in text
    reader.readtext.assert_not_called()


def test_extract_text_pdf_with_unusable_text_falls_back_to_easyocr():
    reader = MagicMock()
    reader.readtext.return_value = [
        ([[0, 0], [1, 0], [1, 1], [0, 1]], "FallbackText", 0.95),
    ]
    fake_pix = MagicMock()
    fake_pix.tobytes.return_value = b"\x89PNGfake"
    fake_page = MagicMock()
    fake_page.get_text.return_value = ""
    fake_page.get_pixmap.return_value = fake_pix
    fake_doc = MagicMock()
    fake_doc.__iter__.return_value = iter([fake_page])
    fake_doc.__enter__.return_value = fake_doc
    fake_doc.__exit__.return_value = False
    with patch("app.ocr.fitz.open", return_value=fake_doc):
        text = ocr.extract_text(reader, b"%PDF-1.4 scanned", "application/pdf")
    assert "FallbackText" in text
    reader.readtext.assert_called_once()


def test_extract_text_unsupported_mime_raises():
    reader = MagicMock()
    with pytest.raises(AppError):
        ocr.extract_text(reader, b"data", "application/zip")
