"""CredChain Python AI Service — Integration Test Suite.

Tests all endpoints with real fixture files from tests/fixtures/.
Run against a locally running service:

    make serve &
    python tests/integration_test.py

Or against Docker:

    make docker-up-build
    python tests/integration_test.py --url http://localhost:8081
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

FIXTURES = Path(__file__).parent / "fixtures"
BASE_URL = "http://127.0.0.1:8082"
FAST_TIMEOUT = 10
LLM_TIMEOUT = 900

results: list[dict[str, Any]] = []


def log(msg: str) -> None:
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def run_test(name: str, fn) -> None:
    log(f"START: {name}")
    start = time.time()
    try:
        result = fn()
        elapsed = round(time.time() - start, 2)
        status = "PASS" if result.get("pass") else "FAIL"
        log(f"  {status} ({elapsed}s): {result.get('note', '')}")
        results.append({"name": name, "status": status, "elapsed": elapsed, **result})
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        log(f"  ERROR ({elapsed}s): {e}")
        results.append({"name": name, "status": "ERROR", "elapsed": elapsed,
                        "note": str(e), "response": None})


def test_health():
    r = requests.get(f"{BASE_URL}/health", timeout=FAST_TIMEOUT)
    body = r.json()
    ok = (r.status_code == 200
          and body.get("code") == 500900
          and body["data"]["models_loaded"])
    return {"pass": ok, "http": r.status_code, "response": body,
            "note": f"code={body.get('code')} models_loaded={body.get('data', {}).get('models_loaded')}"}


def test_extract_bad_mime():
    with open(FIXTURES / "fake.txt", "rb") as f:
        r = requests.post(f"{BASE_URL}/extract",
                          files=[("files", ("fake.txt", f, "text/plain"))],
                          timeout=FAST_TIMEOUT)
    body = r.json()
    ok = r.status_code == 200 and body["data"][0] is None and "files.0" in (body.get("errors") or {})
    return {"pass": ok, "http": r.status_code, "response": body,
            "note": f"data[0]={body['data'][0]} errors={body.get('errors')}"}


def test_extract_empty_file():
    with open(FIXTURES / "empty.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/extract",
                          files=[("files", ("empty.pdf", f, "application/pdf"))],
                          timeout=FAST_TIMEOUT)
    body = r.json()
    ok = r.status_code == 200 and body["data"][0] is None and "files.0" in (body.get("errors") or {})
    return {"pass": ok, "http": r.status_code, "response": body,
            "note": f"data[0]={body['data'][0]} errors={body.get('errors')}"}


def test_verify_malformed_metadata():
    with open(FIXTURES / "diploma-id.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/verify",
                          files=[("files", ("diploma-id.pdf", f, "application/pdf"))],
                          data={"metadata": "not valid json"},
                          timeout=FAST_TIMEOUT)
    body = r.json()
    ok = r.status_code == 400 and body.get("code") == 500241
    return {"pass": ok, "http": r.status_code, "response": body,
            "note": f"code={body.get('code')}"}


extract_data: dict[str, Any] = {}


def test_extract_diploma():
    with open(FIXTURES / "diploma-id.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/extract",
                          files=[("files", ("diploma-id.pdf", f, "application/pdf"))],
                          timeout=LLM_TIMEOUT)
    body = r.json()
    d = (body.get("data") or [None])[0]
    ok = (r.status_code == 200 and body.get("code") == 500100
          and d is not None
          and len(d.get("embeddings", [])) == 768
          and isinstance(d.get("extracted_fields"), dict))
    if ok and d:
        extract_data["embeddings"] = d["embeddings"]
        extract_data["fields"] = d["extracted_fields"]
    note = (f"code={body.get('code')} "
            f"raw_text_len={len(d.get('raw_text', '')) if d else 0} "
            f"embeddings_len={len(d.get('embeddings', [])) if d else 0} "
            f"fields={list(d.get('extracted_fields', {}).keys()) if d else []}")
    return {"pass": ok, "http": r.status_code, "response": body, "note": note}


def test_verify_diploma():
    if not extract_data.get("embeddings"):
        return {"pass": False, "http": 0, "response": None,
                "note": "SKIPPED — T5 did not return embeddings"}
    metadata = json.dumps([{
        "stored_embeddings": extract_data["embeddings"],
        "stored_fields": extract_data["fields"],
    }])
    with open(FIXTURES / "diploma-id.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/verify",
                          files=[("files", ("diploma-id.pdf", f, "application/pdf"))],
                          data={"metadata": metadata},
                          timeout=LLM_TIMEOUT)
    body = r.json()
    d = (body.get("data") or [None])[0]
    ok = (r.status_code == 200 and body.get("code") == 500200
          and d is not None
          and "similarity_score" in d and "verdict" in d
          and "description" in d)
    note = (f"code={body.get('code')} "
            f"similarity={d.get('similarity_score') if d else None} "
            f"verdict={d.get('verdict') if d else None} "
            f"desc_id_len={len(d.get('description', {}).get('id', '')) if d else 0}")
    return {"pass": ok, "http": r.status_code, "response": body, "note": note}


def test_extract_ids_diploma():
    with open(FIXTURES / "diploma-id.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/extract-ids",
                          files=[("files", ("diploma-id.pdf", f, "application/pdf"))],
                          timeout=FAST_TIMEOUT)
    body = r.json()
    d = (body.get("data") or [None])[0]
    ok = (r.status_code == 200 and body.get("code") == 500300
          and d is not None
          and isinstance(d.get("potential_ids"), list))
    note = f"code={body.get('code')} potential_ids={d.get('potential_ids') if d else None}"
    return {"pass": ok, "http": r.status_code, "response": body, "note": note}


def test_extract_multipage():
    """T8: 2-page transcript PDF — verifies both pages are OCR'd."""
    with open(FIXTURES / "transcript-id.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/extract",
                          files=[("files", ("transcript-id.pdf", f, "application/pdf"))],
                          timeout=LLM_TIMEOUT)
    body = r.json()
    d = (body.get("data") or [None])[0]
    ok = (r.status_code == 200 and d is not None
          and len(d.get("raw_text", "")) > 100)
    note = (f"code={body.get('code')} "
            f"raw_text_len={len(d.get('raw_text', '')) if d else 0} "
            f"fields={list(d.get('extracted_fields', {}).keys()) if d else []}")
    return {"pass": ok, "http": r.status_code, "response": body, "note": note}


def test_extract_image_jpg():
    """T9: JPG image (id-card.jpg) — tests EasyOCR direct path."""
    with open(FIXTURES / "id-card.jpg", "rb") as f:
        r = requests.post(f"{BASE_URL}/extract",
                          files=[("files", ("id-card.jpg", f, "image/jpeg"))],
                          timeout=LLM_TIMEOUT)
    body = r.json()
    d = (body.get("data") or [None])[0]
    ok = (r.status_code == 200 and d is not None
          and len(d.get("embeddings", [])) == 768)
    note = (f"code={body.get('code')} "
            f"raw_text_len={len(d.get('raw_text', '')) if d else 0} "
            f"fields={list(d.get('extracted_fields', {}).keys()) if d else []}")
    return {"pass": ok, "http": r.status_code, "response": body, "note": note}


def test_extract_scanned_pdf():
    """T10: Image-only PDF — tests EasyOCR fallback (is_text_useful=False)."""
    with open(FIXTURES / "scanned-diploma.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/extract",
                          files=[("files", ("scanned-diploma.pdf", f, "application/pdf"))],
                          timeout=LLM_TIMEOUT)
    body = r.json()
    d = (body.get("data") or [None])[0]
    ok = (r.status_code == 200 and d is not None
          and len(d.get("embeddings", [])) == 768)
    note = (f"code={body.get('code')} "
            f"raw_text_len={len(d.get('raw_text', '')) if d else 0} "
            f"(EasyOCR fallback expected)")
    return {"pass": ok, "http": r.status_code, "response": body, "note": note}


def test_extract_tiff():
    """T11: TIFF image — tests TIFF MIME type support."""
    with open(FIXTURES / "certificate.tiff", "rb") as f:
        r = requests.post(f"{BASE_URL}/extract",
                          files=[("files", ("certificate.tiff", f, "image/tiff"))],
                          timeout=LLM_TIMEOUT)
    body = r.json()
    d = (body.get("data") or [None])[0]
    ok = (r.status_code == 200 and d is not None
          and len(d.get("embeddings", [])) == 768)
    note = (f"code={body.get('code')} "
            f"raw_text_len={len(d.get('raw_text', '')) if d else 0}")
    return {"pass": ok, "http": r.status_code, "response": body, "note": note}


def write_report(report_path: Path) -> None:
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    total = len(results)
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# CredChain Python AI Service — Integration Test Report",
        f"**Date:** {now}",
        f"**Service:** {BASE_URL}",
        f"**Result:** {passed}/{total} passed | {failed} failed | {errors} errors",
        "",
        "## Summary",
        "",
        "| # | Test | Status | Time | Notes |",
        "|---|------|--------|------|-------|",
    ]
    for r in results:
        icon = "✅" if r["status"] == "PASS" else ("❌" if r["status"] == "FAIL" else "⚠️")
        lines.append(f"| {icon} | {r['name']} | {r['status']} | {r['elapsed']}s | {r.get('note', '')} |")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nReport written to {report_path}")
    log(f"FINAL: {passed}/{total} passed | {failed} failed | {errors} errors")


def main() -> None:
    global BASE_URL
    parser = argparse.ArgumentParser(description="CredChain Python integration tests")
    parser.add_argument("--url", default=BASE_URL, help="Service base URL")
    args = parser.parse_args()
    BASE_URL = args.url

    log("=== CredChain Python AI Service — Integration Tests ===")
    log(f"Service: {BASE_URL}")
    log(f"Fixtures: {FIXTURES}")
    log("")

    run_test("T1: GET /health", test_health)
    run_test("T2: POST /extract — bad MIME (text/plain)", test_extract_bad_mime)
    run_test("T3: POST /extract — empty file", test_extract_empty_file)
    run_test("T4: POST /verify — malformed metadata", test_verify_malformed_metadata)
    run_test("T5: POST /extract — diploma-id.pdf (LLM)", test_extract_diploma)
    run_test("T6: POST /verify — same PDF vs stored (LLM)", test_verify_diploma)
    run_test("T7: POST /extract-ids — diploma-id.pdf (regex)", test_extract_ids_diploma)
    run_test("T8: POST /extract — transcript-id.pdf (2-page, LLM)", test_extract_multipage)
    run_test("T9: POST /extract — id-card.jpg (EasyOCR direct)", test_extract_image_jpg)
    run_test("T10: POST /extract — scanned-diploma.pdf (EasyOCR fallback)", test_extract_scanned_pdf)
    run_test("T11: POST /extract — certificate.tiff (TIFF MIME)", test_extract_tiff)

    report_path = (
        Path(__file__).parent.parent.parent / "docs" /
        f"integration-test-report-{datetime.now(UTC).strftime('%Y-%m-%d')}-full.md"
    )
    write_report(report_path)

    passed = sum(1 for r in results if r["status"] == "PASS")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()

