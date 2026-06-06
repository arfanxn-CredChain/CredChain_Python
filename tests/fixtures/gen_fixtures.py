"""Generate all test fixture files for CredChain Python integration tests.

Single invocation generates 237 bulk fixtures:
  - 60 diplomas, 60 certificates, 60 transcripts, 57 edge cases
  - 4 formats per index: PDF, JPG, PNG, TIFF (except edge case 10: .txt)

All generated files are gitignored. Run after clone.

Usage: python tests/fixtures/gen_fixtures.py
"""

import os
from pathlib import Path
import random
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FIXTURES_DIR = Path(__file__).parent


# ── helpers ──

def _pdf_add_text(page: fitz.Page, lines: list[tuple[str, int, int, bool]]) -> None:
    for text, x, y, bold in lines:
        if not text:
            continue
        page.insert_text(
            (x, y), text,
            fontsize=14 if bold else 11,
            fontname="hebo" if bold else "helv",
        )


def _make_credential_image(
    title: str,
    fields: list[tuple[str, str]],
    size: tuple[int, int] = (600, 420),
) -> Image.Image:
    img = Image.new("RGB", size, color=(255, 255, 255))

    # B: paper grain — subtle random noise to simulate real photographed paper
    pixels = img.load()
    for _ in range(size[0] * size[1] // 4):
        x = random.randrange(0, size[0])
        y = random.randrange(0, size[1])
        g = random.randint(242, 254)
        pixels[x, y] = (g, g, g)

    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        font_body = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except OSError:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
    draw.text((40, 30), title, fill=(0, 0, 0), font=font_title)
    draw.line([(40, 75), (size[0] - 40, 75)], fill=(0, 0, 0), width=2)
    y = 105
    for label, value in fields:
        draw.text((40, y), f"{label}: {value}", fill=(0, 0, 0), font=font_body)
        y += 38
    # B: subtle blur to simulate camera focus
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
    return img


# ── data pools ──

NAMES = [
    "Alice Chen", "Bima Pratama", "Carlos Vega", "Dewi Sartika", "Eko Wijoyo",
    "Fatima Zahra", "Gunawan Lim", "Hana Park", "Irfan Malik", "Julia Tan",
    "Kevin O'Brien", "Lina Marlina", "Muhammad Ali", "Nina Susanti", "Oscar Diaz",
]

INSTITUTIONS = [
    "Universitas Indonesia", "Institut Teknologi Bandung", "Universitas Gadjah Mada",
    "Universitas Airlangga", "Universitas Diponegoro", "Universitas Brawijaya",
    "Universitas Padjadjaran", "Universitas Hasanuddin", "Universitas Sumatera Utara",
    "Universitas Sebelas Maret", "University of Oxford", "Université Paris-Saclay",
    "Technical University of Munich", "University of Tokyo", "National University of Singapore",
]

PROGRAMS = [
    "Ilmu Komputer", "Teknik Informatika", "Sistem Informasi", "Teknik Elektro",
    "Manajemen", "Akuntansi", "Hukum", "Kedokteran", "Teknik Sipil", "Arsitektur",
    "Computer Science", "Data Science", "Software Engineering", "Information Systems",
    "Electrical Engineering",
]

NIKS = [
    "2019051234", "2018030567", "2020012345", "2021056789", "2017078901",
    "2022123456", "2019098765", "2021032109", "2018543210", "2020065432",
    "2022109876", "2019112233", "2020443321", "2021556677", "2018778899",
]

DATES = [
    "15 Mei 1998", "22 Maret 1997", "3 Agustus 1999", "10 Januari 2000",
    "28 September 1996", "5 Februari 2001", "19 November 1995", "7 Juli 2002",
    "12 April 1994", "30 Oktober 2003", "March 15, 1998", "22 March 1997",
    "3 August 1999", "10 January 2000", "28 September 1996",
]

DIPLOMA_IDS = [
    "UI-DIP-001-2345", "ITB-DIP-002-6789", "UGM-DIP-003-1234", "UNAIR-DIP-004-5678",
    "UNDIP-DIP-005-9012", "UB-DIP-006-3456", "UNPAD-DIP-007-7890", "UNHAS-DIP-008-2345",
    "USU-DIP-009-6789", "UNS-DIP-010-1234", "OXF-DIP-011-5678", "UPS-DIP-012-9012",
    "TUM-DIP-013-3456", "UTOK-DIP-014-7890", "NUS-DIP-015-2345",
]

CERT_IDS = [
    "CCA-001-ABCD", "CCA-002-EFGH", "CCA-003-IJKL", "CCA-004-MNOP", "CCA-005-QRST",
    "CCA-006-UVWX", "CCA-007-YZAB", "CCA-008-CDEF", "CCA-009-GHIJ", "CCA-010-KLMN",
    "CCA-011-OPQR", "CCA-012-STUV", "CCA-013-WXYZ", "CCA-014-ABCD", "CCA-015-EFGH",
]

TRANS_IDS = [
    "TR-UI-001-2345", "TR-ITB-002-6789", "TR-UGM-003-1234", "TR-UNAIR-004-5678",
    "TR-UNDIP-005-9012", "TR-UB-006-3456", "TR-UNPAD-007-7890", "TR-UNHAS-008-2345",
    "TR-USU-009-6789", "TR-UNS-010-1234", "TR-OXF-011-5678", "TR-UPS-012-9012",
    "TR-TUM-013-3456", "TR-UTOK-014-7890", "TR-NUS-015-2345",
]

# ── bulk diploma data builder ──

def _diploma_data(i: int) -> tuple[str, list]:
    title = f"IJAZAH SARJANA - {INSTITUTIONS[i]}"
    ipk = f"{3.0 + i * 0.06:.2f}"
    fields = [
        ("Nama", NAMES[i]),
        ("NIM", NIKS[i]),
        ("Program Studi", PROGRAMS[i]),
        ("IPK", ipk),
        ("Tanggal Terbit", DATES[i]),
        ("Nomor Ijazah", DIPLOMA_IDS[i]),
    ]
    return title, fields


# ── bulk certificate data builder ──

def _certificate_data(i: int) -> tuple[str, list]:
    title = f"SERTIFIKAT KOMPETENSI - {INSTITUTIONS[i]}"
    fields = [
        ("Nama", NAMES[i]),
        ("Nomor Sertifikat", CERT_IDS[i]),
        ("Kompetensi", PROGRAMS[i]),
        ("Tanggal Terbit", DATES[i]),
        ("Kode Verifikasi", f"CERT-{NIKS[i]}"),
    ]
    return title, fields


# ── bulk transcript data builder ──

def _transcript_data(i: int) -> tuple[str, list]:
    title = f"TRANSKRIP AKADEMIK - {INSTITUTIONS[i]}"
    ipk = f"{3.2 + i * 0.04:.2f}"
    fields = [
        ("Nama", NAMES[i]),
        ("NIM", NIKS[i]),
        ("Program Studi", PROGRAMS[i]),
        ("IPK Kumulatif", ipk),
        ("Total SKS", str(144)),
        ("Nomor Transkrip", TRANS_IDS[i]),
    ]
    return title, fields


# ── edge case data builder ──

def _edgecase_data(i: int) -> tuple[str, list] | tuple[str, None]:
    """Return (title, fields_or_None). None fields means generate empty/1x1."""
    d1_title, d1_fields = _diploma_data(0)  # "IJAZAH SARJANA - Universitas Indonesia"

    edge_types = [
        ("Empty", None),                                             # 1
        ("Minimal", [("Nama", "A")]),                                # 2
        ("Blurry", d1_fields),                                       # 3 — blurred version of d1
        ("Tampered", d1_fields.copy()),                              # 4
            
        ("Arabic", [("الاسم", "أحمد محمد"),                          # 5
                     ("الرقم", "2023001")]),
        ("Rotated", [("Nama", NAMES[2]), ("NIM", NIKS[2])]),         # 6
        ("Suspicious", [("Nama", "Modified User"),                   # 7
                        ("NIM", NIKS[0]), ("Program Studi", PROGRAMS[0]),
                        ("Instansi", INSTITUTIONS[0])]),
        ("LowSimilar", [("Name", "Unknown Student"),                 # 8
                        ("Institute", "Unknown University"),
                        ("Program", "General Studies")]),
        ("NotSimilar", [("MENU", "Soto Ayam - Rp 25,000"),           # 9
                        ("MENU", "Nasi Goreng - Rp 20,000"),
                        ("MENU", "Mie Ayam - Rp 18,000")]),
        ("LargeText", None),                                           # 10 — bad MIME (.txt) 
        ("SmallImage", [("Nama", NAMES[3])]),                        # 11
        ("Chinese", [("姓名", "张伟"),                                # 12
                      ("学号", "2023001"),
                      ("专业", "计算机科学")]),
        ("Noisy", [("Nama", NAMES[4]), ("NIM", NIKS[4])]),           # 13
        ("NumericOnly", [("3171012345678901", "1234567890"),          # 14
                         ("ABC-12345-XYZ", "DEF-67890-UVW")]),
        ("Stamps", [("Nama", NAMES[5]), ("NIM", NIKS[5])]),           # 15
    ]

    # Override specific fields for tampered/suspicious
    result = list(edge_types[i])
    if i == 3:  # Tampered: same as d1 but change 1 digit
        result[0] = d1_title
        tampered = [(k, v) for k, v in d1_fields]
        # Change IPK from 3.00 to 3.01 (1-digit change)
        tampered[3] = (tampered[3][0], "3.01")
        result[1] = tampered
    elif i == 2:  # Blurry: use d1 title
        result[0] = d1_title
    elif i == 6:  # Suspicious: d1 structure, only name differs
        result[0] = d1_title
        suspicious = [(k, v) for k, v in d1_fields]
        suspicious[0] = ("Nama", "Modified Person")  # change name only
        result[1] = suspicious

    return tuple(result)


# ── bulk generators ──

def _save_all_formats(filepath: str, title: str, fields: list | None,
                      pdf_lines: list[tuple] | None = None,
                      size: tuple = (800, 600),
                      blur: bool = False, rotate: int = 0,
                      noisy: bool = False, stamps: bool = False) -> None:
    """Save all 4 format files (PDF, JPG, PNG, TIFF) with optional effects."""
    stem = FIXTURES_DIR / filepath

    if fields is None:
        (stem.with_suffix(".pdf")).write_bytes(b"")
        img = Image.new("RGB", (1, 1), color=(255, 255, 255))
        for ext in [".jpg", ".png", ".tiff"]:
            img.save(stem.with_suffix(ext))
        return

    if pdf_lines:
        doc = fitz.open()
        page = doc.new_page(width=612, height=792)
        _pdf_add_text(page, pdf_lines)
        doc.save(str(stem.with_suffix(".pdf")))
        doc.close()
    else:
        (stem.with_suffix(".pdf")).write_bytes(b"")

    img = _make_credential_image(title, fields, size=size)

    if rotate:
        img = img.rotate(rotate, expand=True, fillcolor=(255, 255, 255))
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=3))
    if noisy:
        pixels = img.load()
        for _ in range(5000):
            x = random.randrange(0, img.width)
            y = random.randrange(0, img.height)
            pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
    if stamps:
        stamp = Image.new("RGBA", (150, 60), (255, 0, 0, 50))
        stamp_draw = ImageDraw.Draw(stamp)
        try:
            f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except OSError:
            f = ImageFont.load_default()
        stamp_draw.text((10, 15), "VERIFIED", fill=(200, 0, 0), font=f)
        img.paste(stamp, (img.width - 180, img.height - 80), stamp)
        stamp2 = Image.new("RGBA", (180, 60), (0, 0, 255, 40))
        stamp2_draw = ImageDraw.Draw(stamp2)
        stamp2_draw.text((10, 15), "APPROVED", fill=(0, 0, 150), font=f)
        img.paste(stamp2, (40, img.height - 80), stamp2)

    img.save(str(stem.with_suffix(".jpg")), "JPEG", quality=90)
    img.save(str(stem.with_suffix(".png")), "PNG")
    img.save(str(stem.with_suffix(".tiff")), "TIFF")


def _bulk_pdf_lines(title: str, fields: list) -> list[tuple]:
    lines = [(title, 72, 80, True)]
    for i, (label, value) in enumerate(fields):
        lines.append((f"{label}: {value}", 72, 140 + i * 30, False))
    return lines


def gen_bulk_diplomas():
    for i in range(15):
        title, fields = _diploma_data(i)
        stem = f"diploma-{i + 1:03d}"
        lines = _bulk_pdf_lines(title, fields)
        _save_all_formats(stem, title, fields, pdf_lines=lines)


def gen_bulk_certificates():
    for i in range(15):
        title, fields = _certificate_data(i)
        stem = f"certificate-{i + 1:03d}"
        lines = _bulk_pdf_lines(title, fields)
        _save_all_formats(stem, title, fields, pdf_lines=lines)


def gen_bulk_transcripts():
    for i in range(15):
        title, fields = _transcript_data(i)
        stem = f"transcript-{i + 1:03d}"
        lines = _bulk_pdf_lines(title, fields)
        _save_all_formats(stem, title, fields, pdf_lines=lines)


def gen_edge_cases():
    for i in range(15):
        title, fields = _edgecase_data(i)
        stem = f"edgecase-{i + 1:03d}"
        pdf_lines = _bulk_pdf_lines(title, fields) if fields else None

        if i == 0:       # empty: 0-byte / 1x1 pixel
            _save_all_formats(stem, "", None)
        elif i == 1:     # minimal: small image
            _save_all_formats(stem, title, fields, pdf_lines, size=(200, 80))
        elif i == 2:     # blurry
            _save_all_formats(stem, title, fields, pdf_lines, blur=True)
        elif i in (3, 4, 6, 7, 8, 11, 13):  # normal generation
            _save_all_formats(stem, title, fields, pdf_lines)
        elif i == 5:     # rotated
            _save_all_formats(stem, title, fields, pdf_lines, rotate=30)
        elif i == 9:     # bad MIME: .txt file
            (FIXTURES_DIR / f"{stem}.txt").write_text(
                "this is not a pdf or image file\n"
            )
        elif i == 10:    # small image
            _save_all_formats(stem, title, fields, pdf_lines, size=(80, 60))
        elif i == 12:    # noisy background
            _save_all_formats(stem, title, fields, pdf_lines, noisy=True)
        elif i == 14:    # stamps overlay
            _save_all_formats(stem, title, fields, pdf_lines, stamps=True)


# ── main ──

if __name__ == "__main__":
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    print(f"Generating fixtures in {FIXTURES_DIR}/")

    print("\nBulk diplomas (15 indices x 4 formats = 60):")
    gen_bulk_diplomas()
    print("  diploma-001..015 .pdf .jpg .png .tiff")

    print("\nBulk certificates (60):")
    gen_bulk_certificates()
    print("  certificate-001..015 .pdf .jpg .png .tiff")

    print("\nBulk transcripts (60):")
    gen_bulk_transcripts()
    print("  transcript-001..015 .pdf .jpg .png .tiff")

    print("\nEdge cases (14 types x 4 formats + 1 txt = 57):")
    gen_edge_cases()
    print("  edgecase-001..015 (index 10 = .txt only)")

    total = len(list(FIXTURES_DIR.glob("*")))
    print(f"\nDone. Total files: {total}")
