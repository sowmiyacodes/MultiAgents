"""
OpenRouter LLM integration for the DSA Adaptive Tutor.

Wraps the existing slice/llm.py complete() function with tutor-specific
config (OPENROUTER_API_KEY, OPENROUTER_MODEL env vars).

Falls back gracefully when no API key is configured.
"""
from __future__ import annotations

import json
import os
from typing import Any, Type

import httpx
from pydantic import BaseModel

from slice.validation import strip_markdown_fence

API = "https://openrouter.ai/api/v1"


class LLMError(RuntimeError):
    pass


from slice.config import load_env

load_env()


def get_model() -> str:
    return (os.environ.get("OPENROUTER_MODEL") or os.environ.get("SLICE_MODEL") or "openai/gpt-4o-mini").strip()


def get_api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def has_api_key() -> bool:
    return bool(get_api_key())



def call_llm(
    messages: list[dict[str, str]],
    schema: Type[BaseModel] | None = None,
    max_tokens: int = 1200,
    step: str = "call",
) -> Any:
    """
    Call OpenRouter with the given messages.
    Returns: validated schema instance, or raw text if no schema.
    Returns None if API key absent or call fails.
    """
    api_key = get_api_key()
    if not api_key:
        return None

    model = get_model()
    fallback_model = os.environ.get("OPENROUTER_FALLBACK_MODEL", "").strip()
    max_tokens_env = int(os.environ.get("MAX_TOKENS_PER_RESPONSE", str(max_tokens)))

    body = {
        "model": model,
        "max_tokens": max_tokens_env,
        "temperature": 0,
        "messages": messages,
    }
    if schema is not None:
        body["response_format"] = {"type": "json_object"}

    models_to_try = [model]
    if fallback_model and fallback_model != model:
        models_to_try.append(fallback_model)

    for m in models_to_try:
        body["model"] = m
        try:
            r = httpx.post(
                f"{API}/chat/completions",
                json=body,
                timeout=120.0,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://dsa-tutor.local",
                    "X-Title": "DSA Adaptive Tutor",
                },
            )
        except httpx.RequestError:
            continue

        if r.status_code == 402:
            return None  # Budget exceeded
        if r.status_code in (429, 500, 502, 503) and m != models_to_try[-1]:
            continue
        if r.status_code != 200:
            continue

        data = r.json()
        text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()

        if schema is None:
            return text

        # Try to parse
        parsed = _parse(text, schema)
        if parsed is not None:
            return parsed

        # One repair pass
        repaired = _repair(api_key, m, messages, text, schema, max_tokens_env)
        if repaired is not None:
            return repaired

    return None


def _parse(text: str, schema: Type[BaseModel]):
    from slice.validation import strip_markdown_fence
    from pydantic import ValidationError
    try:
        return schema.model_validate_json(strip_markdown_fence(text))
    except (ValidationError, ValueError, Exception):
        return None


def _repair(api_key, model, messages, bad_text, schema, max_tokens):
    from pydantic import ValidationError
    try:
        schema.model_validate_json(strip_markdown_fence(bad_text))
        return None
    except Exception as e:
        why = str(e)[:400]

    fix = messages + [
        {"role": "assistant", "content": bad_text[:2000]},
        {"role": "user", "content": (
            f"That did not match the required schema.\n\nError:\n{why}\n\n"
            f"Required JSON schema:\n{json.dumps(schema.model_json_schema())}\n\n"
            "Reply with the corrected JSON object and nothing else."
        )},
    ]
    try:
        r = httpx.post(
            f"{API}/chat/completions",
            json={"model": model, "max_tokens": max_tokens, "temperature": 0,
                  "messages": fix, "response_format": {"type": "json_object"}},
            timeout=60.0,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if r.status_code != 200:
            return None
        data = r.json()
        text = (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
        return _parse(text, schema)
    except Exception:
        return None
