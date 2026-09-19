from pathlib import Path

from slice.llm import complete

from .schema import DiagnosticResult, SocraticQuestion


PROMPT_DIR = Path(__file__).parent / "prompts"


def _read_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


class DiagnosticAgent:
    name = "diagnostic"

    def run(self, ctx, student_attempt: str) -> DiagnosticResult:
        prompt = _read_prompt("diagnostic.md")

        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": (
                    "Diagnose the following binary-search attempt.\n\n"
                    "STUDENT ATTEMPT:\n"
                    f"{student_attempt}"
                ),
            },
        ]

        result = complete(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=DiagnosticResult,
            step="diagnostic",
        )

        return result


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

        used_angles = [
            record.payload["angle_id"]
            for record in ctx.history("socratic")
        ]

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
                    "DIAGNOSTIC RESULT:\n"
                    f"{diagnostic}\n\n"
                    "SELECTED PEDAGOGICAL ANGLE:\n"
                    f"{angle}\n\n"
                    "ALREADY USED ANGLES:\n"
                    f"{used_angles}\n\n"
                    "Generate exactly one Socratic question."
                ),
            },
        ]

        result = complete(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=SocraticQuestion,
            step="socratic",
        )

        return result