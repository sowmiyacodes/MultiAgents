"""
Tutor state machine states.

The 12 states of the adaptive DSA tutoring engine.  Transitions between them
are always decided by deterministic runtime code — never by an LLM.

The LLM produces *evidence*; the runtime decides *what happens next*.
"""
from __future__ import annotations

from enum import Enum


class TutorState(str, Enum):
    """Every valid state the tutoring engine can be in."""

    START = "START"
    DIAGNOSING = "DIAGNOSING"
    SOCRATIC_GUIDANCE = "SOCRATIC_GUIDANCE"
    GENERATE_TRANSFER_TASK = "GENERATE_TRANSFER_TASK"
    WAITING_FOR_STUDENT = "WAITING_FOR_STUDENT"
    EVALUATING = "EVALUATING"
    TARGETED_TUTORING = "TARGETED_TUTORING"
    UPDATE_STATE = "UPDATE_STATE"
    PLAN_NEXT = "PLAN_NEXT"
    ESCALATED = "ESCALATED"
    HUMAN_REVIEW_WAITING = "HUMAN_REVIEW_WAITING"
    COMPLETE = "COMPLETE"

    @property
    def is_terminal(self) -> bool:
        return self in (
            TutorState.COMPLETE,
            TutorState.HUMAN_REVIEW_WAITING,
            TutorState.ESCALATED,
        )

    @property
    def is_waiting(self) -> bool:
        return self == TutorState.WAITING_FOR_STUDENT

    @property
    def label(self) -> str:
        return self.value.replace("_", " ").title()


# ── Allowed transitions (deterministic) ─────────────────────────────────────

ALLOWED_TRANSITIONS: dict[TutorState, set[TutorState]] = {
    TutorState.START: {TutorState.DIAGNOSING},
    TutorState.DIAGNOSING: {TutorState.SOCRATIC_GUIDANCE, TutorState.TARGETED_TUTORING, TutorState.COMPLETE},
    TutorState.SOCRATIC_GUIDANCE: {TutorState.WAITING_FOR_STUDENT},
    TutorState.WAITING_FOR_STUDENT: {TutorState.EVALUATING},
    TutorState.EVALUATING: {
        TutorState.GENERATE_TRANSFER_TASK,
        TutorState.SOCRATIC_GUIDANCE,
        TutorState.TARGETED_TUTORING,
        TutorState.UPDATE_STATE,
        TutorState.ESCALATED,
    },
    TutorState.GENERATE_TRANSFER_TASK: {TutorState.WAITING_FOR_STUDENT},
    TutorState.TARGETED_TUTORING: {TutorState.WAITING_FOR_STUDENT, TutorState.GENERATE_TRANSFER_TASK, TutorState.ESCALATED},
    TutorState.UPDATE_STATE: {TutorState.PLAN_NEXT},
    TutorState.PLAN_NEXT: {TutorState.COMPLETE, TutorState.SOCRATIC_GUIDANCE},
    TutorState.ESCALATED: {TutorState.HUMAN_REVIEW_WAITING},
    TutorState.HUMAN_REVIEW_WAITING: set(),
    TutorState.COMPLETE: set(),
}


def validate_transition(from_state: TutorState, to_state: TutorState) -> None:
    """Raise if the transition is not in the allowed table."""
    allowed = ALLOWED_TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        raise ValueError(
            f"Invalid state transition: {from_state.value} → {to_state.value}. "
            f"Allowed: {[s.value for s in sorted(allowed, key=lambda x: x.value)]}"
        )
