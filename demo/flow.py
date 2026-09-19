from slice.llm import complete
from slice.records import RunState

from .agents import (
    DiagnosticAgent,
    SocraticAgent,
    EvaluatorAgent,
    TransferAgent,
    PlannerAgent,
    TutorAgentR8,
)

from .angles import (
    ANGLES,
    TRANSFER_TASKS,
    TUTOR_EXPLANATION,
    get_concept_angles,
    get_concept_transfer_tasks,
    get_concept_explanation,
)

from .schema import BackwardLoopRecord
from .concept_registry import get_concept, get_misconception, is_concept_supported
from .query_classifier import classify_query


def build_flow(call=complete):

    diagnostic_agent = DiagnosticAgent(call=call)
    socratic_agent = SocraticAgent(call=call)
    evaluator_agent = EvaluatorAgent(call=call)
    transfer_agent = TransferAgent(call=call)
    planner_agent = PlannerAgent(call=call)
    tutor_agent = TutorAgentR8(call=call)

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------

    def _get_concept_id(ctx) -> str | None:
        """Pull concept_id from the run's diagnostic record (or stored meta)."""
        diag = ctx.latest("diagnostic")
        if diag and diag.get("concept_id"):
            return diag["concept_id"]
        # fall back to classification record
        clf = ctx.latest("query_classification")
        if clf and clf.get("concept_id"):
            return clf["concept_id"]
        return None

    def _concept_kwargs(concept_id: str | None, misconception_id: str | None = None) -> dict:
        """Return keyword arguments to inject concept metadata into agent calls.

        Returns the full set including default_explanation (for TutorAgentR8).
        Use _base_concept_kwargs() for agents that don't accept default_explanation.
        """
        if not concept_id:
            return {}
        concept = get_concept(concept_id)
        if not concept:
            return {}
        misconception = get_misconception(misconception_id) if misconception_id else None
        return {
            "concept_id": concept_id,
            "display_name": concept.display_name,
            "core_invariant": concept.core_invariant,
            "misconception_id": misconception.misconception_id if misconception else None,
            "symptom_patterns": misconception.symptom_patterns if misconception else [],
            "default_explanation": misconception.default_worked_explanation if misconception else None,
        }

    def _base_concept_kwargs(concept_id: str | None, misconception_id: str | None = None) -> dict:
        """Like _concept_kwargs but without default_explanation.

        Use for DiagnosticAgent, PlannerAgent, EvaluatorAgent.
        """
        kw = _concept_kwargs(concept_id, misconception_id)
        kw.pop("default_explanation", None)
        return kw

    def get_current_wrong_socratic_count(ctx) -> int:
        backward_loops = ctx.history("backward_loop")
        last_loop_seq = backward_loops[-1].seq if backward_loops else -1
        return sum(
            1
            for record in ctx.history("evaluator")
            if record.seq > last_loop_seq
            and record.payload.get("stage") == "socratic"
            and record.payload.get("outcome") == "REINFORCE"
        )

    def get_used_angles(ctx):
        backward_loops = ctx.history("backward_loop")
        last_loop_seq = backward_loops[-1].seq if backward_loops else -1
        return {
            record.payload.get("angle_id")
            for record in ctx.history("socratic")
            if record.seq > last_loop_seq and record.payload.get("angle_id")
        }

    def get_next_angle(ctx, concept_id: str | None = None):
        """Return the next unused angle for the given concept."""
        used = get_used_angles(ctx)
        angles = get_concept_angles(concept_id) if concept_id else ANGLES

        for angle in angles:
            if angle["id"] not in used:
                return angle

        if angles:
            backward_loops = ctx.history("backward_loop")
            last_loop_seq = backward_loops[-1].seq if backward_loops else -1
            current_cycle_socratic = [
                r for r in ctx.history("socratic")
                if r.seq > last_loop_seq
            ]
            return angles[len(current_cycle_socratic) % len(angles)]

        return None

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def handle_diagnostic(ctx):
        """DRAFTING → classify query → run diagnostic or answer general question."""

        student = ctx.latest("student_attempt")

        if student is None:
            raise ValueError(
                "No student_attempt record found."
            )

        text = student["text"]

        # ── Step 1: classify the query ───────────────────────────────
        classification = classify_query(text)
        ctx.append(
            "query_classification",
            {
                "scope": classification.scope,
                "concept_id": classification.concept_id,
                "query_type": classification.query_type,
                "confidence": classification.confidence,
                "matched_keywords": classification.matched_keywords,
            },
            produced_by="query_classifier",
        )

        # ── Step 2: out-of-scope ─────────────────────────────────────
        if classification.scope == "OUT_OF_SCOPE":
            ctx.append(
                "learning_state",
                {
                    "misconception": "N/A",
                    "status": "OUT_OF_SCOPE",
                    "successful_angles": [],
                    "reinforced_angles": [],
                    "transfer_passed": False,
                    "recommended_next_action": (
                        "Please submit a DSA-related code attempt or question."
                    ),
                },
                produced_by="learning_state",
            )
            return RunState.COMPLETE

        concept_id = classification.concept_id
        base_ckw = _base_concept_kwargs(concept_id)
        full_ckw = _concept_kwargs(concept_id)

        # ── Step 3: general question → explanation mode ──────────────
        if classification.query_type == "GENERAL_QUESTION":
            concept = get_concept(concept_id) if concept_id else None
            explanation = get_concept_explanation(concept_id) if concept_id else (
                "Please provide more context about which DSA concept you are asking about."
            )

            # Use TutorAgentR8 in "explanation" mode (no planner needed)
            # Build a minimal planner decision for the API signature
            from .schema import PlannerDecision
            dummy_planner = PlannerDecision(
                action="COMPLETE",
                reason="General question — no Boundary Loop needed.",
                pedagogical_goal=f"Explain {concept.display_name if concept else 'DSA concept'}",
                preferred_angle="EXPLANATION",
                difficulty="medium",
                focus=concept.core_invariant if concept else "DSA fundamentals",
            )

            tutor_res = tutor_agent.run(
                ctx,
                student_attempt=text,
                diagnostic={"misconception": "GENERAL_QUESTION", "confidence": 1.0, "evidence": [], "reasoning_pattern": "general question"},
                planner_decision=dummy_planner,
                current_phase="explanation",
                **full_ckw,
            )

            ctx.append(
                "tutor",
                tutor_res.model_dump(),
                produced_by="tutor",
            )

            ctx.append(
                "learning_state",
                {
                    "misconception": "GENERAL_QUESTION",
                    "status": "CONCEPTUAL_QUERY_ANSWERED",
                    "successful_angles": [],
                    "reinforced_angles": [],
                    "transfer_passed": False,
                    "recommended_next_action": (
                        "Student can now try submitting a code attempt for deep diagnosis."
                    ),
                },
                produced_by="learning_state",
            )
            return RunState.COMPLETE

        # ── Step 4: code submission / misconception → full diagnostic ─
        concept = get_concept(concept_id) if concept_id else None
        supported_mids = concept.supported_misconceptions if concept else []
        
        result = diagnostic_agent.run(
            ctx,
            text,
            supported_misconceptions=supported_mids,
            **base_ckw,
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

        concept_id = _get_concept_id(ctx)
        diagnosed_mid = diagnostic.get("misconception")
        base_ckw = _base_concept_kwargs(concept_id, diagnosed_mid)
        full_ckw = _concept_kwargs(concept_id, diagnosed_mid)

        concept = get_concept(concept_id) if concept_id else None
        valid_mids = concept.supported_misconceptions if concept else []

        # Check if the diagnosed misconception is supported for this concept
        if diagnosed_mid not in valid_mids:
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

        student = ctx.latest("student_attempt")
        if student is None:
            raise ValueError(
                "No student_attempt record found."
            )

        evaluators = ctx.history("evaluator")
        last_eval = evaluators[-1].payload if evaluators else None
        transfer_records = ctx.history("transfer")
        socratic_records = ctx.history("socratic")
        backward_loops = ctx.history("backward_loop")
        wrong_count = get_current_wrong_socratic_count(ctx)

        # Detect if a backward loop just triggered
        last_socratic_seq = socratic_records[-1].seq if socratic_records else -1
        latest_backward_loop = None
        if backward_loops and backward_loops[-1].seq > last_socratic_seq:
            latest_backward_loop = backward_loops[-1].payload

        # Determine phase context
        current_phase = "socratic"
        if (
            last_eval
            and last_eval.get("stage") == "socratic"
            and last_eval.get("outcome") == "PASS"
            and not transfer_records
        ):
            current_phase = "transfer"

        # Planner recommends pedagogical intent
        planner_decision = planner_agent.run(
            ctx,
            student_attempt=student["text"],
            diagnostic=diagnostic,
            learning_state=ctx.latest("learning_state"),
            evaluators=[e.payload for e in evaluators],
            wrong_socratic_count=wrong_count,
            backward_loop_count=len(backward_loops),
            used_angles=get_used_angles(ctx),
            current_phase=current_phase,
            transfer_attempted=bool(transfer_records),
            backward_loop=latest_backward_loop,
            **base_ckw,
        )

        ctx.append(
            "planner",
            planner_decision.model_dump(),
            produced_by="planner",
        )

        # Deterministic flow enforces state transitions
        if current_phase == "transfer":
            transfer_tasks = get_concept_transfer_tasks(concept_id) if concept_id else TRANSFER_TASKS
            task_index = 0
            if task_index >= len(transfer_tasks):
                task_index = len(transfer_tasks) - 1

            task = transfer_tasks[task_index]

            tutor_res = tutor_agent.run(
                ctx,
                student_attempt=student["text"],
                diagnostic=diagnostic,
                planner_decision=planner_decision,
                learning_state=ctx.latest("learning_state"),
                current_phase="transfer",
                recent_eval=last_eval,
                backward_loop=latest_backward_loop,
                task=task,
                **full_ckw,
            )

            ctx.append(
                "tutor",
                tutor_res.model_dump(),
                produced_by="tutor",
            )

            ctx.append(
                "transfer",
                {
                    "task_id": tutor_res.angle_id or task.get("id", "TRANSFER_1"),
                    "prompt": tutor_res.question or task.get("prompt", ""),
                    "target_reasoning": tutor_res.pedagogical_goal or task.get("target_reasoning", ""),
                    "phase": "transfer",
                },
                produced_by="transfer",
            )

            return RunState.AWAITING_EXPERT

        # Socratic phase
        angle = get_next_angle(ctx, concept_id)

        if angle is None:
            concept_explanation = get_concept_explanation(concept_id) if concept_id else TUTOR_EXPLANATION

            ctx.append(
                "tutor",
                {
                    "phase": "explanation",
                    "question": concept_explanation,
                    "pedagogical_goal": "Provide worked example explanation",
                    "angle_id": "EXHAUSTED",
                    "explanation": concept_explanation,
                    "difficulty": "foundational",
                    "type": "worked_example",
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
                    "misconception": diagnosed_mid,
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
                        "the core invariant in a future encounter."
                    ),
                },
                produced_by="learning_state",
            )

            return RunState.COMPLETE

        tutor_res = tutor_agent.run(
            ctx,
            student_attempt=student["text"],
            diagnostic=diagnostic,
            planner_decision=planner_decision,
            learning_state=ctx.latest("learning_state"),
            current_phase="socratic",
            recent_eval=last_eval,
            backward_loop=latest_backward_loop,
            angle=angle,
            **full_ckw,
        )

        ctx.append(
            "tutor",
            tutor_res.model_dump(),
            produced_by="tutor",
        )

        ctx.append(
            "socratic",
            {
                "angle_id": tutor_res.angle_id or angle.get("id", "UNKNOWN"),
                "question": tutor_res.question,
                "pedagogical_goal": tutor_res.pedagogical_goal or angle.get("goal", ""),
                "phase": "socratic",
            },
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

        concept_id = _get_concept_id(ctx)
        diagnosed_mid = diagnostic.get("misconception")
        base_ckw = _base_concept_kwargs(concept_id, diagnosed_mid)

        # -------------------------------------------------
        # Current-question tracking is the source of truth
        # -------------------------------------------------
        transfer_records = ctx.history("transfer")
        socratic_records = ctx.history("socratic")
        response_records = ctx.history("student_response")

        is_transfer = False
        if transfer_records:
            if not socratic_records or transfer_records[-1].seq > socratic_records[-1].seq:
                if response_records and response_records[-1].seq > transfer_records[-1].seq:
                    is_transfer = True

        if is_transfer and transfer is not None:
            result = evaluator_agent.run(
                ctx,
                student["text"],
                diagnostic,
                transfer,
                response,
                stage="transfer",
                transfer_task=transfer,
                **base_ckw,
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
                        "misconception": diagnosed_mid,
                        "status": "TRANSFER_PASSED",
                        "successful_angles": [
                            record.payload.get("angle_id")
                            for record in ctx.history("socratic")
                            if record.payload.get("angle_id")
                        ],
                        "reinforced_angles": [],
                        "transfer_passed": True,
                        "recommended_next_action": (
                            "Use a related problem in the next encounter."
                        ),
                    },
                    produced_by="learning_state",
                )

                return RunState.COMPLETE

            if result.outcome == "REINFORCE":

                ctx.append(
                    "learning_state",
                    {
                        "misconception": diagnosed_mid,
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
            **base_ckw,
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
                    "misconception": diagnosed_mid,
                    "status": "SOCRATIC_PASS",
                    "successful_angles": [
                        angle_id
                    ],
                    "reinforced_angles": [],
                    "transfer_passed": False,
                    "recommended_next_action": (
                        "Test the reasoning on a fresh transfer task."
                    ),
                    "wrong_socratic_count": 0,
                    "backward_loop_count": len(ctx.history("backward_loop")),
                },
                produced_by="learning_state",
            )

            return RunState.GATING

        if result.outcome == "REINFORCE":

            wrong_count = get_current_wrong_socratic_count(ctx)

            if wrong_count >= 3:
                backward_loops = ctx.history("backward_loop")
                backward_loop_count = len(backward_loops) + 1

                loop_record = BackwardLoopRecord(
                    reason="three_wrong_socratic_answers",
                    wrong_socratic_count=wrong_count,
                    backward_loop_count=backward_loop_count,
                    misconception=diagnosed_mid,
                )

                ctx.append(
                    "backward_loop",
                    loop_record.model_dump(),
                    produced_by="backward_loop",
                )

                ctx.append(
                    "learning_state",
                    {
                        "misconception": diagnosed_mid,
                        "status": "BACKWARD_LOOP",
                        "successful_angles": [],
                        "reinforced_angles": [
                            record.payload.get("angle_id")
                            for record in ctx.history("socratic")
                            if record.payload.get("angle_id")
                        ],
                        "transfer_passed": False,
                        "recommended_next_action": (
                            "Revisit core invariant "
                            "from a foundational perspective."
                        ),
                        "wrong_socratic_count": 0,
                        "backward_loop_count": backward_loop_count,
                    },
                    produced_by="learning_state",
                )

                return RunState.GATING

            ctx.append(
                "learning_state",
                {
                    "misconception": diagnosed_mid,
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
                    "wrong_socratic_count": wrong_count,
                    "backward_loop_count": len(ctx.history("backward_loop")),
                },
                produced_by="learning_state",
            )

            return RunState.GATING

        ctx.append(
            "learning_state",
            {
                "misconception": diagnosed_mid,
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