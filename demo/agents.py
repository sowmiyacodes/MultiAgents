from pathlib import Path

from slice.llm import complete

from .schema import (
    DiagnosticResult,
    SocraticQuestion,
    EvaluationResult,
    TransferTask,
    PlannerDecision,
    TutorResponse,
    VALID_PLANNER_ACTIONS,
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

    def __init__(self, call=complete):
        self.call = call

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

        return self.call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=DiagnosticResult,
            step="diagnostic",
        )


class SocraticAgent:
    name = "socratic"

    def __init__(self, call=complete):
        self.call = call

    def run(
        self,
        ctx,
        student_attempt: str,
        diagnostic: dict,
        angle: dict,
    ) -> SocraticQuestion:

        prompt = _read_prompt("socratic.md")

        user_content = (
            "STUDENT ATTEMPT:\n"
            f"{student_attempt}\n\n"
            "DIAGNOSTIC:\n"
            f"{diagnostic}\n\n"
            "SELECTED SOCRATIC ANGLE:\n"
            f"{angle}\n\n"
            "Generate one Socratic question."
        )

        backward_loop = ctx.latest("backward_loop")
        if backward_loop:
            user_content += (
                f"\n\nBACKWARD LOOP CONTEXT:\n"
                f"A backward loop was triggered ({backward_loop.get('reason')}). "
                f"Revisit misconception {backward_loop.get('misconception')} "
                f"from a foundational teaching and reinforcement perspective."
            )

        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ]

        return self.call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=SocraticQuestion,
            step="socratic",
        )


class EvaluatorAgent:
    name = "evaluator"

    def __init__(self, call=complete):
        self.call = call

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

        return self.call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=EvaluationResult,
            step="evaluator",
        )


class TransferAgent:
    name = "transfer"

    def __init__(self, call=complete):
        self.call = call

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

        return self.call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=TransferTask,
            step="transfer",
        )


class PlannerAgent:
    name = "planner"

    def __init__(self, call=complete):
        self.call = call

    def _fallback_action(
        self,
        diagnostic: dict,
        learning_state: dict | None,
        wrong_socratic_count: int,
        backward_loop: dict | None,
        current_phase: str,
        transfer_attempted: bool,
    ) -> str:
        if backward_loop or wrong_socratic_count >= 3:
            return "BACKWARD_REMEDIATE"
        if (
            learning_state
            and learning_state.get("status") == "SOCRATIC_PASS"
            and not transfer_attempted
        ):
            return "ASK_TRANSFER"
        if (
            learning_state
            and learning_state.get("status") == "TRANSFER_PASSED"
        ):
            return "COMPLETE"
        return "ASK_SOCRATIC"

    def run(
        self,
        ctx,
        student_attempt: str,
        diagnostic: dict,
        learning_state: dict | None = None,
        evaluators: list | None = None,
        wrong_socratic_count: int = 0,
        backward_loop_count: int = 0,
        used_angles: set[str] | None = None,
        current_phase: str = "socratic",
        transfer_attempted: bool = False,
        backward_loop: dict | None = None,
    ) -> PlannerDecision:
        prompt = _read_prompt("planner.md")

        user_content = (
            f"STUDENT BINARY-SEARCH ATTEMPT:\n{student_attempt}\n\n"
            f"DIAGNOSTIC:\n{diagnostic}\n\n"
            f"CURRENT LEARNING STATE:\n{learning_state}\n\n"
            f"CURRENT PHASE:\n{current_phase}\n\n"
            f"WRONG SOCRATIC COUNT IN CURRENT CYCLE:\n{wrong_socratic_count}\n\n"
            f"BACKWARD LOOP COUNT:\n{backward_loop_count}\n\n"
            f"USED ANGLES:\n{list(used_angles or [])}\n\n"
            f"TRANSFER ATTEMPTED:\n{transfer_attempted}\n\n"
            f"BACKWARD LOOP TRIGGER CONTEXT:\n{backward_loop}\n\n"
            f"RECENT EVALUATIONS:\n{evaluators or []}\n\n"
            "Recommend the next pedagogical move."
        )

        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ]

        try:
            result = self.call(
                settings=ctx.settings,
                budget=ctx.budget,
                messages=messages,
                schema=PlannerDecision,
                step="planner",
            )
            # Bound actions strictly to the allowed set
            if result.action not in VALID_PLANNER_ACTIONS:
                fallback_act = self._fallback_action(
                    diagnostic=diagnostic,
                    learning_state=learning_state,
                    wrong_socratic_count=wrong_socratic_count,
                    backward_loop=backward_loop,
                    current_phase=current_phase,
                    transfer_attempted=transfer_attempted,
                )
                return PlannerDecision(
                    action=fallback_act,  # type: ignore[arg-type]
                    reason=f"Invalid action '{result.action}' safely overridden to {fallback_act}.",
                    pedagogical_goal=result.pedagogical_goal or "Reason about eliminated range invariant",
                    preferred_angle=result.preferred_angle or "COUNTEREXAMPLE_ARRAY",
                    difficulty="foundational" if fallback_act == "BACKWARD_REMEDIATE" else "medium",
                    focus="boundary_elimination",
                )
            return result
        except Exception as e:
            if "Unknown step" in str(e):
                fallback_act = self._fallback_action(
                    diagnostic=diagnostic,
                    learning_state=learning_state,
                    wrong_socratic_count=wrong_socratic_count,
                    backward_loop=backward_loop,
                    current_phase=current_phase,
                    transfer_attempted=transfer_attempted,
                )
                pref_angle = "COUNTEREXAMPLE_ARRAY" if fallback_act == "BACKWARD_REMEDIATE" else "ELIMINATED_RANGE_PROOF"
                return PlannerDecision(
                    action=fallback_act,
                    reason=f"Offline deterministic pedagogical decision ({fallback_act}).",
                    pedagogical_goal="Reason about the entire eliminated range invariant",
                    preferred_angle=pref_angle,
                    difficulty="foundational" if fallback_act == "BACKWARD_REMEDIATE" else "medium",
                    focus="boundary_elimination",
                )
            fallback_act = self._fallback_action(
                diagnostic=diagnostic,
                learning_state=learning_state,
                wrong_socratic_count=wrong_socratic_count,
                backward_loop=backward_loop,
                current_phase=current_phase,
                transfer_attempted=transfer_attempted,
            )
            return PlannerDecision(
                action=fallback_act,
                reason=f"Planner error ({e}) safely overridden to {fallback_act}.",
                pedagogical_goal="Reason about the entire eliminated range invariant",
                preferred_angle="COUNTEREXAMPLE_ARRAY",
                difficulty="foundational" if fallback_act == "BACKWARD_REMEDIATE" else "medium",
                focus="boundary_elimination",
            )



class TutorAgentR8:
    name = "tutor"

    def __init__(self, call=complete):
        self.call = call

    def run(
        self,
        ctx,
        student_attempt: str,
        diagnostic: dict,
        planner_decision: PlannerDecision,
        learning_state: dict | None = None,
        current_phase: str = "socratic",
        recent_eval: dict | None = None,
        backward_loop: dict | None = None,
        angle: dict | None = None,
        task: dict | None = None,
    ) -> TutorResponse:
        prompt = _read_prompt("tutor_r8.md")

        user_content = (
            f"STUDENT ATTEMPT:\n{student_attempt}\n\n"
            f"DIAGNOSTIC:\n{diagnostic}\n\n"
            f"PLANNER DECISION:\n{planner_decision.model_dump()}\n\n"
            f"LEARNING STATE:\n{learning_state}\n\n"
            f"CURRENT PHASE:\n{current_phase}\n\n"
            f"RECENT EVALUATION:\n{recent_eval}\n\n"
            f"BACKWARD LOOP CONTEXT:\n{backward_loop}\n\n"
            f"SUGGESTED ANGLE:\n{angle}\n\n"
            f"SUGGESTED TRANSFER TASK:\n{task}\n\n"
            f"Generate the student-facing content for phase '{current_phase}'."
        )

        messages = [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ]

        try:
            return self.call(
                settings=ctx.settings,
                budget=ctx.budget,
                messages=messages,
                schema=TutorResponse,
                step="tutor",
            )
        except ValueError as e:
            if "Unknown step" in str(e):
                # Fallback for legacy test stubs that expect step="socratic" or step="transfer"
                if current_phase == "transfer":
                    transfer_agent = TransferAgent(call=self.call)
                    t_task = task or {
                        "id": "TRANSFER_1",
                        "prompt": "Consider binary search where nums[mid] = 12 and target = 20. Which indices are ruled out and what is the new boundary?",
                        "target_reasoning": "Every index at or before mid is impossible. Left becomes mid + 1.",
                    }
                    res = transfer_agent.run(ctx, diagnostic, t_task)
                    return TutorResponse(
                        phase="transfer",
                        question=res.prompt,
                        pedagogical_goal=res.target_reasoning,
                        angle_id=res.task_id,
                        difficulty=planner_decision.difficulty,
                    )
                else:
                    socratic_agent = SocraticAgent(call=self.call)
                    s_angle = angle or {
                        "id": planner_decision.preferred_angle or "COUNTEREXAMPLE_ARRAY",
                        "goal": planner_decision.pedagogical_goal,
                    }
                    res = socratic_agent.run(ctx, student_attempt, diagnostic, s_angle)
                    return TutorResponse(
                        phase="socratic",
                        question=res.question,
                        pedagogical_goal=res.pedagogical_goal,
                        angle_id=res.angle_id,
                        difficulty=planner_decision.difficulty,
                    )
            raise