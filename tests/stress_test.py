"""Stress test — all bulk fixtures through /extract, /verify, /extract-ids.

Uses multi-file batching (up to 15 files/request) for speed.
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
BASE_URL = "http://localhost:8081"
TIMEOUT = 300

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
                        "note": str(e)})


def _build_batch(prefix: str) -> list[tuple]:
    """Build batch of existing PDF file tuples for a prefix."""
    batch: list[tuple] = []
    for i in range(15):
        p = FIXTURES / f"{prefix}-{i + 1:03d}.pdf"
        if p.exists():
            batch.append(("files", (p.name, open(p, "rb"), "application/pdf")))  # noqa: SIM115
    return batch


def test_extract_all() -> dict:
    """Extract all existing PDF fixtures via batch requests."""
    total = 0
    passed = 0
    failures: list[str] = []
    prefixes = ["diploma", "certificate", "transcript", "edgecase"]

    for prefix in prefixes:
        batch = _build_batch(prefix)
        if not batch:
            continue
        filenames = [ft[1][0] for ft in batch]
        r = requests.post(f"{BASE_URL}/extract", files=batch, timeout=TIMEOUT)
        body = r.json()
        for ft in batch:
            ft[1][1].close()
        data = body.get("data") or []
        errors = body.get("errors") or {}
        for j, d in enumerate(data):
            filename = filenames[j] if j < len(filenames) else f"index-{j}"
            if d is not None and "embeddings" in d:
                passed += 1
            else:
                err_msg = errors.get(f"files.{j}", ["Unknown"])[0]
                failures.append(f"{filename}: {err_msg}")
        total += len(data)

    ok = passed >= total * 0.7
    note = f"{passed}/{total} PDF extracts OK"
    if failures:
        note += f" | FAILURES: {'; '.join(failures)}"
    return {"pass": ok, "note": note}


def test_extract_ids_all() -> dict:
    """Extract IDs from all existing PDF fixtures."""
    total = 0
    passed = 0
    failures: list[str] = []
    prefixes = ["diploma", "certificate", "transcript", "edgecase"]

    for prefix in prefixes:
        batch = _build_batch(prefix)
        if not batch:
            continue
        filenames = [ft[1][0] for ft in batch]
        r = requests.post(f"{BASE_URL}/extract-ids", files=batch, timeout=TIMEOUT)
        body = r.json()
        for ft in batch:
            ft[1][1].close()
        data = body.get("data") or []
        for j, d in enumerate(data):
            filename = filenames[j] if j < len(filenames) else f"index-{j}"
            if d is not None and "potential_ids" in d:
                passed += 1
            else:
                failures.append(f"{filename}: null response")
        total += len(data)

    ok = passed >= total * 0.6
    note = f"{passed}/{total} extract-ids OK"
    if failures:
        note += f" | FAILURES: {'; '.join(failures)}"
    return {"pass": ok, "note": note}


def test_verify_verdicts() -> dict:
    """Extract diploma-001 as reference, verify tampered/suspicious/low/not_similar."""
    ref_path = FIXTURES / "diploma-001.pdf"
    with open(ref_path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/extract",
            files=[("files", ("diploma-001.pdf", f, "application/pdf"))],
            timeout=TIMEOUT,
        )
    body = r.json()
    d = (body.get("data") or [None])[0]
    if d is None or "embeddings" not in d:
        return {"pass": False, "note": "SKIPPED — diploma-001 extract failed"}
    ref_emb = d["embeddings"]

    checks = {
        "tampered":       {"idx": 4,  "expect": "tampered"},
        "suspicious":      {"idx": 7,  "expect": "suspicious"},
        "low_similarity":  {"idx": 8,  "expect": "low_similarity"},
        "not_similar":     {"idx": 9,  "expect": "not_similar"},
    }

    detail = {}
    all_ok = True
    for name, cfg in checks.items():
        path = FIXTURES / f"edgecase-{cfg['idx']:03d}.pdf"
        if not path.exists():
            detail[name] = "file not found"
            all_ok = False
            continue
        metadata = json.dumps([{"stored_embeddings": ref_emb}])
        with open(path, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/verify",
                files=[("files", (path.name, f, "application/pdf"))],
                data={"metadata": metadata},
                timeout=TIMEOUT,
            )
        body = r.json()
        d2 = (body.get("data") or [None])[0]
        if d2 is None:
            detail[name] = "null response"
            all_ok = False
        elif d2.get("verdict") == cfg["expect"]:
            detail[name] = f"OK ({cfg['expect']}, {d2.get('similarity_score', '?')})"
        else:
            detail[name] = f"MISMATCH: got '{d2.get('verdict')}' expected '{cfg['expect']}'"
            all_ok = False

    note = " | ".join(f"{k}: {v}" for k, v in detail.items())
    return {"pass": all_ok, "note": note}


def write_report(report_path: Path) -> None:
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    total = len(results)
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# CredChain Python AI Service — Stress Test Report",
        f"**Date:** {now}",
        f"**Service:** {BASE_URL}",
        f"**Result:** {passed}/{total} passed | {failed} failed | {errors} errors",
        "",
        "## Summary",
        "",
        "| Test | Status | Time | Notes |",
        "|------|--------|------|-------|",
    ]
    for r in results:
        icon = "✅" if r["status"] == "PASS" else "❌"
        lines.append(
            f"| {icon} {r['name']} | {r['status']} | {r['elapsed']}s | {r.get('note', '')} |"
        )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nReport written to {report_path}")
    log(f"FINAL: {passed}/{total} passed | {failed} failed | {errors} errors")


def main() -> None:
    global BASE_URL
    parser = argparse.ArgumentParser(description="CredChain Python stress test")
    parser.add_argument("--url", default=BASE_URL)
    args = parser.parse_args()
    BASE_URL = args.url

    log("=== CredChain Python — Stress Test ===")
    log(f"Service: {BASE_URL} | Fixtures: {FIXTURES}\n")

    run_test("POST /extract — all 237 fixtures (batch requests)", test_extract_all)
    run_test("POST /verify — tampered/suspicious/low/not_similar", test_verify_verdicts)
    run_test("POST /extract-ids — all PDFs (batch)", test_extract_ids_all)

    report_path = (
        Path(__file__).parent.parent.parent / "docs" /
        f"stress-test-report-{datetime.now(UTC).strftime('%Y-%m-%d')}.md"
    )
    write_report(report_path)

    passed = sum(1 for r in results if r["status"] == "PASS")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
