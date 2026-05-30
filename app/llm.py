"""Qwen2.5-0.5B-Instruct (GGUF Q4_K_M) wrapper via llama-cpp-python.

Public function signatures take a single `llm` parameter (an instance of
llama_cpp.Llama). Descriptions are now locale-based (see app/description.py)
so generate_description_id and translate_to_english have been removed.
"""

import json
import threading
from typing import TYPE_CHECKING, Any

from app import codes
from app.config import settings
from app.errors import AppError

if TYPE_CHECKING:
    from llama_cpp import Llama

EXTRACT_PROMPT = (
    "You are a document analysis assistant. Read the following document text "
    "and identify all meaningful field name to value pairs. Output a single "
    "JSON object mapping field names (snake_case) to their string values. "
    "Do not include any commentary, do not wrap in markdown. "
    "If a field is ambiguous, omit it. If no fields are present, return {}."
)


def _generate(
    llm: "Llama",
    prompt: str,
    max_tokens: int | None = None,
    json_mode: bool = False,
) -> str:
    """Run a single chat-completion call with deterministic decoding.

    Uses temperature=0.0 for stable output. max_tokens defaults to
    settings.llm_max_new_tokens. json_mode=True constrains sampling to
    valid JSON, reducing parse failures in extract_fields.
    """
    if max_tokens is None:
        max_tokens = settings.llm_max_new_tokens
    kwargs: dict[str, Any] = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response: Any = llm.create_chat_completion(**kwargs)
    content = response["choices"][0]["message"]["content"]
    return str(content)


def extract_fields(llm: "Llama", text: str) -> dict[str, str]:
    """Extract all meaningful fields from document text using Qwen2.5.

    Open-ended: never hardcodes field names. Returns whatever the model
    identifies. Retries once if the first response is not valid JSON.
    Raises AppError(CODE_AI_EXTRACT_LLM_FAILED) if both attempts fail.
    Returns {} for empty text without calling the model.
    """
    if not text or not text.strip():
        return {}
    prompt = f"{EXTRACT_PROMPT}\n\nDocument text:\n{text}"
    for attempt in range(2):
        raw = _generate(llm, prompt, json_mode=True)
        try:
            result = json.loads(raw)
            if isinstance(result, dict):
                return {str(k): str(v) for k, v in result.items()}
        except (json.JSONDecodeError, ValueError):
            if attempt == 0:
                prompt = (
                    f"{EXTRACT_PROMPT}\n\nYour previous response was not valid JSON. "
                    f"Output ONLY a JSON object.\n\nDocument text:\n{text}"
                )
    raise AppError(codes.CODE_AI_EXTRACT_LLM_FAILED)


def _generate_with_cancel(
    llm: "Llama",
    prompt: str,
    max_tokens: int,
    cancel_event: threading.Event,
) -> str:
    """Stream tokens from Qwen and stop early if cancel_event is set.

    Uses stream=True so generation can be interrupted at token boundaries.
    When cancel_event is set, the loop exits and partial output is returned.
    This allows asyncio.wait_for to actually stop work rather than abandoning
    a running thread.
    """
    tokens: list[str] = []
    for chunk in llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.0,
        stream=True,
    ):
        if cancel_event.is_set():
            break
        delta = str(chunk["choices"][0].get("delta", {}).get("content", ""))  # type: ignore[index, union-attr]
        if delta:
            tokens.append(delta)
    return "".join(tokens)


def extract_fields_with_cancel(
    llm: "Llama",
    text: str,
    cancel_event: threading.Event,
) -> dict[str, str]:
    """Like extract_fields but accepts a cancel_event for cooperative cancellation.

    When cancel_event is set between tokens, generation stops and
    AppError(CODE_AI_LLM_TIMEOUT) is raised so the caller knows it was
    cancelled rather than failed.
    """
    if not text or not text.strip():
        return {}
    prompt = f"{EXTRACT_PROMPT}\n\nDocument text:\n{text}"
    for attempt in range(2):
        raw = _generate_with_cancel(llm, prompt, settings.llm_max_new_tokens, cancel_event)
        if cancel_event.is_set():
            raise AppError(codes.CODE_AI_LLM_TIMEOUT)
        try:
            result = json.loads(raw)
            if isinstance(result, dict):
                return {str(k): str(v) for k, v in result.items()}
        except (json.JSONDecodeError, ValueError):
            if attempt == 0:
                prompt = (
                    f"{EXTRACT_PROMPT}\n\nYour previous response was not valid JSON. "
                    f"Output ONLY a JSON object.\n\nDocument text:\n{text}"
                )
    raise AppError(codes.CODE_AI_EXTRACT_LLM_FAILED)

