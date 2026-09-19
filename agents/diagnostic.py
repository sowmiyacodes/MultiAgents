"""
Diagnostic Agent.

Identifies the student's specific misconception from their code/explanation.
Strictly evidence-driven: does not shotgun-guess unrelated concepts.
"""
from __future__ import annotations

from typing import Optional

from llm.fallback import diagnose as fallback_diagnose
from llm.openrouter import call_llm
from llm.prompts import DIAGNOSTIC_SYSTEM, DIAGNOSTIC_USER_TEMPLATE
from llm.schemas import DiagnosisResult
from slice.validation import sanitise_student_input, validate_llm_output


class DiagnosticAgent:
    """Diagnoses the precise misconception and understanding in student's input."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def diagnose(
        self,
        student_input: str,
        topic: Optional[str] = None,
        subconcept: Optional[str] = None,
    ) -> DiagnosisResult:
        clean_input = sanitise_student_input(student_input)
        
        # If topic is not provided, detect it from student input
        if not topic or topic == "general":
            from llm.fallback import classify
            clf = classify(clean_input)
            topic = clf.topic
            if not subconcept:
                subconcept = clf.subconcept

        messages = [
            {"role": "system", "content": DIAGNOSTIC_SYSTEM},
            {
                "role": "user",
                "content": DIAGNOSTIC_USER_TEMPLATE.format(
                    topic=topic,
                    subconcept=subconcept or "general",
                    student_input=clean_input,
                ),
            },
        ]

        raw = call_llm(messages=messages, schema=DiagnosisResult, step="diagnostic")
        validated = validate_llm_output(raw, DiagnosisResult)

        if validated is not None:
            if not validated.topic:
                validated.topic = topic
            if not validated.subconcept:
                validated.subconcept = subconcept or "general"
            return validated

        return fallback_diagnose(clean_input, topic, subconcept)
