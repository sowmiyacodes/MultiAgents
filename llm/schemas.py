"""
Pydantic schemas for all agent inputs and outputs.

These are the contracts between agents and the runtime.  ALL LLM output is
validated against one of these schemas before the runtime uses it.

The runtime (state machine) reads these validated models to decide transitions.
The LLM is never trusted to produce a transition directly — it produces
*evidence*, the runtime decides *what happens next*.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Enum types ────────────────────────────────────────────────────────────────

class StudentIntent(str, Enum):
    GENERAL_EXPLANATION = "GENERAL_EXPLANATION"
    DEBUGGING = "DEBUGGING"
    CONCEPTUAL_CONFUSION = "CONCEPTUAL_CONFUSION"
    SOLUTION_ATTEMPT = "SOLUTION_ATTEMPT"
    WRONG_ANSWER = "WRONG_ANSWER"
    CODE_REVIEW = "CODE_REVIEW"
    INTERVIEW_PREPARATION = "INTERVIEW_PREPARATION"
    PRACTICE = "PRACTICE"
    ADAPTIVE_LEARNING = "ADAPTIVE_LEARNING"


class Severity(str, Enum):
    FOUNDATIONAL = "foundational"
    MODERATE = "moderate"
    SURFACE = "surface"


class EvalResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"


class MasteryStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    DIAGNOSED = "DIAGNOSED"
    IN_PROGRESS = "IN_PROGRESS"
    PROVISIONALLY_MASTERED = "PROVISIONALLY_MASTERED"
    MASTERED = "MASTERED"
    REGRESSED = "REGRESSED"


class PlannerAction(str, Enum):
    PRACTICE_SAME_CONCEPT = "PRACTICE_SAME_CONCEPT"
    PRACTICE_VARIANT = "PRACTICE_VARIANT"
    INTRODUCE_PREREQUISITE = "INTRODUCE_PREREQUISITE"
    REVIEW_MISCONCEPTION = "REVIEW_MISCONCEPTION"
    MOVE_TO_NEXT_TOPIC = "MOVE_TO_NEXT_TOPIC"
    SPACED_REVIEW = "SPACED_REVIEW"
    HUMAN_REVIEW = "HUMAN_REVIEW"


# ── Classifier ────────────────────────────────────────────────────────────────

class ClassificationResult(BaseModel):
    """Output of the Question Classifier Agent."""

    domain: str = Field(description="DSA domain (e.g., binary_search, arrays, graphs)")
    topic: str = Field(description="Specific topic within the domain")
    subconcept: Optional[str] = Field(
        default=None, description="Subconcept if identifiable (e.g., boundary_update)"
    )
    difficulty: Optional[str] = Field(
        default=None, description="Estimated difficulty: easy, medium, hard"
    )
    intent: StudentIntent = Field(description="Student's intent")
    adaptive: bool = Field(
        description="True if adaptive tutoring is needed; False for general Q&A"
    )
    reasoning: str = Field(
        description="Brief reasoning for classification (1-2 sentences)"
    )

    @field_validator("intent", mode="before")
    @classmethod
    def normalise_intent(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v

    @field_validator("domain", "topic", mode="before")
    @classmethod
    def normalise_topic(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_lower = v.lower()
            if "binary" in v_lower or "bsearch" in v_lower or ("search" in v_lower and "tree" not in v_lower) or "boundary" in v_lower or "pointer" in v_lower:
                return "binary_search"
            if "array" in v_lower:
                return "arrays"
            if "string" in v_lower:
                return "strings"
            if "hash" in v_lower:
                return "hashing"
            if "link" in v_lower:
                return "linked_lists"
            if "stack" in v_lower:
                return "stacks"
            if "queue" in v_lower and "priority" not in v_lower:
                return "queues"
            if "tree" in v_lower or "bst" in v_lower:
                return "trees"
            if "graph" in v_lower:
                return "graphs"
            if "heap" in v_lower or "priority" in v_lower:
                return "heaps"
            if "recur" in v_lower:
                return "recursion"
            if "dp" in v_lower or "dynamic" in v_lower:
                return "dynamic_programming"
            if "greedy" in v_lower:
                return "greedy"
            if "sort" in v_lower:
                return "sorting"
            if "backtrack" in v_lower:
                return "backtracking"
            if "pointer" in v_lower or "update" in v_lower or "left" in v_lower or "right" in v_lower:
                return "binary_search"
        return v

    @field_validator("subconcept", mode="before")
    @classmethod
    def normalise_subconcept(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_lower = v.lower()
            if any(k in v_lower for k in ("boundary", "pointer", "left", "right", "increment", "update")):
                return "boundary_update"
            if "loop" in v_lower or "condition" in v_lower:
                return "loop_condition"
            if "first" in v_lower:
                return "first_occurrence"
            if "last" in v_lower:
                return "last_occurrence"
            if "rotate" in v_lower:
                return "rotated_array"
        return v





# ── Diagnostic ────────────────────────────────────────────────────────────────

class DiagnosisResult(BaseModel):
    """Output of the Diagnostic Agent."""

    misconception_id: str = Field(
        description="Misconception identifier (e.g., M1_INCOMPLETE_ELIMINATION)"
    )
    concept: str = Field(description="The concept being misunderstood")
    evidence: list[str] = Field(
        min_length=1,
        max_length=5,
        description="Concrete evidence from the student's attempt/text",
    )
    severity: str = Field(
        description="foundational, moderate, or surface"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in diagnosis (0–1)")
    invariant: str = Field(
        description="The invariant the student is violating or not understanding"
    )
    is_known: bool = Field(
        default=True,
        description="Whether this misconception is in the local knowledge base",
    )
    topic: str = Field(default="", description="DSA topic being diagnosed")
    subconcept: str = Field(default="", description="Subconcept being diagnosed")
    intent: Optional[str] = Field(default="CONCEPTUAL_CONFUSION", description="Detected student intent")
    wants_direct_explanation: bool = Field(default=False, description="Whether the student explicitly asked for direct explanation")


# ── Socratic ──────────────────────────────────────────────────────────────────

class SocraticOutput(BaseModel):
    """Output of the Socratic Agent."""

    angle_id: str = Field(description="The Socratic angle used (e.g., ELIMINATED_RANGE_PROOF)")
    question: str = Field(description="The focused Socratic question to ask the student")
    pedagogical_goal: str = Field(
        description="What reasoning this question is designed to elicit"
    )
    hint: Optional[str] = Field(
        default=None, description="Optional subtle hint if context warrants it"
    )


# ── Transfer Task ─────────────────────────────────────────────────────────────

class TransferTask(BaseModel):
    """Output of the Transfer Task Agent."""

    task_id: str = Field(description="Unique transfer task identifier")
    problem: str = Field(
        description="The complete fresh transfer problem statement for the student"
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Problem context: array, indices, values, target, etc.",
    )
    target_reasoning: str = Field(
        description="The reasoning the student must demonstrate to pass"
    )
    hint: Optional[str] = Field(
        default=None, description="Hint if contextually appropriate"
    )


# ── Evaluator ─────────────────────────────────────────────────────────────────

class EvaluationResult(BaseModel):
    """Output of the Evaluator Agent."""

    result: EvalResult = Field(description="PASS, FAIL, or PARTIAL")
    reasoning_correct: bool = Field(
        description="Whether the student's reasoning (not just the answer) is correct"
    )
    transfer_success: bool = Field(
        description="Whether the student successfully applied the reasoning to the new context"
    )
    misconception_recurred: bool = Field(
        description="Whether the originally diagnosed misconception appeared again"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in evaluation (0–1)")
    feedback: str = Field(
        description="Educational feedback for the student (2-4 sentences)"
    )
    evidence: list[str] = Field(
        min_length=1,
        max_length=5,
        description="Evidence supporting the evaluation",
    )
    reasoning_quality: str = Field(
        default="adequate",
        description="Reasoning quality: poor, partial, good, excellent"
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Error type if incorrect: e.g. off_by_one, wrong_boundary, infinite_loop, conceptual, none"
    )
    concept: Optional[str] = Field(
        default=None,
        description="Concept evaluated"
    )
    mastery_delta: float = Field(
        default=0.0,
        description="Mastery score delta (-0.3 to +0.3)"
    )
    needs_another_attempt: bool = Field(
        default=False,
        description="Whether another attempt is required"
    )

    @field_validator("result", mode="before")
    @classmethod
    def normalise_result(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v


# ── Targeted Tutor ────────────────────────────────────────────────────────────

class TutorOutput(BaseModel):
    """Output of the Targeted Tutor Agent."""

    misconception_stated: str = Field(
        description="Clear, direct statement of the misconception being addressed"
    )
    explanation: str = Field(description="The correct reasoning explained clearly")
    worked_example: str = Field(
        description="A concrete worked example demonstrating correct reasoning"
    )
    apply_prompt: str = Field(
        description="A prompt asking the student to apply the explained reasoning"
    )
    key_insight: str = Field(
        description="The single most important takeaway (one sentence)"
    )


# ── Planner ───────────────────────────────────────────────────────────────────

class PlannerOutput(BaseModel):
    """Output of the Planner Agent."""

    action: PlannerAction = Field(description="The next recommended learning action")
    reason: str = Field(description="Pedagogical rationale for selecting this action")
    next_topic: Optional[str] = Field(
        default=None, description="Next topic if the action is MOVE_TO_NEXT_TOPIC"
    )
    next_subconcept: Optional[str] = Field(
        default=None, description="Next subconcept if moving on"
    )
    message: str = Field(
        description="A message to present to the student about what comes next"
    )
    spaced_review_days: Optional[int] = Field(
        default=None, description="Days until spaced review if action is SPACED_REVIEW"
    )

    @field_validator("action", mode="before")
    @classmethod
    def normalise_action(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.upper()
        return v
