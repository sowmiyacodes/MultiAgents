from pydantic import BaseModel, Field


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