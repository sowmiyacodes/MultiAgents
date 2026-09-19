"""
Test State Machine Transitions and Deterministic Sequencing.
"""
import pytest

from slice.state_machine import TutorState, validate_transition


def test_valid_transitions():
    # START -> DIAGNOSING
    validate_transition(TutorState.START, TutorState.DIAGNOSING)
    # DIAGNOSING -> SOCRATIC_GUIDANCE
    validate_transition(TutorState.DIAGNOSING, TutorState.SOCRATIC_GUIDANCE)
    # SOCRATIC_GUIDANCE -> WAITING_FOR_STUDENT
    validate_transition(TutorState.SOCRATIC_GUIDANCE, TutorState.WAITING_FOR_STUDENT)
    # WAITING_FOR_STUDENT -> EVALUATING
    validate_transition(TutorState.WAITING_FOR_STUDENT, TutorState.EVALUATING)
    # EVALUATING -> UPDATE_STATE
    validate_transition(TutorState.EVALUATING, TutorState.UPDATE_STATE)
    # UPDATE_STATE -> PLAN_NEXT
    validate_transition(TutorState.UPDATE_STATE, TutorState.PLAN_NEXT)
    # PLAN_NEXT -> COMPLETE
    validate_transition(TutorState.PLAN_NEXT, TutorState.COMPLETE)


def test_invalid_transition_raises():
    with pytest.raises(ValueError):
        # Cannot jump from START directly to COMPLETE
        validate_transition(TutorState.START, TutorState.COMPLETE)

    with pytest.raises(ValueError):
        # Cannot jump from DIAGNOSING directly to UPDATE_STATE without evaluation
        validate_transition(TutorState.DIAGNOSING, TutorState.UPDATE_STATE)
