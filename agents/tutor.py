"""
Targeted Tutor Agent.

Activated after repeated Socratic failure.
Provides an explicit explanation:
1. State misconception clearly.
2. Explain the correct underlying logic.
3. Provide a concrete worked example.
4. Prompt the student to apply it.
"""
from __future__ import annotations

from typing import Optional

from llm.fallback import tutor_explanation as fallback_tutor
from llm.openrouter import call_llm
from llm.prompts import TUTOR_SYSTEM, TUTOR_USER_TEMPLATE
from llm.schemas import TutorOutput
from slice.validation import sanitise_student_input, validate_llm_output


class TargetedTutorAgent:
    """Delivers direct, targeted remediation when Socratic loops exhaust."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def explain(
        self,
        misconception_id: str,
        invariant: str,
        topic: str,
        subconcept: Optional[str],
        student_input: str,
    ) -> TutorOutput:
        clean_input = sanitise_student_input(student_input)

        messages = [
            {"role": "system", "content": TUTOR_SYSTEM},
            {
                "role": "user",
                "content": TUTOR_USER_TEMPLATE.format(
                    topic=topic,
                    subconcept=subconcept or "general",
                    misconception_id=misconception_id,
                    invariant=invariant,
                    student_input=clean_input,
                ),
            },
        ]

        raw = call_llm(messages=messages, schema=TutorOutput, step="tutor")
        validated = validate_llm_output(raw, TutorOutput)

        if validated is not None:
            return validated

        return fallback_tutor(
            misconception_id=misconception_id,
            topic=topic,
            student_input=clean_input,
        )
