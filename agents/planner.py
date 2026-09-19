"""
Planner Agent.

Determines the next learning action based on mastery evidence.
Actions:
- PRACTICE_SAME_CONCEPT
- PRACTICE_VARIANT
- INTRODUCE_PREREQUISITE
- REVIEW_MISCONCEPTION
- MOVE_TO_NEXT_TOPIC
- SPACED_REVIEW
- HUMAN_REVIEW
"""
from __future__ import annotations

from typing import Optional

from llm.fallback import plan_next as fallback_plan
from llm.openrouter import call_llm
from llm.prompts import PLANNER_SYSTEM, PLANNER_USER_TEMPLATE
from llm.schemas import PlannerOutput
from slice.validation import validate_llm_output


class PlannerAgent:
    """Plans pedagogical trajectory based on verified learning evidence."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def plan(
        self,
        student_id: str,
        topic: str,
        subconcept: str,
        misconception_id: str,
        mastery_status: str,
        transfer_passed: bool,
        failed_transfer_count: int,
        successful_transfer_count: int,
        session_count: int = 1,
        previous_encounters: str = "None",
    ) -> PlannerOutput:
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM},
            {
                "role": "user",
                "content": PLANNER_USER_TEMPLATE.format(
                    student_id=student_id,
                    topic=topic,
                    subconcept=subconcept,
                    misconception_id=misconception_id,
                    mastery_status=mastery_status,
                    transfer_passed=transfer_passed,
                    failed_transfer_count=failed_transfer_count,
                    successful_transfer_count=successful_transfer_count,
                    session_count=session_count,
                    previous_encounters=previous_encounters,
                ),
            },
        ]

        raw = call_llm(messages=messages, schema=PlannerOutput, step="planner")
        validated = validate_llm_output(raw, PlannerOutput)

        if validated is not None:
            return validated

        return fallback_plan(
            topic=topic,
            subconcept=subconcept,
            mastery_status=mastery_status,
            transfer_passed=transfer_passed,
            failed_count=failed_transfer_count,
            success_count=successful_transfer_count,
        )
