"""Generate all test fixture files for CredChain Python integration tests.

Run: python tests/fixtures/gen_fixtures.py
Or:  make gen-fixtures

Generates PDFs (PyMuPDF), images (Pillow), and edge-case files.
All files are placed in the same directory as this script.
"""

from pathlib import Path

import fitz
from PIL import Image, ImageDraw, ImageFont

FIXTURES_DIR = Path(__file__).parent


def _pdf_add_text(page: fitz.Page, lines: list[tuple[str, int, int, bool]]) -> None:
    for text, x, y, bold in lines:
        if not text:
            continue
        page.insert_text(
            (x, y), text,
            fontsize=14 if bold else 11,
            fontname="hebo" if bold else "helv",
        )


def gen_diploma_id() -> None:
    """1-page Indonesian diploma (digital text, fast OCR path)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _pdf_add_text(page, [
        ("UNIVERSITAS INDONESIA", 72, 80, True),
        ("Fakultas Ilmu Komputer", 72, 105, False),
        ("IJAZAH SARJANA", 72, 170, True),
        ("Dengan ini menyatakan bahwa:", 72, 230, False),
        ("Nama: John Doe Pratama", 72, 280, True),
        ("Nomor Induk Mahasiswa: 2019051234", 72, 310, False),
        ("Tanggal Lahir: 15 Mei 1998", 72, 335, False),
        ("Program Studi: Ilmu Komputer", 72, 360, False),
        ("IPK: 3.85", 72, 385, False),
        ("Tanggal Terbit: 20 Juli 2023", 72, 410, False),
        ("Nomor Ijazah: UI-CS-2023-001234", 72, 435, False),
        ("Nomor Registrasi: REG-IJZ-2023-051234", 72, 460, False),
        ("telah menyelesaikan seluruh persyaratan akademik", 72, 510, False),
        ("dan dinyatakan lulus sebagai Sarjana Ilmu Komputer.", 72, 530, False),
        ("Diterbitkan oleh: Prof. Dr. Rektor Universitas Indonesia", 72, 600, False),
        ("Kode Verifikasi: 7G9K-2X8M-AB12", 72, 670, False),
    ])
    doc.save(str(FIXTURES_DIR / "diploma-id.pdf"))
    doc.close()
    print("Generated diploma-id.pdf")


def gen_certificate_en() -> None:
    """1-page English professional certificate (digital text)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _pdf_add_text(page, [
        ("PROFESSIONAL CERTIFICATION", 72, 80, True),
        ("Issued by: CredChain Certification Authority", 72, 105, False),
        ("CERTIFICATE OF COMPLETION", 72, 170, True),
        ("This certifies that:", 72, 230, False),
        ("Holder Name: Jane Smith", 72, 280, True),
        ("Certification Number: CCA-2024-EN-009876", 72, 310, False),
        ("Date of Birth: March 22, 1995", 72, 335, False),
        ("Specialization: Blockchain Technology", 72, 360, False),
        ("Score: 92/100", 72, 385, False),
        ("Issue Date: January 15, 2024", 72, 410, False),
        ("Expiry Date: January 15, 2027", 72, 435, False),
        ("Reference ID: REF-CCA-2024-009876", 72, 460, False),
        ("has successfully completed all requirements", 72, 510, False),
        ("for the Blockchain Technology Certification.", 72, 530, False),
        ("Authorized by: Dr. Chief Examiner", 72, 600, False),
        ("Verification Code: ABCD-1234-EFGH", 72, 670, False),
    ])
    doc.save(str(FIXTURES_DIR / "certificate-en.pdf"))
    doc.close()
    print("Generated certificate-en.pdf")


def gen_transcript_id() -> None:
    """2-page Indonesian academic transcript (digital text, multi-page test)."""
    doc = fitz.open()

    page1 = doc.new_page(width=612, height=792)
    _pdf_add_text(page1, [
        ("UNIVERSITAS INDONESIA", 72, 60, True),
        ("TRANSKRIP AKADEMIK RESMI", 72, 85, True),
        ("Nama: Budi Santoso", 72, 140, False),
        ("NIM: 2018030567", 72, 165, False),
        ("Program Studi: Teknik Informatika", 72, 190, False),
        ("Angkatan: 2018", 72, 215, False),
        ("DAFTAR NILAI SEMESTER 1-4", 72, 260, True),
        ("Algoritma dan Struktur Data: A (4.0)", 72, 295, False),
        ("Pemrograman Berorientasi Objek: A- (3.7)", 72, 320, False),
        ("Basis Data: B+ (3.3)", 72, 345, False),
        ("Jaringan Komputer: A (4.0)", 72, 370, False),
        ("Matematika Diskrit: B+ (3.3)", 72, 395, False),
        ("Kalkulus: B (3.0)", 72, 420, False),
        ("Sistem Operasi: A (4.0)", 72, 445, False),
        ("Rekayasa Perangkat Lunak: A- (3.7)", 72, 470, False),
        ("IPK Semester 1-4: 3.63", 72, 520, True),
        ("Halaman 1 dari 2", 72, 750, False),
    ])

    page2 = doc.new_page(width=612, height=792)
    _pdf_add_text(page2, [
        ("UNIVERSITAS INDONESIA", 72, 60, True),
        ("TRANSKRIP AKADEMIK RESMI (Lanjutan)", 72, 85, True),
        ("Nama: Budi Santoso | NIM: 2018030567", 72, 120, False),
        ("DAFTAR NILAI SEMESTER 5-8", 72, 160, True),
        ("Kecerdasan Buatan: A (4.0)", 72, 195, False),
        ("Keamanan Siber: A- (3.7)", 72, 220, False),
        ("Pengolahan Citra Digital: B+ (3.3)", 72, 245, False),
        ("Komputasi Awan: A (4.0)", 72, 270, False),
        ("Skripsi: A (4.0)", 72, 295, False),
        ("IPK Kumulatif: 3.75", 72, 350, True),
        ("Total SKS: 144", 72, 375, False),
        ("Status Kelulusan: LULUS", 72, 400, True),
        ("Nomor Transkrip: TR-UI-TI-2022-030567", 72, 450, False),
        ("Tanggal Terbit: 15 Agustus 2022", 72, 475, False),
        ("Kode Verifikasi: TR22-BUDI-0567", 72, 500, False),
        ("Ditetapkan oleh Dekan Fakultas Teknik", 72, 600, False),
        ("Halaman 2 dari 2", 72, 750, False),
    ])

    doc.save(str(FIXTURES_DIR / "transcript-id.pdf"))
    doc.close()
    print("Generated transcript-id.pdf (2 pages)")


def _make_credential_image(
    title: str,
    fields: list[tuple[str, str]],
    size: tuple[int, int] = (800, 600),
) -> Image.Image:
    """Render a credential as a PIL image with white background."""
    img = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    from PIL.ImageFont import FreeTypeFont
    from PIL.ImageFont import ImageFont as PILImageFont
    font_title: FreeTypeFont | PILImageFont
    font_body: FreeTypeFont | PILImageFont
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        font_body = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except OSError:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()
    draw.text((40, 30), title, fill=(0, 0, 0), font=font_title)
    draw.line([(40, 65), (size[0] - 40, 65)], fill=(0, 0, 0), width=2)
    y = 90
    for label, value in fields:
        draw.text((40, y), f"{label}: {value}", fill=(0, 0, 0), font=font_body)
        y += 30
    return img


def gen_scanned_diploma() -> None:
    """1-page image-only PDF (no text layer) — triggers EasyOCR fallback."""
    img = _make_credential_image(
        "IJAZAH SARJANA - UNIVERSITAS INDONESIA",
        [
            ("Nama", "Ahmad Fauzi"),
            ("NIM", "2017040123"),
            ("Program Studi", "Sistem Informasi"),
            ("IPK", "3.72"),
            ("Tanggal Terbit", "10 September 2021"),
            ("Nomor Ijazah", "UI-SI-2021-040123"),
            ("Nomor Registrasi", "REG-AFZ-2021-040123"),
            ("Kode Verifikasi", "SCAN-1234-ABCD"),
        ],
    )
    import io
    width, height = img.size
    png_buf = io.BytesIO()
    img.save(png_buf, format="PNG")
    png_buf.seek(0)
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    rect = fitz.Rect(0, 0, width, height)
    page.insert_image(rect, stream=png_buf.read())
    doc.save(str(FIXTURES_DIR / "scanned-diploma.pdf"))
    doc.close()
    print("Generated scanned-diploma.pdf (image-only, EasyOCR fallback)")


def gen_id_card_jpg() -> None:
    """Indonesian KTP simulation — tests NIK regex + EasyOCR path."""
    img = _make_credential_image(
        "KARTU TANDA PENDUDUK (KTP)",
        [
            ("NIK", "3171012345678901"),
            ("Nama", "Siti Rahayu"),
            ("Tempat/Tgl Lahir", "Jakarta, 05-08-1992"),
            ("Jenis Kelamin", "Perempuan"),
            ("Alamat", "Jl. Merdeka No. 17, Jakarta Pusat"),
            ("RT/RW", "003/005"),
            ("Kel/Desa", "Gambir"),
            ("Kecamatan", "Gambir"),
            ("Agama", "Islam"),
            ("Status Perkawinan", "Belum Kawin"),
            ("Pekerjaan", "Karyawan Swasta"),
            ("Kewarganegaraan", "WNI"),
            ("Berlaku Hingga", "SEUMUR HIDUP"),
        ],
        size=(800, 500),
    )
    img.save(str(FIXTURES_DIR / "id-card.jpg"), "JPEG", quality=90)
    print("Generated id-card.jpg")


def gen_certificate_png() -> None:
    """PNG certificate — tests PNG MIME type."""
    img = _make_credential_image(
        "SERTIFIKAT KOMPETENSI",
        [
            ("Nama", "Rizky Pratama"),
            ("Nomor Sertifikat", "SK-2024-RP-005432"),
            ("Kompetensi", "Pengembangan Aplikasi Web"),
            ("Tanggal Terbit", "20 Maret 2024"),
            ("Berlaku Hingga", "20 Maret 2027"),
            ("Kode Verifikasi", "PNG4-CERT-5432"),
        ],
    )
    img.save(str(FIXTURES_DIR / "certificate.png"), "PNG")
    print("Generated certificate.png")


def gen_certificate_webp() -> None:
    """WEBP certificate — tests WEBP MIME type."""
    img = _make_credential_image(
        "SERTIFIKAT PELATIHAN",
        [
            ("Nama", "Dewi Kusuma"),
            ("Nomor Sertifikat", "SP-2024-DK-007891"),
            ("Pelatihan", "Keamanan Jaringan Komputer"),
            ("Tanggal Terbit", "05 April 2024"),
            ("Penyelenggara", "Lembaga Sertifikasi Nasional"),
            ("Kode Verifikasi", "WEBP-7891-CERT"),
        ],
    )
    img.save(str(FIXTURES_DIR / "certificate.webp"), "WEBP", quality=90)
    print("Generated certificate.webp")


def gen_certificate_tiff() -> None:
    """TIFF certificate — tests TIFF MIME type."""
    img = _make_credential_image(
        "SERTIFIKAT KEAHLIAN",
        [
            ("Nama", "Hendra Wijaya"),
            ("Nomor Sertifikat", "SK-2024-HW-003210"),
            ("Keahlian", "Analisis Data dan Machine Learning"),
            ("Tanggal Terbit", "12 Februari 2024"),
            ("Lembaga Penerbit", "Asosiasi Profesional Indonesia"),
            ("NIP", "198703122010011005"),
            ("Kode Verifikasi", "TIFF-3210-CERT"),
        ],
    )
    img.save(str(FIXTURES_DIR / "certificate.tiff"), "TIFF")
    print("Generated certificate.tiff")


def gen_empty_pdf() -> None:
    """0-byte PDF — tests empty file rejection."""
    path = FIXTURES_DIR / "empty.pdf"
    path.write_bytes(b"")
    print("Generated empty.pdf (0 bytes)")


def gen_fake_txt() -> None:
    """Plain text file — tests MIME type rejection."""
    path = FIXTURES_DIR / "fake.txt"
    path.write_text("this is not a pdf or image file\n")
    print("Generated fake.txt")


if __name__ == "__main__":
    print(f"Generating fixtures in {FIXTURES_DIR}/")
    gen_diploma_id()
    gen_certificate_en()
    gen_transcript_id()
    gen_scanned_diploma()
    gen_id_card_jpg()
    gen_certificate_png()
    gen_certificate_webp()
    gen_certificate_tiff()
    gen_empty_pdf()
    gen_fake_txt()
    print("\nAll fixtures generated.")
    print("Files:")
    for f in sorted(FIXTURES_DIR.glob("*")):
        if f.name != "gen_fixtures.py":
            print(f"  {f.name:35s} {f.stat().st_size:>8,} bytes")

