"""Extraction prompts for Gemini — module-level constants for easy editing.

Mirrors prompts from notebooks/credchain-python.ipynb.
"""

PROMPT_EXTRACT_DOCUMENT = (
    "Extract all textual content from this document. "
    "Omit headers, footers, boilerplate, and formatting artifacts. "
    "Also extract all document IDs, registration numbers, and identifier codes. "
    "For each ID, identify its type (e.g. passport, driver_license, tax_id, "
    "student_id, national_id, etc.). "
    "Return a JSON object with keys 'raw_text' (string) and 'ids' "
    "(array of {type: str, value: str} objects)."
)

PROMPT_EXTRACT_IDS = (
    "Extract all document IDs, registration numbers, and identifier codes "
    "from this document. "
    "For each ID, identify its type (e.g. passport, driver_license, tax_id, "
    "student_id, national_id, etc.). "
    "Return a JSON object with key 'ids' containing an array of "
    "{type: str, value: str} objects."
)
