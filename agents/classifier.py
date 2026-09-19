"""
Question Classifier Agent.

Determines:
- Domain & Topic (e.g. binary_search, arrays, graphs, or generic DSA)
- Subconcept (if identifiable, e.g. boundary_update)
- Student intent (GENERAL_EXPLANATION, CONCEPTUAL_CONFUSION, etc.)
- Adaptive flag: True if adaptive Socratic tutoring is needed, False for general Q&A
"""
from __future__ import annotations

from typing import Optional

from llm.fallback import classify as fallback_classify
from llm.openrouter import call_llm
from llm.prompts import CLASSIFIER_SYSTEM, CLASSIFIER_USER_TEMPLATE
from llm.schemas import ClassificationResult
from slice.validation import sanitise_student_input, validate_llm_output


class QuestionClassifier:
    """Classifies incoming student queries into general Q&A or adaptive tutoring."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def classify(self, student_input: str) -> ClassificationResult:
        clean_input = sanitise_student_input(student_input)

        messages = [
            {"role": "system", "content": CLASSIFIER_SYSTEM},
            {"role": "user", "content": CLASSIFIER_USER_TEMPLATE.format(student_input=clean_input)},
        ]

        raw = call_llm(messages=messages, schema=ClassificationResult, step="classifier")
        validated = validate_llm_output(raw, ClassificationResult)

        if validated is not None:
            return validated

        return fallback_classify(clean_input)
