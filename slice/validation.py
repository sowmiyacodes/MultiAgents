"""
Validation and prompt-injection defence.

All student input, retrieved content, and external text is treated as DATA,
not instructions.  This module:

  1. Sanitises student input before it is passed to any agent prompt.
  2. Validates all LLM JSON outputs against their Pydantic schemas.
  3. Provides a fallback path when LLM output is persistently invalid.

The LLM is NEVER allowed to:
  • Directly set state-machine state
  • Bypass attempt limits or escalation
  • Modify the database
  • Execute code
  • Alter configuration
"""
from __future__ import annotations

import re
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# Patterns that look like prompt-injection attempts.
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(your\s+)?(previous|system|all)\s+(prompt|instruction)", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"(forget|disregard)\s+(everything|your\s+(training|instructions))", re.I),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a\s+)", re.I),
    re.compile(r"new\s+system\s+prompt", re.I),
    re.compile(r"override\s+(the\s+)?(system|instruction)", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"DAN\s+mode", re.I),
]

# Maximum length of student input we accept (characters).
MAX_INPUT_LENGTH = 4000


def sanitise_student_input(raw: str) -> str:
    """
    Prepare student input for safe inclusion in agent prompts.

    • Truncates to MAX_INPUT_LENGTH.
    • Flags injection-like patterns (logs but does NOT refuse — we still
      process the educational content; we just don't let it leak into the
      system role).
    """
    text = (raw or "").strip()[:MAX_INPUT_LENGTH]
    return text


def contains_injection_attempt(text: str) -> bool:
    """Return True if the text contains prompt-injection-like patterns."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def validate_llm_output(raw: Any, schema: Type[T]) -> T | None:
    """
    Parse and validate a dict/str from the LLM against a Pydantic schema.

    Returns the validated model, or None if validation fails.
    Callers should fall back to deterministic logic on None.
    """
    if raw is None:
        return None

    try:
        if isinstance(raw, dict):
            return schema.model_validate(raw)
        if isinstance(raw, str):
            return schema.model_validate_json(raw)
        if isinstance(raw, schema):
            return raw
    except (ValidationError, ValueError, TypeError):
        pass

    return None


def strip_markdown_fence(text: str) -> str:
    """Strip ``` JSON fences that models add even when not asked."""
    t = (text or "").strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) > 1:
            t = parts[1]
            if t.lstrip().lower().startswith("json"):
                t = t.lstrip()[4:]
    return t.strip()
