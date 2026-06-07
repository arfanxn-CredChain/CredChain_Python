"""Domain error class + HTTP status mapper for the AI service."""

from app import codes

DEFAULT_MESSAGES: dict[int, str] = {
    codes.CODE_AI_SUCCESS: "Success",
    codes.CODE_AI_UNAUTHORIZED: "Invalid or missing API key",
    codes.CODE_AI_VALIDATION: "Validation failed",
    codes.CODE_AI_INTERNAL: "Internal server error",
    codes.CODE_AI_RATE_LIMITED: "Too many requests",
    codes.CODE_AI_EXTRACT_SUCCESS: "Document extracted successfully",
    codes.CODE_AI_EXTRACT_OCR_FAILED: "OCR failed during extraction",
    codes.CODE_AI_GEMINI_FAILED: "Gemini API request failed",
    codes.CODE_AI_VERIFY_SUCCESS: "Verification completed",
    codes.CODE_AI_VERIFY_INVALID_INPUT: "Invalid compared embeddings",
    codes.CODE_AI_VERIFY_OCR_FAILED: "OCR failed during verification",
    codes.CODE_AI_EXTRACT_IDS_SUCCESS: "Potential IDs extracted",
    codes.CODE_AI_EXTRACT_IDS_OCR_FAILED: "OCR failed during ID extraction",
    codes.CODE_AI_EXTRACT_IDS_NO_MATCHES: "No potential IDs found in document",
    codes.CODE_AI_HEALTH_SUCCESS: "Service is healthy",
    codes.CODE_AI_HEALTH_NOT_READY: "Models not yet loaded",
}


class AppError(Exception):
    """Domain error carrying a 6-digit code, human message, and optional
    per-field error map.

    Raised by routes/services when a known failure path occurs. The
    FastAPI exception handler in main.py converts these into the unified
    {code, message, errors} envelope.
    """

    def __init__(
        self,
        code: int,
        message: str | None = None,
        errors: dict[str, list[str]] | None = None,
    ) -> None:
        self.code = code
        self.message = message or DEFAULT_MESSAGES.get(code, "error")
        self.errors = errors
        super().__init__(self.message)


def http_status_for(code: int) -> int:
    """Map a 6-digit response code to its HTTP status code.

    Convention from the spec:
      xx00         -> 200 OK (success)
      xx40 / xx41+ -> 400 Bad Request (validation)
      xx50 / xx51+ -> 500 Internal Server Error (internal failure)
    """
    status_suffix = code % 100
    if code == codes.CODE_AI_UNAUTHORIZED:
        return 401
    if code == codes.CODE_AI_RATE_LIMITED:
        return 429
    if status_suffix < 20:
        return 200
    if 40 <= status_suffix < 50:
        return 400
    return 500
