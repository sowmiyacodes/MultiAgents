"""
Socratic Agent.

Teaches through focused questions targeting the diagnosed misconception.
Rules:
1. One focused question at a time.
2. Target the specific diagnosed misconception.
3. Do not immediately reveal the answer.
4. Do not repeat angles within the same cycle.
"""
from __future__ import annotations

from typing import Optional

from llm.fallback import socratic_question as fallback_socratic
from llm.openrouter import call_llm
from llm.prompts import SOCRATIC_SYSTEM, SOCRATIC_USER_TEMPLATE
from llm.schemas import SocraticOutput
from slice.validation import sanitise_student_input, validate_llm_output


class SocraticAgent:
    """Generates focused Socratic questions based on angle and misconception."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def ask(
        self,
        misconception_id: str,
        angle_id: str,
        angle_description: str,
        topic: str,
        subconcept: Optional[str],
        used_questions: list[str],
        student_input: str,
    ) -> SocraticOutput:
        clean_input = sanitise_student_input(student_input)
        used_q_text = "\n".join(f"- {q}" for q in used_questions) if used_questions else "None"

        messages = [
            {"role": "system", "content": SOCRATIC_SYSTEM},
            {
                "role": "user",
                "content": SOCRATIC_USER_TEMPLATE.format(
                    topic=topic,
                    subconcept=subconcept or "general",
                    misconception_id=misconception_id,
                    angle_id=angle_id,
                    angle_description=angle_description,
                    used_questions=used_q_text,
                    student_input=clean_input,
                ),
            },
        ]

        raw = call_llm(messages=messages, schema=SocraticOutput, step="socratic")
        validated = validate_llm_output(raw, SocraticOutput)

        if validated is not None:
            return validated

        return fallback_socratic(misconception_id, angle_id, topic, used_questions)
