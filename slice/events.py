"""
Event log.

Every important state transition and agent action is recorded here with a
timestamp.  The log is append-only (written to SQLite through the tutor db)
and is the authoritative audit trail for any session.

Event names are fixed string constants rather than an Enum so they print
cleanly without the class prefix.
"""
from __future__ import annotations

import time
from typing import Any

# ── Event name constants ─────────────────────────────────────────────────────

SESSION_STARTED = "SESSION_STARTED"
SESSION_RESUMED = "SESSION_RESUMED"
SESSION_COMPLETED = "SESSION_COMPLETED"

QUESTION_CLASSIFIED = "QUESTION_CLASSIFIED"
GENERAL_ANSWER_GIVEN = "GENERAL_ANSWER_GIVEN"

DIAGNOSIS_CREATED = "DIAGNOSIS_CREATED"
DIAGNOSIS_KNOWN_MISCONCEPTION = "DIAGNOSIS_KNOWN_MISCONCEPTION"
DIAGNOSIS_UNKNOWN_TOPIC = "DIAGNOSIS_UNKNOWN_TOPIC"

SOCRATIC_QUESTION_ASKED = "SOCRATIC_QUESTION_ASKED"
STUDENT_RESPONSE_RECEIVED = "STUDENT_RESPONSE_RECEIVED"

TRANSFER_TASK_CREATED = "TRANSFER_TASK_CREATED"
TRANSFER_ANSWER_RECEIVED = "TRANSFER_ANSWER_RECEIVED"

EVALUATION_COMPLETED = "EVALUATION_COMPLETED"
EVALUATION_PASS = "EVALUATION_PASS"
EVALUATION_FAIL = "EVALUATION_FAIL"
EVALUATION_PARTIAL = "EVALUATION_PARTIAL"

MISCONCEPTION_RECURRED = "MISCONCEPTION_RECURRED"
SOCRATIC_ATTEMPTS_EXHAUSTED = "SOCRATIC_ATTEMPTS_EXHAUSTED"

TUTOR_EXPLANATION_CREATED = "TUTOR_EXPLANATION_CREATED"
TUTOR_TRANSFER_CREATED = "TUTOR_TRANSFER_CREATED"

LEARNING_STATE_UPDATED = "LEARNING_STATE_UPDATED"
MASTERY_UPDATED = "MASTERY_UPDATED"

PLAN_CREATED = "PLAN_CREATED"
ESCALATED = "ESCALATED"
HUMAN_REVIEW_REQUESTED = "HUMAN_REVIEW_REQUESTED"

STATE_TRANSITION = "STATE_TRANSITION"
LLM_FALLBACK_USED = "LLM_FALLBACK_USED"
LLM_CALL_MADE = "LLM_CALL_MADE"
VALIDATION_FAILED = "VALIDATION_FAILED"
BUDGET_LIMIT_HIT = "BUDGET_LIMIT_HIT"


# ── Event record ─────────────────────────────────────────────────────────────

def make_event(
    event_type: str,
    data: dict[str, Any] | None = None,
    session_id: str | None = None,
    student_id: str | None = None,
) -> dict[str, Any]:
    """Build a structured event dict ready to be stored."""
    return {
        "event_type": event_type,
        "timestamp": time.time(),
        "session_id": session_id,
        "student_id": student_id,
        "data": data or {},
    }
