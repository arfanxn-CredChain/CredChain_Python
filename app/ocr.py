"""OCR orchestration: PyMuPDF for digital PDFs, EasyOCR fallback for
image-only PDFs and standalone images."""

import string
from typing import TYPE_CHECKING

import fitz

from app import codes
from app.errors import AppError

if TYPE_CHECKING:
    import easyocr

MIN_USEFUL_TEXT_CHARS = 50
MIN_PRINTABLE_RATIO = 0.80
MAX_PDF_PAGES = 50
MAX_OCR_TEXT_LENGTH = 200_000

PDF_MIME = "application/pdf"
IMAGE_MIMES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
})

_PRINTABLE = set(string.printable)


def is_text_useful(text: str) -> bool:
    """Decide whether PyMuPDF-extracted text is high-quality enough to
    skip the EasyOCR fallback.

    Both criteria must hold:
      1. Stripped length >= MIN_USEFUL_TEXT_CHARS
      2. Ratio of printable characters >= MIN_PRINTABLE_RATIO

    Edge cases:
      - Empty string returns False (length check fails)
      - Whitespace-only returns False (length check after strip fails)
      - Documents with embedded broken fonts produce control codes that
        fail the printable ratio (criterion 2)
    """
    stripped = text.strip()
    if len(stripped) < MIN_USEFUL_TEXT_CHARS:
        return False
    printable_count = sum(1 for ch in stripped if ch in _PRINTABLE)
    ratio = printable_count / len(stripped)
    return ratio >= MIN_PRINTABLE_RATIO


def extract_text(
    reader: "easyocr.Reader", file_bytes: bytes, mime_type: str
) -> str:
    """Extract text from a credential document.

    Strategy:
      - PDF: try PyMuPDF text extraction first; if is_text_useful is
        False, render each page to a PNG and run EasyOCR.
      - Supported image: run EasyOCR directly on the bytes.
      - Anything else: raise AppError(CODE_AI_EXTRACT_OCR_FAILED).

    Returns the concatenated extracted text. Whitespace is normalized
    by joining EasyOCR fragments with single spaces.
    """
    if mime_type == PDF_MIME:
        return _extract_from_pdf(reader, file_bytes)
    if mime_type in IMAGE_MIMES:
        return _easyocr_to_text(reader, file_bytes)
    raise AppError(
        codes.CODE_AI_EXTRACT_OCR_FAILED,
        message=f"Unsupported MIME type: {mime_type}",
    )


def _extract_from_pdf(reader: "easyocr.Reader", file_bytes: bytes) -> str:
    direct_chunks: list[str] = []
    fallback_chunks: list[str] = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page_num, page in enumerate(doc):
            if page_num >= MAX_PDF_PAGES:
                break
            page_text = page.get_text() or ""
            if is_text_useful(page_text):
                direct_chunks.append(page_text)
            else:
                pix = page.get_pixmap()
                png_bytes = pix.tobytes("png")
                fallback_chunks.append(_easyocr_to_text(reader, png_bytes))
    if direct_chunks and not fallback_chunks:
        return "\n".join(direct_chunks).strip()[:MAX_OCR_TEXT_LENGTH]
    return "\n".join([*direct_chunks, *fallback_chunks]).strip()[:MAX_OCR_TEXT_LENGTH]


def _easyocr_to_text(reader: "easyocr.Reader", image_bytes: bytes) -> str:
    fragments = reader.readtext(image_bytes)
    return " ".join(frag[1] for frag in fragments).strip()[:MAX_OCR_TEXT_LENGTH]
