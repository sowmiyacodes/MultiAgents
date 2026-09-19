from slice.llm import complete
from slice.records import RunState

from .agents import DiagnosticAgent, SocraticAgent, EvaluatorAgent
from .angles import ANGLES


def build_flow(call=complete):
    diagnostic_agent = DiagnosticAgent()
    socratic_agent = SocraticAgent()
    evaluator_agent = EvaluatorAgent()

    def handle_diagnostic(ctx):
        student = ctx.latest("student_attempt")

        if student is None:
            raise ValueError("No student_attempt record found.")

        result = diagnostic_agent.run(
            ctx,
            student["text"],
        )

        ctx.append(
            "diagnostic",
            result.model_dump(),
            produced_by="diagnostic",
        )

        return RunState.GATING

    def handle_socratic(ctx):
        student = ctx.latest("student_attempt")
        diagnostic = ctx.latest("diagnostic")

        if student is None:
            raise ValueError("No student_attempt record found.")

        if diagnostic is None:
            raise ValueError("No diagnostic result found.")

        if diagnostic["misconception"] != "M1_INCOMPLETE_ELIMINATION":
            ctx.append(
                "socratic",
                {
                    "angle_id": "NOT_REQUIRED",
                    "question": (
                        "No Socratic intervention was generated because "
                        "the target misconception was not diagnosed."
                    ),
                    "pedagogical_goal": "No intervention required.",
                },
                produced_by="socratic",
            )

            return RunState.COMPLETE

        used_angles = {
            record.payload["angle_id"]
            for record in ctx.history("socratic")
            if "angle_id" in record.payload
        }

        available_angles = [
            angle
            for angle in ANGLES
            if angle["id"] not in used_angles
        ]

        if not available_angles:
            raise ValueError("No unused Socratic angles remain.")

        selected_angle = available_angles[0]

        result = socratic_agent.run(
            ctx,
            student["text"],
            diagnostic,
            selected_angle,
        )

        ctx.append(
            "socratic",
            result.model_dump(),
            produced_by="socratic",
        )

        return RunState.COMPLETE

    def handle_evaluator(ctx):
        student = ctx.latest("student_attempt")
        diagnostic = ctx.latest("diagnostic")
        socratic = ctx.latest("socratic")
        response = ctx.latest("student_response")

        if student is None:
            raise ValueError("No student_attempt record found.")

        if diagnostic is None:
            raise ValueError("No diagnostic result found.")

        if socratic is None:
            raise ValueError("No socratic question found.")

        if response is None:
            raise ValueError("No student_response record found.")

        result = evaluator_agent.run(
            ctx,
            student["text"],
            diagnostic,
            socratic,
            response["response"],
        )

        ctx.append(
            "evaluator",
            result.model_dump(),
            produced_by="evaluator",
        )

        return RunState.COMPLETE

    return type(
        "BoundaryLoopFlow",
        (),
        {
            "name": "boundary_loop",
            "handlers": {
                RunState.DRAFTING: handle_diagnostic,
                RunState.GATING: handle_socratic,
            },
        },
    )()