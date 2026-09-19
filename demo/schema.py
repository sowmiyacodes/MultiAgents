from pydantic import BaseModel, Field


class DiagnosticResult(BaseModel):
    misconception: str = Field(
        description=(
            "The diagnosed misconception. Use "
            "M1_INCOMPLETE_ELIMINATION, NONE, or UNCERTAIN."
        )
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the diagnosis from 0 to 1."
    )

    evidence: list[str] = Field(
        min_length=1,
        max_length=3,
        description="Concrete evidence from the student's attempt."
    )

    reasoning_pattern: str = Field(
        description="The reasoning pattern that appears to cause the error."
    )


class SocraticQuestion(BaseModel):
    angle_id: str = Field(
        description="The pedagogical angle used for this intervention."
    )

    question: str = Field(
        description="Exactly one Socratic question for the student."
    )

    pedagogical_goal: str = Field(
        description="What reasoning the question is intended to elicit."
    )

class StudentResponse(BaseModel):
    response: str = Field(
        description="The student's response to the Socratic question."
    )

class EvaluationResult(BaseModel):
    outcome: str = Field(
        description=(
            "Evaluation outcome. Use PASS, REINFORCE, or UNCERTAIN."
        )
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the evaluation from 0 to 1."
    )

    evidence: list[str] = Field(
        min_length=1,
        max_length=3,
        description=(
            "Concrete evidence from the student's response "
            "supporting the evaluation."
        )
    )

    reasoning_assessment: str = Field(
        description=(
            "Assessment of whether the student's reasoning shows "
            "understanding of complete boundary elimination."
        )
    )