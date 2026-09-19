"""
Execution and Token Budgets for the Tutoring System.

Enforces deterministic limits outside the LLM:
- Socratic attempt limits (e.g. 3 attempts before targeted tutoring)
- Agent call limits per session (prevents run-away agent loops)
- Token fences (checked before requests are dispatched)
"""
from __future__ import annotations


class TutorBudgetExceeded(RuntimeError):
    """Raised when a tutoring budget fence is breached."""


class TutorBudget:
    """Tracks and enforces limits during an active tutoring session."""

    def __init__(
        self,
        max_socratic_attempts: int = 3,
        max_agent_calls: int = 30,
        max_tokens: int = 250000,
    ) -> None:
        self.max_socratic_attempts = max_socratic_attempts
        self.max_agent_calls = max_agent_calls
        self.max_tokens = max_tokens

        self.socratic_attempts: int = 0
        self.agent_calls: int = 0
        self.tokens_used: int = 0
        self.tutor_attempts: int = 0

    def bump_agent_call(self, agent_name: str = "") -> int:
        self.agent_calls += 1
        if self.agent_calls > self.max_agent_calls:
            raise TutorBudgetExceeded(
                f"Agent call budget exceeded ({self.agent_calls}/{self.max_agent_calls}). "
                "Stopping session to prevent unbounded execution."
            )
        return self.agent_calls

    def record_socratic_attempt(self) -> int:
        self.socratic_attempts += 1
        return self.socratic_attempts

    def socratic_attempts_exhausted(self) -> bool:
        return self.socratic_attempts >= self.max_socratic_attempts

    def record_tutor_attempt(self) -> int:
        self.tutor_attempts += 1
        return self.tutor_attempts

    def tutor_attempts_exhausted(self) -> bool:
        return self.tutor_attempts >= 2

    def record_tokens(self, count: int) -> int:
        self.tokens_used += count
        if self.tokens_used > self.max_tokens:
            raise TutorBudgetExceeded(
                f"Token budget exceeded ({self.tokens_used}/{self.max_tokens})."
            )
        return self.tokens_used
