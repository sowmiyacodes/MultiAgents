from typing import Literal
from pydantic import BaseModel, Field

PlannerActionType = Literal[
    "ASK_SOCRATIC",
    "ASK_TRANSFER",
    "BACKWARD_REMEDIATE",
    "REINFORCE",
    "COMPLETE",
]

VALID_PLANNER_ACTIONS = {
    "ASK_SOCRATIC",
    "ASK_TRANSFER",
    "BACKWARD_REMEDIATE",
    "REINFORCE",
    "COMPLETE",
}



class DiagnosticResult(BaseModel):
    misconception: str = Field(
        description="The diagnosed misconception identifier."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the diagnosis."
    )

    evidence: list[str] = Field(
        min_length=1,
        max_length=3,
        description="Concrete evidence from the student's attempt."
    )

    reasoning_pattern: str = Field(
        description="Description of the student's reasoning pattern."
    )


class SocraticQuestion(BaseModel):
    angle_id: str = Field(
        description="The Socratic angle used."
    )

    question: str = Field(
        description="The Socratic question."
    )

    pedagogical_goal: str = Field(
        description="What reasoning the question is intended to elicit."
    )


class StudentResponse(BaseModel):
    response: str = Field(
        description="The student's response."
    )


class EvaluationResult(BaseModel):
    outcome: str = Field(
        description="Evaluation outcome: PASS, REINFORCE, or UNCERTAIN."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the evaluation."
    )

    evidence: list[str] = Field(
        min_length=1,
        max_length=3,
        description="Concrete evidence from the student's response."
    )

    reasoning_assessment: str = Field(
        description="Assessment of the student's reasoning."
    )


class TransferTask(BaseModel):
    task_id: str = Field(
        description="Identifier for the transfer task."
    )

    prompt: str = Field(
        description="A fresh binary-search reasoning task."
    )

    target_reasoning: str = Field(
        description="The reasoning the student should demonstrate."
    )


class BackwardLoopRecord(BaseModel):
    reason: str = Field(
        description="Reason the backward loop was triggered."
    )

    wrong_socratic_count: int = Field(
        description="Number of wrong Socratic answers that triggered the loop."
    )

    backward_loop_count: int = Field(
        description="How many backward loops have occurred in this run."
    )

    misconception: str = Field(
        description="The targeted misconception being revisited."
    )


class LearningState(BaseModel):
    misconception: str = Field(
        description="The tracked misconception."
    )

    status: str = Field(
        description="Current learning status."
    )

    successful_angles: list[str] = Field(
        default_factory=list
    )

    reinforced_angles: list[str] = Field(
        default_factory=list
    )

    transfer_passed: bool = False

    recommended_next_action: str = Field(
        description="Recommended next action for a future encounter."
    )

    wrong_socratic_count: int = 0
    backward_loop_count: int = 0


class PlannerDecision(BaseModel):
    action: str = Field(
        description="Allowed pedagogical actions: ASK_SOCRATIC, ASK_TRANSFER, BACKWARD_REMEDIATE, REINFORCE, COMPLETE."
    )
    reason: str = Field(
        description="Pedagogical rationale for selecting this action."
    )
    pedagogical_goal: str = Field(
        description="Specific pedagogical goal or concept focus for this step."
    )
    preferred_angle: str = Field(
        description="Preferred angle identifier or strategy for the tutor."
    )
    difficulty: str = Field(
        default="medium",
        description="Target difficulty level (e.g. foundational, easy, medium, hard)."
    )
    focus: str = Field(
        default="boundary_elimination",
        description="Core focus of the pedagogical intervention."
    )


class TutorResponse(BaseModel):
    phase: str = Field(
        description="Tutoring phase: 'socratic', 'transfer', or 'explanation'."
    )
    question: str = Field(
        description="Student-facing Socratic question, transfer task prompt, or explanation text."
    )
    pedagogical_goal: str = Field(
        description="What reasoning this question or task is intended to elicit."
    )
    angle_id: str = Field(
        default="FOUNDATIONAL",
        description="The reasoning angle or task ID used."
    )
    explanation: str | None = Field(
        default=None,
        description="Short worked explanation when explicitly requested."
    )
    difficulty: str = Field(
        default="medium",
        description="Difficulty level of the question or task."
    )