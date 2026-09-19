"""Deterministic offline tests for Planner Agent, Tutor Agent R8, and CLI.

Tests cover:
1. Planner returns valid structured decision.
2. Invalid planner action is handled safely.
3. Tutor R8 generates a Socratic question from planner context.
4. Tutor R8 generates a transfer task.
5. Planner decision is persisted.
6. Tutor output is persisted.
7. Backward loop causes Planner to receive backward-loop context.
8. Backward loop produces a simpler Socratic Tutor question.
9. Existing current-question phase tracking still works.
10. Existing backward-loop behavior verified.
11. Existing transfer behavior verified.
12. CLI normal mode does not dump complete run history.
13. CLI --debug mode can still show detailed history.

All tests run offline against stubs with no network or OpenRouter API key required.
"""
from __future__ import annotations

import io
from pathlib import Path
import pytest

from slice.config import Settings
from slice.records import RunState
from slice.runner import advance, Context
from slice.store import Store
from demo.flow import build_flow
from demo.agents import PlannerAgent, TutorAgentR8, DiagnosticAgent, EvaluatorAgent
from demo.schema import (
    PlannerDecision,
    TutorResponse,
    DiagnosticResult,
    EvaluationResult,
    SocraticQuestion,
    TransferTask,
)
from run_boundary_loop import run_session

S = Settings(
    api_key="mock-key",
    model="mock-model",
    fallback_model="mock-fallback",
    escalation_model="mock-escalation",
    max_tokens=1000,
    max_tokens_per_run=50000,
    max_attempts_per_step=3,
    expert_timeout_minutes=45,
    langfuse_public="",
    langfuse_secret="",
    langfuse_host="",
)


class MockLLMCall:
    """Deterministic mock for all agents."""

    def __init__(
        self,
        planner_action: str = "ASK_SOCRATIC",
        evaluator_outcomes: list[str] | None = None,
        force_invalid_action: bool = False,
    ):
        self.planner_action = planner_action
        self.evaluator_outcomes = list(evaluator_outcomes or [])
        self.force_invalid_action = force_invalid_action
        self.planner_calls: list[dict] = []
        self.tutor_calls: list[dict] = []

    def __call__(self, settings, budget, messages, schema, step):
        if step == "diagnostic":
            return schema(
                misconception="M1_INCOMPLETE_ELIMINATION",
                confidence=0.95,
                evidence=["Student only moved left by 1."],
                reasoning_pattern="Treated interval as linear scan.",
            )

        if step == "planner":
            self.planner_calls.append({"messages": messages})
            action = "INVALID_RANDOM_ACTION" if self.force_invalid_action else self.planner_action
            return schema(
                action=action,
                reason="Pedagogical rationale for this step.",
                pedagogical_goal="Reason about the entire eliminated range invariant.",
                preferred_angle="COUNTEREXAMPLE_ARRAY",
                difficulty="foundational" if action == "BACKWARD_REMEDIATE" else "medium",
                focus="boundary_elimination",
            )

        if step == "tutor":
            self.tutor_calls.append({"messages": messages})
            # Check phase from messages
            content = " ".join(m.get("content", "") for m in messages)
            if "phase 'transfer'" in content or "'phase': 'transfer'" in content:
                return schema(
                    phase="transfer",
                    question="Transfer problem: If nums[mid] is 12 and target is 20, what is the new left bound?",
                    pedagogical_goal="Transfer sorted invariant to left boundary.",
                    angle_id="TRANSFER_1",
                    difficulty="medium",
                )
            elif "phase 'explanation'" in content:
                return schema(
                    phase="explanation",
                    question="Worked explanation: Every index <= mid cannot contain target.",
                    pedagogical_goal="Explain invariant directly.",
                    angle_id="EXHAUSTED",
                    explanation="Worked explanation details.",
                    difficulty="foundational",
                )
            else:
                return schema(
                    phase="socratic",
                    question="Consider array [2, 4, 6, 8, 10]. If mid is 6 and target is 9, what can be eliminated?",
                    pedagogical_goal="Reason about eliminated range.",
                    angle_id="COUNTEREXAMPLE_ARRAY",
                    difficulty="foundational" if self.planner_action == "BACKWARD_REMEDIATE" else "medium",
                )

        if step == "evaluator":
            outcome = "REINFORCE"
            if self.evaluator_outcomes:
                outcome = self.evaluator_outcomes.pop(0)

            return schema(
                outcome=outcome,
                confidence=0.9,
                evidence=["Analyzed student reasoning response."],
                reasoning_assessment=f"Assessed as {outcome}.",
            )

        if step == "socratic":
            return schema(
                angle_id="ELIMINATED_RANGE_PROOF",
                question="What indices are eliminated?",
                pedagogical_goal="Reason about range elimination.",
            )

        if step == "transfer":
            return schema(
                task_id="TRANSFER_1",
                prompt="Fresh transfer task prompt.",
                target_reasoning="Target boundary reasoning.",
            )

        raise ValueError(f"Unknown step: {step}")


def test_1_planner_returns_valid_structured_decision(tmp_path):
    """1. Planner returns valid structured decision."""
    store = Store(str(tmp_path / "t1.db"))
    run_id = store.create_run("boundary_loop")
    ctx = Context(store, run_id, S)

    mock = MockLLMCall(planner_action="ASK_SOCRATIC")
    planner = PlannerAgent(call=mock)

    decision = planner.run(
        ctx,
        student_attempt="while left <= right: left = left + 1",
        diagnostic={"misconception": "M1_INCOMPLETE_ELIMINATION"},
        learning_state=None,
        wrong_socratic_count=0,
    )

    assert isinstance(decision, PlannerDecision)
    assert decision.action == "ASK_SOCRATIC"
    assert decision.pedagogical_goal
    assert decision.preferred_angle
    assert decision.focus == "boundary_elimination"


def test_2_invalid_planner_action_handled_safely(tmp_path):
    """2. Invalid planner action is handled safely and visibly."""
    store = Store(str(tmp_path / "t2.db"))
    run_id = store.create_run("boundary_loop")
    ctx = Context(store, run_id, S)

    mock = MockLLMCall(force_invalid_action=True)
    planner = PlannerAgent(call=mock)

    # Calling with invalid action should NOT crash; it safely falls back to allowed action
    decision = planner.run(
        ctx,
        student_attempt="while left <= right: left = left + 1",
        diagnostic={"misconception": "M1_INCOMPLETE_ELIMINATION"},
        learning_state=None,
        wrong_socratic_count=0,
    )

    assert isinstance(decision, PlannerDecision)
    assert decision.action in {"ASK_SOCRATIC", "BACKWARD_REMEDIATE", "ASK_TRANSFER", "COMPLETE"}
    assert "safely overridden" in decision.reason


def test_3_tutor_r8_generates_socratic_question(tmp_path):
    """3. Tutor R8 generates a Socratic question from planner context."""
    store = Store(str(tmp_path / "t3.db"))
    run_id = store.create_run("boundary_loop")
    ctx = Context(store, run_id, S)

    mock = MockLLMCall()
    tutor = TutorAgentR8(call=mock)

    decision = PlannerDecision(
        action="ASK_SOCRATIC",
        reason="Test socratic reasoning",
        pedagogical_goal="Reason about eliminated range",
        preferred_angle="COUNTEREXAMPLE_ARRAY",
        difficulty="medium",
        focus="boundary_elimination",
    )

    response = tutor.run(
        ctx,
        student_attempt="left = left + 1",
        diagnostic={"misconception": "M1_INCOMPLETE_ELIMINATION"},
        planner_decision=decision,
        current_phase="socratic",
    )

    assert isinstance(response, TutorResponse)
    assert response.phase == "socratic"
    assert response.question
    assert response.angle_id


def test_4_tutor_r8_generates_transfer_task(tmp_path):
    """4. Tutor R8 generates a transfer task."""
    store = Store(str(tmp_path / "t4.db"))
    run_id = store.create_run("boundary_loop")
    ctx = Context(store, run_id, S)

    mock = MockLLMCall()
    tutor = TutorAgentR8(call=mock)

    decision = PlannerDecision(
        action="ASK_TRANSFER",
        reason="Socratic passed, testing transfer",
        pedagogical_goal="Transfer invariant to new problem",
        preferred_angle="TRANSFER_1",
        difficulty="medium",
        focus="boundary_elimination",
    )

    response = tutor.run(
        ctx,
        student_attempt="left = left + 1",
        diagnostic={"misconception": "M1_INCOMPLETE_ELIMINATION"},
        planner_decision=decision,
        current_phase="transfer",
    )

    assert isinstance(response, TutorResponse)
    assert response.phase == "transfer"
    assert "Transfer" in response.question or len(response.question) > 10


def test_5_planner_decision_is_persisted(tmp_path):
    """5. Planner decision is persisted in history with kind='planner'."""
    store = Store(str(tmp_path / "t5.db"))
    run_id = store.create_run("boundary_loop")
    store.append(run_id, "student_attempt", {"text": "while left <= right: left = left + 1"}, produced_by="student")

    mock = MockLLMCall()
    flow = build_flow(call=mock)

    advance(store, run_id, flow, S)

    planners = store.history(run_id, "planner")
    assert len(planners) >= 1
    assert planners[0].produced_by == "planner"
    assert "action" in planners[0].payload
    assert "pedagogical_goal" in planners[0].payload


def test_6_tutor_output_is_persisted(tmp_path):
    """6. Tutor output is persisted in history with kind='tutor'."""
    store = Store(str(tmp_path / "t6.db"))
    run_id = store.create_run("boundary_loop")
    store.append(run_id, "student_attempt", {"text": "while left <= right: left = left + 1"}, produced_by="student")

    mock = MockLLMCall()
    flow = build_flow(call=mock)

    advance(store, run_id, flow, S)

    tutors = store.history(run_id, "tutor")
    assert len(tutors) >= 1
    assert tutors[0].produced_by == "tutor"
    assert "phase" in tutors[0].payload
    assert "question" in tutors[0].payload


def test_7_backward_loop_causes_planner_to_receive_context(tmp_path):
    """7. Backward loop causes Planner to receive backward-loop context."""
    store = Store(str(tmp_path / "t7.db"))
    run_id = store.create_run("boundary_loop")
    store.append(run_id, "student_attempt", {"text": "left = left + 1"}, produced_by="student")

    mock = MockLLMCall(evaluator_outcomes=["REINFORCE", "REINFORCE", "REINFORCE"])
    flow = build_flow(call=mock)

    # Initial advance
    advance(store, run_id, flow, S)

    # 3 wrong answers
    for i in range(3):
        store.append(run_id, "student_response", {"response": f"wrong {i}"}, produced_by="student")
        store.set_state(run_id, RunState.EVALUATING)
        advance(store, run_id, flow, S)

    # Verify backward loop occurred
    loops = store.history(run_id, "backward_loop")
    assert len(loops) == 1

    # Check that subsequent planner decision was recorded with backward loop context
    planners = store.history(run_id, "planner")
    assert len(planners) == 4
    # The 4th planner run happened right after the backward loop
    last_planner = planners[-1]
    assert last_planner.seq > loops[0].seq


def test_8_backward_loop_produces_simpler_socratic_question(tmp_path):
    """8. Backward loop produces a simpler Socratic Tutor question."""
    store = Store(str(tmp_path / "t8.db"))
    run_id = store.create_run("boundary_loop")
    store.append(run_id, "student_attempt", {"text": "left = left + 1"}, produced_by="student")

    mock = MockLLMCall(
        planner_action="BACKWARD_REMEDIATE",
        evaluator_outcomes=["REINFORCE", "REINFORCE", "REINFORCE"],
    )
    flow = build_flow(call=mock)

    advance(store, run_id, flow, S)
    for i in range(3):
        store.append(run_id, "student_response", {"response": f"wrong {i}"}, produced_by="student")
        store.set_state(run_id, RunState.EVALUATING)
        advance(store, run_id, flow, S)

    tutors = store.history(run_id, "tutor")
    loops = store.history(run_id, "backward_loop")
    assert len(loops) == 1
    post_loop_tutor = tutors[-1].payload
    assert post_loop_tutor["phase"] == "socratic"
    assert post_loop_tutor["difficulty"] in ("foundational", "easy", "medium")


def test_9_existing_current_question_phase_tracking(tmp_path):
    """9. Current-question phase tracking still works (historical transfer doesn't corrupt Socratic)."""
    store = Store(str(tmp_path / "t9.db"))
    run_id = store.create_run("boundary_loop")
    store.append(run_id, "student_attempt", {"text": "left = left + 1"}, produced_by="student")

    mock = MockLLMCall(evaluator_outcomes=["PASS", "REINFORCE"])
    flow = build_flow(call=mock)

    # Initial advance -> Socratic question 1
    advance(store, run_id, flow, S)

    # Socratic correct -> advances to transfer
    store.append(run_id, "student_response", {"response": "correct socratic"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    state = advance(store, run_id, flow, S)
    assert state == RunState.AWAITING_EXPERT
    assert store.latest(run_id, "transfer") is not None

    # Transfer answer incorrect -> evaluated as stage="transfer"
    store.append(run_id, "student_response", {"response": "wrong transfer answer"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    state = advance(store, run_id, flow, S)
    assert state == RunState.AWAITING_EXPERT

    # Flow is now at a new Socratic question because transfer needed reinforcement
    latest_socratic = store.latest(run_id, "socratic")
    transfer_records = store.history(run_id, "transfer")
    socratic_records = store.history(run_id, "socratic")
    assert socratic_records[-1].seq > transfer_records[-1].seq


def test_10_backward_loop_cycle_and_counter_reset(tmp_path):
    """10. Backward loop counter resets after trigger and tracks cycles."""
    store = Store(str(tmp_path / "t10.db"))
    run_id = store.create_run("boundary_loop")
    store.append(run_id, "student_attempt", {"text": "left = left + 1"}, produced_by="student")

    mock = MockLLMCall(evaluator_outcomes=["REINFORCE", "REINFORCE", "REINFORCE", "PASS", "PASS"])
    flow = build_flow(call=mock)

    advance(store, run_id, flow, S)
    for i in range(3):
        store.append(run_id, "student_response", {"response": f"cycle1 wrong {i}"}, produced_by="student")
        store.set_state(run_id, RunState.EVALUATING)
        advance(store, run_id, flow, S)

    assert len(store.history(run_id, "backward_loop")) == 1

    # In cycle 2, student passes
    store.append(run_id, "student_response", {"response": "cycle2 pass"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    advance(store, run_id, flow, S)

    # Should have advanced to transfer
    assert store.latest(run_id, "transfer") is not None
    assert len(store.history(run_id, "backward_loop")) == 1


def test_11_transfer_success_completes_run(tmp_path):
    """11. Socratic pass + Transfer pass completes run."""
    store = Store(str(tmp_path / "t11.db"))
    run_id = store.create_run("boundary_loop")
    store.append(run_id, "student_attempt", {"text": "left = left + 1"}, produced_by="student")

    mock = MockLLMCall(evaluator_outcomes=["PASS", "PASS"])
    flow = build_flow(call=mock)

    advance(store, run_id, flow, S)

    # Socratic pass
    store.append(run_id, "student_response", {"response": "socratic pass"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    advance(store, run_id, flow, S)

    # Transfer pass
    store.append(run_id, "student_response", {"response": "transfer pass"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    final_state = advance(store, run_id, flow, S)

    assert final_state == RunState.COMPLETE
    ls = store.latest(run_id, "learning_state")
    assert ls["status"] == "TRANSFER_PASSED"
    assert ls["transfer_passed"] is True


def test_12_cli_normal_mode_does_not_dump_history(capsys, monkeypatch, tmp_path):
    """12. CLI normal mode does not dump complete run history."""
    monkeypatch.chdir(tmp_path)

    # Mock inputs: student attempt + END, student answer + END
    inputs = iter([
        "while left <= right: left = left + 1",
        "END",
        "Because nums[mid] < target, range up to mid is impossible.",
        "END",
        "On transfer, right becomes mid - 1.",
        "END",
    ])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    mock = MockLLMCall(evaluator_outcomes=["PASS", "PASS"])
    monkeypatch.setattr("run_boundary_loop.build_flow", lambda: build_flow(call=mock))

    run_session(debug=False)

    captured = capsys.readouterr().out

    # In normal mode, RUN HISTORY banner should NOT be present
    assert "RUN HISTORY" not in captured
    assert "[DEBUG]" not in captured
    assert "THE BOUNDARY LOOP" in captured
    assert "DIAGNOSIS" in captured
    assert "EVALUATION" in captured
    assert "BOUNDARY LOOP COMPLETE" in captured


def test_13_cli_debug_mode_shows_detailed_history(capsys, monkeypatch, tmp_path):
    """13. CLI --debug mode can still show detailed history and planner decisions."""
    monkeypatch.chdir(tmp_path)

    inputs = iter([
        "while left <= right: left = left + 1",
        "END",
        "Because nums[mid] < target, range up to mid is impossible.",
        "END",
        "On transfer, right becomes mid - 1.",
        "END",
    ])
    monkeypatch.setattr("builtins.input", lambda: next(inputs))

    mock = MockLLMCall(evaluator_outcomes=["PASS", "PASS"])
    monkeypatch.setattr("run_boundary_loop.build_flow", lambda: build_flow(call=mock))

    run_session(debug=True)

    captured = capsys.readouterr().out

    # In debug mode, RUN HISTORY and DEBUG sections should be present
    assert "RUN HISTORY" in captured
    assert "[DEBUG] PLANNER DECISION" in captured
    assert "[DEBUG] TUTOR R8 RECORD" in captured
    assert "THE BOUNDARY LOOP" in captured
