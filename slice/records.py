
"""
What a run is made of.

Deliberately stdlib-only: no pydantic, no framework. The store below has to be
understandable in one sitting, and a dependency-free core is easier to trust.

Domain schemas live in demo/schema.py.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RunState(str, Enum):
    DRAFTING = "drafting"
    GATING = "gating"
    AWAITING_EXPERT = "awaiting_expert"
    EVALUATING = "evaluating"
    COMPLETE = "complete"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (
            RunState.COMPLETE,
            RunState.FAILED,
        )

    @property
    def is_suspended(self) -> bool:
        return self is RunState.AWAITING_EXPERT


@dataclass(frozen=True)
class Version:
    """
    One immutable entry in a run's history.

    `kind` groups a series such as "student_attempt",
    "diagnostic", "socratic", "student_response", and "evaluator".

    `seq` orders the whole run.
    """

    seq: int
    kind: str
    produced_by: str
    payload: dict[str, Any]
    created_at: float

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


@dataclass
class Question:
    """
    A question parked for a human.

    The run is suspended until it is answered.
    """

    id: str
    run_id: str
    question: str
    context: dict[str, Any] = field(default_factory=dict)
    asked_at: float = 0.0
    timeout_at: float = 0.0
    answered_at: float | None = None
    answer: str | None = None

    @property
    def is_answered(self) -> bool:
        return self.answer is not None

    @property
    def is_expired(self) -> bool:
        return (
            not self.is_answered
            and time.time() > self.timeout_at
        )


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

