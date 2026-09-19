"""
Deterministic State Transition Decider.

Enforces:
- The LLM never chooses state machine transitions directly.
- The LLM produces structured evidence.
- The deterministic code in this module evaluates the evidence,
  attempt limits, and recurrence flags to select the next state.
"""
from __future__ import annotations

from typing import Optional

from llm.schemas import EvalResult, EvaluationResult
from runtime.budgets import TutorBudget
from slice.state_machine import TutorState


def decide_next_state_from_eval(
    eval_result: EvaluationResult,
    stage: str,  # "socratic" or "transfer"
    budget: TutorBudget,
    target_misconception: str,
) -> TutorState:
    """
    Decide the next state purely deterministically from evaluation evidence and budget.
    """
    is_pass = eval_result.result == EvalResult.PASS and eval_result.reasoning_correct
    is_fail = eval_result.result == EvalResult.FAIL or not eval_result.reasoning_correct
    recurred = eval_result.misconception_recurred

    if stage == "socratic":
        if is_pass:
            # Socratic pass: proceed to test transfer on a fresh problem
            return TutorState.GENERATE_TRANSFER_TASK

        # Socratic not passed
        if budget.socratic_attempts_exhausted():
            # Exhausted max Socratic attempts: escalate to Targeted Tutoring
            return TutorState.TARGETED_TUTORING

        # Try a different Socratic angle
        return TutorState.SOCRATIC_GUIDANCE

    elif stage == "transfer":
        if is_pass and eval_result.transfer_success:
            # Transfer passed: update state, then plan next
            return TutorState.UPDATE_STATE

        # Transfer failed
        if budget.tutor_attempts > 0 and (budget.socratic_attempts_exhausted() or recurred):
            # Failed after targeted tutoring -> escalate to human review
            return TutorState.ESCALATED

        if budget.socratic_attempts_exhausted():
            return TutorState.TARGETED_TUTORING

        # Misconception recurred on transfer -> go back to Socratic with different angle
        return TutorState.SOCRATIC_GUIDANCE

    return TutorState.SOCRATIC_GUIDANCE
