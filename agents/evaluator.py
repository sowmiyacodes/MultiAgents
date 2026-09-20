"""
Evaluator Agent.

Evaluates student responses against target reasoning.
Key principles:
- Correct final answer without valid reasoning is NOT an automatic pass.
- Evaluates whether misconception recurred.
- Checks transfer reasoning capability.
"""
from __future__ import annotations

from typing import Optional

from llm.fallback import evaluate as fallback_evaluate
from llm.openrouter import call_llm
from llm.prompts import EVALUATOR_SYSTEM, EVALUATOR_USER_TEMPLATE
from llm.schemas import EvaluationResult
from slice.validation import sanitise_student_input, validate_llm_output


class EvaluatorAgent:
    """Evaluates student's Socratic answers or transfer task submissions."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def evaluate(
        self,
        student_response: str,
        misconception_id: str,
        topic: str,
        stage: str,
        target_reasoning: str,
        invariant: str,
        question_or_task: str,
    ) -> EvaluationResult:
        clean_response = sanitise_student_input(student_response)

        messages = [
            {"role": "system", "content": EVALUATOR_SYSTEM},
            {
                "role": "user",
                "content": EVALUATOR_USER_TEMPLATE.format(
                    topic=topic,
                    stage=stage,
                    misconception_id=misconception_id,
                    invariant=invariant,
                    question_or_task=question_or_task,
                    target_reasoning=target_reasoning,
                    student_response=clean_response,
                ),
            },
        ]

        raw = call_llm(messages=messages, schema=EvaluationResult, step="evaluator")
        validated = validate_llm_output(raw, EvaluationResult)

        if validated is not None:
            # Keep the core boundary-elimination loop deterministic when the
            # response contains an unambiguous contradiction or invariant.
            if misconception_id == "M1_INCOMPLETE_ELIMINATION":
                deterministic = fallback_evaluate(
                    student_response=clean_response,
                    misconception_id=misconception_id,
                    topic=topic,
                    stage=stage,
                    target_reasoning=target_reasoning,
                    question_or_task=question_or_task,
                )
                response_lower = clean_response.lower()
                has_invariant = any(
                    marker in response_lower
                    for marker in (
                        "mid + 1",
                        "mid+1",
                        "all indices",
                        "all elements",
                        "eliminated",
                        "ruled out",
                        "impossible",
                    )
                )
                has_incomplete_rule = any(
                    marker in response_lower
                    for marker in (
                        "left++",
                        "right--",
                        "move by one",
                        "only one",
                        "still works",
                    )
                )
                if has_invariant or has_incomplete_rule:
                    return deterministic
            return validated

        return fallback_evaluate(
            student_response=clean_response,
            misconception_id=misconception_id,
            topic=topic,
            stage=stage,
            target_reasoning=target_reasoning,
            question_or_task=question_or_task,
        )
