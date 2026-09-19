"""
Transfer Task Agent.

Generates a fresh transfer problem that differs from the original example,
testing if the student can transfer the reasoning to a novel scenario.
"""
from __future__ import annotations

from typing import Optional

from llm.fallback import transfer_task as fallback_transfer
from llm.openrouter import call_llm
from llm.prompts import TRANSFER_SYSTEM, TRANSFER_USER_TEMPLATE
from llm.schemas import TransferTask
from slice.validation import validate_llm_output


class TransferAgent:
    """Generates fresh transfer tasks testing the acquired reasoning."""

    def __init__(self, model: Optional[str] = None):
        self.model = model

    def generate(
        self,
        misconception_id: str,
        topic: str,
        subconcept: Optional[str],
        target_reasoning: str,
        original_example: str,
        previous_tasks: list[str],
    ) -> TransferTask:
        prev_tasks_text = "\n".join(f"- {t}" for t in previous_tasks) if previous_tasks else "None"

        messages = [
            {"role": "system", "content": TRANSFER_SYSTEM},
            {
                "role": "user",
                "content": TRANSFER_USER_TEMPLATE.format(
                    topic=topic,
                    subconcept=subconcept or "general",
                    misconception_id=misconception_id,
                    target_reasoning=target_reasoning,
                    original_example=original_example,
                    previous_tasks=prev_tasks_text,
                ),
            },
        ]

        raw = call_llm(messages=messages, schema=TransferTask, step="transfer")
        validated = validate_llm_output(raw, TransferTask)

        if validated is not None:
            return validated

        return fallback_transfer(misconception_id, topic, previous_tasks)
