from pathlib import Path

from slice.llm import complete

from .schema import (
    DiagnosticResult,
    SocraticQuestion,
    EvaluationResult,
    TransferTask,
)


PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def _read_prompt(filename: str) -> str:
    path = PROMPT_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {path}"
        )

    return path.read_text(encoding="utf-8")


class DiagnosticAgent:
    name = "diagnostic"

    def run(
        self,
        ctx,
        student_attempt: str,
    ) -> DiagnosticResult:

        prompt = _read_prompt("diagnostic.md")

        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": (
                    "STUDENT BINARY-SEARCH ATTEMPT:\n\n"
                    f"{student_attempt}\n\n"
                    "Diagnose the reasoning."
                ),
            },
        ]

        return complete(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=DiagnosticResult,
            step="diagnostic",
        )


class SocraticAgent:
    name = "socratic"

    def run(
        self,
        ctx,
        student_attempt: str,
        diagnostic: dict,
        angle: dict,
    ) -> SocraticQuestion:

        prompt = _read_prompt("socratic.md")

        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": (
                    "STUDENT ATTEMPT:\n"
                    f"{student_attempt}\n\n"
                    "DIAGNOSTIC:\n"
                    f"{diagnostic}\n\n"
                    "SELECTED SOCRATIC ANGLE:\n"
                    f"{angle}\n\n"
                    "Generate one Socratic question."
                ),
            },
        ]

        return complete(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=SocraticQuestion,
            step="socratic",
        )


class EvaluatorAgent:
    name = "evaluator"

    def run(
        self,
        ctx,
        student_attempt: str,
        diagnostic: dict,
        question: dict,
        student_response: str,
        stage: str = "socratic",
        transfer_task: dict | None = None,
    ) -> EvaluationResult:

        prompt = _read_prompt("evaluator.md")

        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": (
                    f"EVALUATION STAGE:\n{stage}\n\n"
                    "ORIGINAL STUDENT ATTEMPT:\n"
                    f"{student_attempt}\n\n"
                    "DIAGNOSTIC:\n"
                    f"{diagnostic}\n\n"
                    "QUESTION OR TRANSFER TASK:\n"
                    f"{question}\n\n"
                    "STUDENT RESPONSE:\n"
                    f"{student_response}\n\n"
                    "TRANSFER TASK DETAILS:\n"
                    f"{transfer_task}\n\n"
                    "Evaluate the student's reasoning."
                ),
            },
        ]

        return complete(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=EvaluationResult,
            step="evaluator",
        )


class TransferAgent:
    name = "transfer"

    def run(
        self,
        ctx,
        diagnostic: dict,
        task: dict,
    ) -> TransferTask:

        prompt = _read_prompt("transfer.md")

        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": (
                    "DIAGNOSTIC:\n"
                    f"{diagnostic}\n\n"
                    "TRANSFER TASK:\n"
                    f"{task}\n\n"
                    "Generate the fresh transfer task."
                ),
            },
        ]

        return complete(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=TransferTask,
            step="transfer",
        )