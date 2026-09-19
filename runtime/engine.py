"""
The Tutoring Engine.

Orchestrates the 12-state deterministic state machine:
START
→ DIAGNOSING
→ SOCRATIC_GUIDANCE
→ GENERATE_TRANSFER_TASK
→ WAITING_FOR_STUDENT
→ EVALUATING
→ TARGETED_TUTORING
→ UPDATE_STATE
→ PLAN_NEXT
→ ESCALATED
→ HUMAN_REVIEW_WAITING
→ COMPLETE

Rules strictly enforced:
- Runtime, NOT the LLM, decides all state transitions.
- All 7 agents are generic across DSA topics.
- Knowledge rubrics in knowledge/ support specific topics.
- Persistent SQLite state in data/tutor.db survives restarts.
- Second encounters adapt based on previous evidence.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Optional

from agents.classifier import QuestionClassifier
from agents.diagnostic import DiagnosticAgent
from agents.evaluator import EvaluatorAgent
from agents.planner import PlannerAgent
from agents.socratic import SocraticAgent
from agents.transfer import TransferAgent
from agents.tutor import TargetedTutorAgent
from llm.fallback import general_answer
from llm.openrouter import call_llm
from llm.prompts import GENERAL_QA_SYSTEM, GENERAL_QA_USER_TEMPLATE
from llm.schemas import (
    ClassificationResult,
    DiagnosisResult,
    EvaluationResult,
    EvalResult,
    MasteryStatus,
    PlannerOutput,
    SocraticOutput,
    StudentIntent,
    TransferTask,
    TutorOutput,
)
from runtime.budgets import TutorBudget
from runtime.store import TutorStore
from runtime.transitions import decide_next_state_from_eval
from slice.events import (
    DIAGNOSIS_CREATED,
    ESCALATED,
    EVALUATION_COMPLETED,
    EVALUATION_FAIL,
    EVALUATION_PASS,
    GENERAL_ANSWER_GIVEN,
    HUMAN_REVIEW_REQUESTED,
    LEARNING_STATE_UPDATED,
    MISCONCEPTION_RECURRED,
    PLAN_CREATED,
    QUESTION_CLASSIFIED,
    SESSION_COMPLETED,
    SESSION_STARTED,
    SOCRATIC_ATTEMPTS_EXHAUSTED,
    SOCRATIC_QUESTION_ASKED,
    STATE_TRANSITION,
    STUDENT_RESPONSE_RECEIVED,
    TRANSFER_TASK_CREATED,
    TUTOR_EXPLANATION_CREATED,
)
from slice.state_machine import TutorState, validate_transition


class TutoringSession:
    """Represents a single active tutoring session for a student."""

    def __init__(
        self,
        student_id: str,
        store: TutorStore,
        session_id: Optional[str] = None,
        max_socratic_attempts: int = 3,
        max_agent_calls: int = 30,
    ) -> None:
        self.student_id = student_id
        self.session_id = session_id or f"sess_{uuid.uuid4().hex[:10]}"
        self.store = store
        self.state = TutorState.START
        self.budget = TutorBudget(
            max_socratic_attempts=max_socratic_attempts,
            max_agent_calls=max_agent_calls,
        )

        # Active contextual data
        self.current_query: str = ""
        self.classification: Optional[ClassificationResult] = None
        self.diagnosis: Optional[DiagnosisResult] = None
        self.current_angle: Optional[str] = None
        self.current_question: Optional[str] = None
        self.current_transfer: Optional[TransferTask] = None
        self.current_eval: Optional[EvaluationResult] = None
        self.current_tutor: Optional[TutorOutput] = None
        self.current_plan: Optional[PlannerOutput] = None
        self.general_response: Optional[str] = None

        # Tracking within session
        self.used_angles: list[str] = []
        self.used_questions: list[str] = []
        self.used_transfer_ids: list[str] = []
        self.stage: str = "socratic"  # "socratic" or "transfer"

        # Previous encounter adaptation
        self.previous_encounters_context: str = ""
        self.adapted_from_history: bool = False

        # Output / UI message log
        self.messages: list[dict[str, str]] = []

    def log_event(self, event_type: str, data: Optional[dict[str, Any]] = None) -> None:
        self.store.record_event(
            event_type=event_type,
            session_id=self.session_id,
            student_id=self.student_id,
            data=data,
        )

    def transition_to(self, new_state: TutorState) -> None:
        validate_transition(self.state, new_state)
        old_state = self.state
        self.state = new_state
        self.log_event(
            STATE_TRANSITION,
            {"from": old_state.value, "to": new_state.value},
        )


class TutoringEngine:
    """The central deterministic tutoring engine."""

    def __init__(
        self,
        store: Optional[TutorStore] = None,
        db_path: str = "data/tutor.db",
        max_socratic_attempts: int = 3,
        max_agent_calls: int = 30,
    ) -> None:
        self.store = store or TutorStore(db_path=db_path)
        self.max_socratic_attempts = max_socratic_attempts
        self.max_agent_calls = max_agent_calls

        # Instantiate agents
        self.classifier = QuestionClassifier()
        self.diagnostic = DiagnosticAgent()
        self.socratic = SocraticAgent()
        self.transfer = TransferAgent()
        self.evaluator = EvaluatorAgent()
        self.tutor = TargetedTutorAgent()
        self.planner = PlannerAgent()

    def start_session(self, student_id: str, initial_query: str) -> TutoringSession:
        session = TutoringSession(
            student_id=student_id,
            store=self.store,
            max_socratic_attempts=self.max_socratic_attempts,
            max_agent_calls=self.max_agent_calls,
        )
        session.current_query = initial_query
        self.store.create_session(
            session_id=session.session_id,
            student_id=student_id,
            topic="general",
            mode="adaptive",
        )
        session.log_event(SESSION_STARTED, {"initial_query": initial_query})

        # Load previous history to adapt if available
        past_misconceptions = self.store.get_student_misconceptions(student_id=student_id)
        if past_misconceptions:
            last = past_misconceptions[0]
            session.previous_encounters_context = (
                f"Previous encounter: Misconception {last['misconception_id']} in {last['topic']}"
            )
            session.adapted_from_history = True

        return session

    def step(self, session: TutoringSession, student_input: Optional[str] = None) -> TutorState:
        """Advance the session through one state machine step."""
        state = session.state

        if state == TutorState.START:
            session.transition_to(TutorState.DIAGNOSING)
            return self.step(session)

        elif state == TutorState.DIAGNOSING:
            session.budget.bump_agent_call("classifier")
            classification = self.classifier.classify(session.current_query)
            session.classification = classification
            session.log_event(QUESTION_CLASSIFIED, classification.model_dump())

            if not classification.adaptive:
                # General Q&A branch
                session.general_response = self._handle_general_qa(session.current_query, classification.topic)
                session.log_event(GENERAL_ANSWER_GIVEN, {"topic": classification.topic})
                session.transition_to(TutorState.COMPLETE)
                return session.state

            # Adaptive branch: run Diagnostic Agent
            session.budget.bump_agent_call("diagnostic")
            diagnosis = self.diagnostic.diagnose(
                student_input=session.current_query,
                topic=classification.topic,
                subconcept=classification.subconcept,
            )
            session.diagnosis = diagnosis
            session.log_event(DIAGNOSIS_CREATED, diagnosis.model_dump())

            # Record in SQLite persistent store
            self.store.record_misconception(
                student_id=session.student_id,
                topic=classification.topic,
                subconcept=classification.subconcept or "general",
                misconception_id=diagnosis.misconception_id,
                evidence=diagnosis.evidence,
            )

            # Check if student had previous used angles for this topic
            past_state = self.store.get_learning_state(
                student_id=session.student_id,
                topic=classification.topic,
                subconcept=classification.subconcept or "general",
            )
            if past_state and past_state.get("used_angles"):
                session.used_angles.extend(past_state["used_angles"])

            session.transition_to(TutorState.SOCRATIC_GUIDANCE)
            return self.step(session)

        elif state == TutorState.SOCRATIC_GUIDANCE:
            session.budget.bump_agent_call("socratic")
            session.budget.record_socratic_attempt()
            session.stage = "socratic"

            diagnosis = session.diagnosis
            topic = session.classification.topic if session.classification else "binary_search"
            subconcept = session.classification.subconcept if session.classification else None

            # Select an unused Socratic angle
            angle_id, angle_desc = self._select_next_angle(topic, diagnosis.misconception_id, session.used_angles)
            session.current_angle = angle_id
            if angle_id not in session.used_angles:
                session.used_angles.append(angle_id)


            socratic_out = self.socratic.ask(
                misconception_id=diagnosis.misconception_id,
                angle_id=angle_id,
                angle_description=angle_desc,
                topic=topic,
                subconcept=subconcept,
                used_questions=session.used_questions,
                student_input=session.current_query,
            )
            session.current_question = socratic_out.question
            session.used_questions.append(socratic_out.question)

            session.log_event(
                SOCRATIC_QUESTION_ASKED,
                {"angle_id": angle_id, "question": socratic_out.question},
            )

            session.transition_to(TutorState.WAITING_FOR_STUDENT)
            return session.state

        elif state == TutorState.GENERATE_TRANSFER_TASK:
            session.budget.bump_agent_call("transfer")
            session.stage = "transfer"

            diagnosis = session.diagnosis
            topic = session.classification.topic if session.classification else "binary_search"
            subconcept = session.classification.subconcept if session.classification else None

            transfer_task = self.transfer.generate(
                misconception_id=diagnosis.misconception_id,
                topic=topic,
                subconcept=subconcept,
                target_reasoning=diagnosis.invariant,
                original_example=session.current_query,
                previous_tasks=session.used_transfer_ids,
            )
            session.current_transfer = transfer_task
            session.used_transfer_ids.append(transfer_task.task_id)
            session.current_question = transfer_task.problem

            session.log_event(
                TRANSFER_TASK_CREATED,
                {"task_id": transfer_task.task_id, "problem": transfer_task.problem},
            )

            session.transition_to(TutorState.WAITING_FOR_STUDENT)
            return session.state

        elif state == TutorState.WAITING_FOR_STUDENT:
            if student_input is None:
                # System halts here waiting for external human input
                return session.state

            # Input arrived: transition to EVALUATING
            session.log_event(STUDENT_RESPONSE_RECEIVED, {"response": student_input})
            session.transition_to(TutorState.EVALUATING)
            return self.step(session, student_input=student_input)

        elif state == TutorState.EVALUATING:
            session.budget.bump_agent_call("evaluator")
            diagnosis = session.diagnosis
            topic = session.classification.topic if session.classification else "binary_search"

            target_reasoning = (
                session.current_transfer.target_reasoning
                if session.stage == "transfer" and session.current_transfer
                else diagnosis.invariant
            )

            eval_res = self.evaluator.evaluate(
                student_response=student_input or "",
                misconception_id=diagnosis.misconception_id,
                topic=topic,
                stage=session.stage,
                target_reasoning=target_reasoning,
                invariant=diagnosis.invariant,
                question_or_task=session.current_question or "",
            )
            session.current_eval = eval_res

            # Record attempt in SQLite store
            self.store.record_attempt(
                session_id=session.session_id,
                student_id=session.student_id,
                stage=session.stage,
                angle_id=session.current_angle,
                task_id=session.current_transfer.task_id if session.current_transfer else None,
                student_response=student_input or "",
                outcome=eval_res.result.value,
                reasoning_correct=eval_res.reasoning_correct,
                transfer_success=eval_res.transfer_success,
                misconception_recurred=eval_res.misconception_recurred,
            )

            session.log_event(EVALUATION_COMPLETED, eval_res.model_dump())

            if eval_res.result == EvalResult.PASS:
                session.log_event(EVALUATION_PASS)
            else:
                session.log_event(EVALUATION_FAIL)

            if eval_res.misconception_recurred:
                session.log_event(MISCONCEPTION_RECURRED, {"misconception_id": diagnosis.misconception_id})

            # Check if Socratic attempts are exhausted
            if session.budget.socratic_attempts_exhausted() and eval_res.result != EvalResult.PASS:
                session.log_event(SOCRATIC_ATTEMPTS_EXHAUSTED)

            # DETERMINISTIC TRANSITION DECIDER
            next_state = decide_next_state_from_eval(
                eval_result=eval_res,
                stage=session.stage,
                budget=session.budget,
                target_misconception=diagnosis.misconception_id,
            )

            session.transition_to(next_state)
            return self.step(session)

        elif state == TutorState.TARGETED_TUTORING:
            session.budget.bump_agent_call("tutor")
            session.budget.record_tutor_attempt()

            diagnosis = session.diagnosis
            topic = session.classification.topic if session.classification else "binary_search"
            subconcept = session.classification.subconcept if session.classification else None

            tutor_out = self.tutor.explain(
                misconception_id=diagnosis.misconception_id,
                invariant=diagnosis.invariant,
                topic=topic,
                subconcept=subconcept,
                student_input=session.current_query,
            )
            session.current_tutor = tutor_out
            session.log_event(TUTOR_EXPLANATION_CREATED, tutor_out.model_dump())

            # After targeted tutoring, generate fresh transfer task
            session.transition_to(TutorState.GENERATE_TRANSFER_TASK)
            return self.step(session)

        elif state == TutorState.UPDATE_STATE:
            # Deterministic update of persistent learning state
            topic = session.classification.topic if session.classification else "binary_search"
            subconcept = session.classification.subconcept or "general"
            diagnosis = session.diagnosis

            # Resolve misconception in persistent store
            self.store.resolve_misconceptions(
                student_id=session.student_id,
                topic=topic,
                subconcept=subconcept,
                misconception_id=diagnosis.misconception_id,
            )

            existing = self.store.get_learning_state(session.student_id, topic, subconcept)
            succ_count = (existing["successful_transfer_count"] + 1) if existing else 1
            fail_count = existing["failed_transfer_count"] if existing else 0

            # Mastery requires evidence: Socratic + Transfer success
            mastery = MasteryStatus.PROVISIONALLY_MASTERED.value if succ_count == 1 else MasteryStatus.MASTERED.value

            self.store.save_learning_state(
                student_id=session.student_id,
                topic=topic,
                subconcept=subconcept,
                mastery_status=mastery,
                confidence=0.92,
                successful_transfer_count=succ_count,
                failed_transfer_count=fail_count,
                last_strategy="Socratic + Fresh Transfer Validation",
                used_angles=session.used_angles,
                history_entry={
                    "session_id": session.session_id,
                    "misconception": diagnosis.misconception_id,
                    "angles_used": session.used_angles,
                    "transfer_task": session.current_transfer.task_id if session.current_transfer else "",
                    "result": "PASS",
                },
            )

            session.log_event(
                LEARNING_STATE_UPDATED,
                {"mastery_status": mastery, "topic": topic, "subconcept": subconcept},
            )

            session.transition_to(TutorState.PLAN_NEXT)
            return self.step(session)

        elif state == TutorState.PLAN_NEXT:
            session.budget.bump_agent_call("planner")
            topic = session.classification.topic if session.classification else "binary_search"
            subconcept = session.classification.subconcept or "general"
            diagnosis = session.diagnosis

            existing = self.store.get_learning_state(session.student_id, topic, subconcept)
            succ_count = existing["successful_transfer_count"] if existing else 1
            fail_count = existing["failed_transfer_count"] if existing else 0
            mastery = existing["mastery_status"] if existing else MasteryStatus.PROVISIONALLY_MASTERED.value

            plan = self.planner.plan(
                student_id=session.student_id,
                topic=topic,
                subconcept=subconcept,
                misconception_id=diagnosis.misconception_id,
                mastery_status=mastery,
                transfer_passed=True,
                failed_transfer_count=fail_count,
                successful_transfer_count=succ_count,
            )
            session.current_plan = plan
            session.log_event(PLAN_CREATED, plan.model_dump())

            session.transition_to(TutorState.COMPLETE)
            return self.step(session)

        elif state == TutorState.ESCALATED:
            session.log_event(ESCALATED)
            session.log_event(HUMAN_REVIEW_REQUESTED)
            session.transition_to(TutorState.HUMAN_REVIEW_WAITING)
            return session.state

        elif state in (TutorState.COMPLETE, TutorState.HUMAN_REVIEW_WAITING):
            session.store.update_session_status(session.session_id, state.value)
            session.log_event(SESSION_COMPLETED, {"final_state": state.value})
            return session.state

        return session.state

    def _select_next_angle(self, topic: str, misconception_id: str, used_angles: list[str]) -> tuple[str, str]:
        """Select an angle that has NOT yet been used."""
        # Standard candidate angles for binary search M1
        candidate_angles = [
            ("ELIMINATED_RANGE_PROOF", "Ask which indices are provably eliminated"),
            ("COUNTEREXAMPLE", "Walk through a concrete array where the student's rule fails"),
            ("INVARIANT_RESTATEMENT", "Ask what must remain true about the search interval"),
            ("OPPOSITE_BRANCH_TRANSFER", "Apply the elimination reasoning when target < nums[mid]"),
        ]

        for aid, desc in candidate_angles:
            if aid not in used_angles:
                return aid, desc

        # If all exhausted, rotate or use generic
        idx = len(used_angles) % len(candidate_angles)
        return candidate_angles[idx]

    def _handle_general_qa(self, query: str, topic: str) -> str:
        """Handles non-adaptive general DSA questions via OpenRouter or fallback."""
        messages = [
            {"role": "system", "content": GENERAL_QA_SYSTEM},
            {"role": "user", "content": GENERAL_QA_USER_TEMPLATE.format(student_input=query)},
        ]
        res = call_llm(messages=messages, step="general_qa")
        if res and isinstance(res, str) and len(res.strip()) > 20:
            return res.strip()

        return general_answer(query, topic)
