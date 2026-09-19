from slice.llm import complete
from slice.records import RunState

from .agents import (
    DiagnosticAgent,
    SocraticAgent,
    EvaluatorAgent,
    TransferAgent,
)

from .angles import (
    ANGLES,
    TRANSFER_TASKS,
    TUTOR_EXPLANATION,
)


def build_flow(call=complete):

    diagnostic_agent = DiagnosticAgent()
    socratic_agent = SocraticAgent()
    evaluator_agent = EvaluatorAgent()
    transfer_agent = TransferAgent()

    def get_used_angles(ctx):
        return {
            record.payload.get("angle_id")
            for record in ctx.history("socratic")
            if record.payload.get("angle_id")
        }

    def get_next_angle(ctx):
        used = get_used_angles(ctx)

        for angle in ANGLES:
            if angle["id"] not in used:
                return angle

        return None

    def handle_diagnostic(ctx):

        student = ctx.latest("student_attempt")

        if student is None:
            raise ValueError(
                "No student_attempt record found."
            )

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

    def handle_gating(ctx):

        diagnostic = ctx.latest("diagnostic")

        if diagnostic is None:
            raise ValueError(
                "No diagnostic result found."
            )

        if diagnostic["misconception"] != (
            "M1_INCOMPLETE_ELIMINATION"
        ):

            ctx.append(
                "learning_state",
                {
                    "misconception": diagnostic["misconception"],
                    "status": "NO_TARGET_MISCONCEPTION",
                    "successful_angles": [],
                    "reinforced_angles": [],
                    "transfer_passed": False,
                    "recommended_next_action": (
                        "Continue with normal instruction."
                    ),
                },
                produced_by="learning_state",
            )

            return RunState.COMPLETE

        evaluators = ctx.history("evaluator")

        if evaluators:

            last_eval = evaluators[-1].payload

            if (
                last_eval.get("stage") == "socratic"
                and last_eval.get("outcome") == "PASS"
            ):

                transfer_records = ctx.history("transfer")

                if not transfer_records:

                    task_index = 0

                    if task_index >= len(TRANSFER_TASKS):
                        task_index = (
                            len(TRANSFER_TASKS) - 1
                        )

                    task = TRANSFER_TASKS[task_index]

                    result = transfer_agent.run(
                        ctx,
                        diagnostic,
                        task,
                    )

                    ctx.append(
                        "transfer",
                        result.model_dump(),
                        produced_by="transfer",
                    )

                    return RunState.AWAITING_EXPERT

        angle = get_next_angle(ctx)

        if angle is None:

            ctx.append(
                "tutor",
                {
                    "type": "worked_example",
                    "explanation": TUTOR_EXPLANATION,
                    "reason": (
                        "All bounded Socratic angles were exhausted "
                        "without sufficient evidence of understanding."
                    ),
                },
                produced_by="tutor",
            )

            ctx.append(
                "learning_state",
                {
                    "misconception": (
                        "M1_INCOMPLETE_ELIMINATION"
                    ),
                    "status": "REINFORCEMENT_NEEDED",
                    "successful_angles": [],
                    "reinforced_angles": [
                        record.payload.get("angle_id")
                        for record in ctx.history("socratic")
                        if record.payload.get("angle_id")
                    ],
                    "transfer_passed": False,
                    "recommended_next_action": (
                        "Use the worked example and revisit "
                        "boundary elimination in a future encounter."
                    ),
                },
                produced_by="learning_state",
            )

            return RunState.COMPLETE

        student = ctx.latest("student_attempt")

        result = socratic_agent.run(
            ctx,
            student["text"],
            diagnostic,
            angle,
        )

        ctx.append(
            "socratic",
            result.model_dump(),
            produced_by="socratic",
        )

        return RunState.AWAITING_EXPERT

    def handle_evaluator(ctx):

        student = ctx.latest("student_attempt")
        diagnostic = ctx.latest("diagnostic")
        student_response = ctx.latest("student_response")
        socratic = ctx.latest("socratic")
        transfer = ctx.latest("transfer")

        if student is None:
            raise ValueError(
                "No student_attempt record found."
            )

        if diagnostic is None:
            raise ValueError(
                "No diagnostic result found."
            )

        if student_response is None:
            raise ValueError(
                "No student_response record found."
            )

        response = student_response["response"]

        # -------------------------------------------------
        # Transfer evaluation
        # -------------------------------------------------

        if transfer is not None:

            transfer_records = ctx.history("transfer")
            response_records = ctx.history("student_response")

            if (
                transfer_records
                and response_records[-1].seq
                > transfer_records[-1].seq
            ):

                result = evaluator_agent.run(
                    ctx,
                    student["text"],
                    diagnostic,
                    transfer,
                    response,
                    stage="transfer",
                    transfer_task=transfer,
                )

                payload = result.model_dump()
                payload["stage"] = "transfer"

                ctx.append(
                    "evaluator",
                    payload,
                    produced_by="evaluator",
                )

                if result.outcome == "PASS":

                    ctx.append(
                        "learning_state",
                        {
                            "misconception": (
                                "M1_INCOMPLETE_ELIMINATION"
                            ),
                            "status": "TRANSFER_PASSED",
                            "successful_angles": [
                                record.payload.get("angle_id")
                                for record in ctx.history("socratic")
                                if record.payload.get("angle_id")
                            ],
                            "reinforced_angles": [],
                            "transfer_passed": True,
                            "recommended_next_action": (
                                "Use a related binary-search "
                                "boundary problem in the next encounter."
                            ),
                        },
                        produced_by="learning_state",
                    )

                    return RunState.COMPLETE

                if result.outcome == "REINFORCE":

                    ctx.append(
                        "learning_state",
                        {
                            "misconception": (
                                "M1_INCOMPLETE_ELIMINATION"
                            ),
                            "status": (
                                "TRANSFER_REINFORCEMENT_NEEDED"
                            ),
                            "successful_angles": [],
                            "reinforced_angles": [
                                record.payload.get("angle_id")
                                for record in ctx.history("socratic")
                                if record.payload.get("angle_id")
                            ],
                            "transfer_passed": False,
                            "recommended_next_action": (
                                "Return to a different Socratic "
                                "angle before attempting transfer again."
                            ),
                        },
                        produced_by="learning_state",
                    )

                    return RunState.GATING

                return RunState.GATING

        # -------------------------------------------------
        # Socratic evaluation
        # -------------------------------------------------

        if socratic is None:
            raise ValueError(
                "No Socratic question found."
            )

        result = evaluator_agent.run(
            ctx,
            student["text"],
            diagnostic,
            socratic,
            response,
            stage="socratic",
        )

        payload = result.model_dump()
        payload["stage"] = "socratic"

        ctx.append(
            "evaluator",
            payload,
            produced_by="evaluator",
        )

        angle_id = socratic.get(
            "angle_id",
            "UNKNOWN",
        )

        if result.outcome == "PASS":

            ctx.append(
                "learning_state",
                {
                    "misconception": (
                        "M1_INCOMPLETE_ELIMINATION"
                    ),
                    "status": "SOCRATIC_PASS",
                    "successful_angles": [
                        angle_id
                    ],
                    "reinforced_angles": [],
                    "transfer_passed": False,
                    "recommended_next_action": (
                        "Test the reasoning on a fresh transfer task."
                    ),
                },
                produced_by="learning_state",
            )

            return RunState.GATING

        if result.outcome == "REINFORCE":

            ctx.append(
                "learning_state",
                {
                    "misconception": (
                        "M1_INCOMPLETE_ELIMINATION"
                    ),
                    "status": "REINFORCE",
                    "successful_angles": [],
                    "reinforced_angles": [
                        angle_id
                    ],
                    "transfer_passed": False,
                    "recommended_next_action": (
                        "Ask a new Socratic question from "
                        "a different angle."
                    ),
                },
                produced_by="learning_state",
            )

            return RunState.GATING

        ctx.append(
            "learning_state",
            {
                "misconception": (
                    "M1_INCOMPLETE_ELIMINATION"
                ),
                "status": "UNCERTAIN",
                "successful_angles": [],
                "reinforced_angles": [
                    angle_id
                ],
                "transfer_passed": False,
                "recommended_next_action": (
                    "Use another Socratic angle."
                ),
            },
            produced_by="learning_state",
        )

        return RunState.GATING

    return type(
        "BoundaryLoopFlow",
        (),
        {
            "name": "boundary_loop",
            "handlers": {
                RunState.DRAFTING: handle_diagnostic,
                RunState.GATING: handle_gating,
                RunState.EVALUATING: handle_evaluator,
            },
        },
    )()