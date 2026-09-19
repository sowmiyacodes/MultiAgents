"""Deterministic tests for the backward loop behavior in The Boundary Loop.

Tests 1 to 5 cover:
1. Three wrong Socratic answers trigger the backward loop.
2. Two wrong Socratic answers do not trigger the backward loop.
3. Wrong Socratic counter resets after a backward loop.
4. Backward loop is based on wrong answer count (>= 3), not angle exhaustion.
5. Transfer failure does not trigger the Socratic backward loop.

All tests run against mock/stub responses: no OpenRouter API key or network required.
"""
from __future__ import annotations

import re
from pathlib import Path
import pytest

from slice.config import Settings
from slice.records import RunState
from slice.runner import advance
from slice.store import Store
from demo.flow import build_flow
from demo import angles as angles_module

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


class StubCall:
    """Mock LLM callable that satisfies agent schemas deterministically."""

    def __init__(self, evaluator_outcomes: list[str] | None = None) -> None:
        self.evaluator_outcomes = list(evaluator_outcomes or [])
        self.evaluator_call_count = 0
        self.socratic_call_count = 0

    def __call__(self, settings, budget, messages, schema, step):
        if step == "diagnostic":
            return schema(
                misconception="M1_INCOMPLETE_ELIMINATION",
                confidence=0.95,
                evidence=["Student only adjusted left boundary by 1."],
                reasoning_pattern="Treated binary search interval as linear scan.",
            )

        if step == "socratic":
            self.socratic_call_count += 1
            angle_id = "UNKNOWN"
            for msg in messages:
                content = msg.get("content", "")
                if "SELECTED SOCRATIC ANGLE:" in content:
                    m = re.search(r"['\"]id['\"]\s*:\s*['\"]([^'\"]+)['\"]", content)
                    if m:
                        angle_id = m.group(1)

            return schema(
                angle_id=angle_id,
                question=f"Question #{self.socratic_call_count} on {angle_id}: Which indices are ruled out?",
                pedagogical_goal=f"Reason about {angle_id}",
            )

        if step == "evaluator":
            self.evaluator_call_count += 1
            outcome = "REINFORCE"
            if self.evaluator_outcomes:
                outcome = self.evaluator_outcomes.pop(0)

            return schema(
                outcome=outcome,
                confidence=0.9,
                evidence=["Analyzed student reasoning."],
                reasoning_assessment=f"Evaluated reasoning as {outcome}.",
            )

        if step == "transfer":
            return schema(
                task_id="TRANSFER_1",
                prompt="Transfer task: Explain which indices are impossible.",
                target_reasoning="Target boundary elimination reasoning.",
            )

        raise ValueError(f"Unknown step: {step}")


def test_1_three_wrong_answers_trigger_backward_loop(tmp_path):
    """TEST 1 — THREE WRONG ANSWERS TRIGGER BACKWARD LOOP

    Assertions prove:
    1. The run did not become COMPLETE immediately.
    2. A 'backward_loop' record exists in run history.
    3. The backward loop record indicates the reason is three wrong Socratic answers.
    4. The wrong-answer count at trigger time is 3.
    5. The backward loop count increased to 1.
    6. A new Socratic question/intervention is generated after the backward loop.
    7. The flow is waiting for another student answer rather than terminating.
    """
    store = Store(str(tmp_path / "test1.db"))
    run_id = store.create_run("boundary_loop")
    store.append(
        run_id,
        "student_attempt",
        {"text": "while left <= right: ... left = left + 1"},
        produced_by="student",
    )

    stub = StubCall(evaluator_outcomes=["REINFORCE", "REINFORCE", "REINFORCE"])
    flow = build_flow(call=stub)

    # Initial advance: diagnostic -> gating -> socratic #1 -> AWAITING_EXPERT
    state = advance(store, run_id, flow, S)
    assert state == RunState.AWAITING_EXPERT
    assert len(store.history(run_id, "socratic")) == 1

    # Wrong answer #1
    store.append(run_id, "student_response", {"response": "wrong response 1"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    state = advance(store, run_id, flow, S)
    assert state == RunState.AWAITING_EXPERT
    assert len(store.history(run_id, "backward_loop")) == 0
    assert len(store.history(run_id, "socratic")) == 2

    # Wrong answer #2
    store.append(run_id, "student_response", {"response": "wrong response 2"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    state = advance(store, run_id, flow, S)
    assert state == RunState.AWAITING_EXPERT
    assert len(store.history(run_id, "backward_loop")) == 0
    assert len(store.history(run_id, "socratic")) == 3

    # Wrong answer #3 -> MUST trigger backward loop
    store.append(run_id, "student_response", {"response": "wrong response 3"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    state = advance(store, run_id, flow, S)

    # 1. The run did not become COMPLETE immediately.
    assert state != RunState.COMPLETE

    # 7. The flow is waiting for another student answer rather than terminating.
    assert state == RunState.AWAITING_EXPERT

    # 2. A "backward_loop" record exists in run history.
    loops = store.history(run_id, "backward_loop")
    assert len(loops) == 1
    loop_payload = loops[0].payload

    # 3. The backward loop record indicates the reason is three wrong Socratic answers.
    assert loop_payload["reason"] == "three_wrong_socratic_answers"

    # 4. The wrong-answer count at trigger time is 3.
    assert loop_payload["wrong_socratic_count"] == 3

    # 5. The backward loop count increased to 1.
    assert loop_payload["backward_loop_count"] == 1

    # 6. A new Socratic question/intervention is generated after the backward loop.
    socratic_records = store.history(run_id, "socratic")
    assert len(socratic_records) == 4
    assert socratic_records[-1].seq > loops[0].seq


def test_2_two_wrong_answers_do_not_trigger_loop(tmp_path):
    """TEST 2 — TWO WRONG ANSWERS DO NOT TRIGGER LOOP

    Assertions:
    - no backward_loop record exists
    - backward_loop_count remains 0
    - the flow asks another Socratic question
    - the run is not incorrectly completed
    """
    store = Store(str(tmp_path / "test2.db"))
    run_id = store.create_run("boundary_loop")
    store.append(
        run_id,
        "student_attempt",
        {"text": "while left <= right: ... left = left + 1"},
        produced_by="student",
    )

    stub = StubCall(evaluator_outcomes=["REINFORCE", "REINFORCE"])
    flow = build_flow(call=stub)

    # Initial advance
    advance(store, run_id, flow, S)

    # Wrong #1
    store.append(run_id, "student_response", {"response": "wrong 1"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    advance(store, run_id, flow, S)

    # Wrong #2
    store.append(run_id, "student_response", {"response": "wrong 2"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    state = advance(store, run_id, flow, S)

    # Assertions:
    assert len(store.history(run_id, "backward_loop")) == 0
    learning_state = store.latest(run_id, "learning_state")
    assert learning_state.get("backward_loop_count", 0) == 0
    assert len(store.history(run_id, "socratic")) == 3
    assert state == RunState.AWAITING_EXPERT
    assert state != RunState.COMPLETE


def test_3_counter_resets_after_backward_loop(tmp_path):
    """TEST 3 — COUNTER RESETS AFTER BACKWARD LOOP

    Simulate:
    wrong #1, wrong #2, wrong #3 -> backward loop
    Then:
    wrong #1 in NEW cycle, wrong #2 in NEW cycle, correct (PASS)

    Assertions:
    - only ONE backward_loop event occurred
    - the second cycle does NOT trigger another backward loop
    - the correct Socratic answer can progress normally
    - the old three wrong answers were not carried into the new cycle
    """
    store = Store(str(tmp_path / "test3.db"))
    run_id = store.create_run("boundary_loop")
    store.append(
        run_id,
        "student_attempt",
        {"text": "while left <= right: ... left = left + 1"},
        produced_by="student",
    )

    stub = StubCall(
        evaluator_outcomes=[
            "REINFORCE", "REINFORCE", "REINFORCE",  # Cycle 1: 3 wrong -> triggers backward loop
            "REINFORCE", "REINFORCE", "PASS",       # Cycle 2: 2 wrong, then correct
        ]
    )
    flow = build_flow(call=stub)

    # Cycle 1: 3 wrong Socratic responses
    advance(store, run_id, flow, S)
    for i in range(1, 4):
        store.append(run_id, "student_response", {"response": f"cycle 1 wrong {i}"}, produced_by="student")
        store.set_state(run_id, RunState.EVALUATING)
        advance(store, run_id, flow, S)

    # Verify backward loop 1 occurred
    assert len(store.history(run_id, "backward_loop")) == 1

    # Cycle 2: wrong #1
    store.append(run_id, "student_response", {"response": "cycle 2 wrong 1"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    advance(store, run_id, flow, S)
    assert len(store.history(run_id, "backward_loop")) == 1
    assert store.latest(run_id, "learning_state")["wrong_socratic_count"] == 1

    # Cycle 2: wrong #2
    store.append(run_id, "student_response", {"response": "cycle 2 wrong 2"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    advance(store, run_id, flow, S)
    assert len(store.history(run_id, "backward_loop")) == 1
    assert store.latest(run_id, "learning_state")["wrong_socratic_count"] == 2

    # Cycle 2: correct (PASS)
    store.append(run_id, "student_response", {"response": "cycle 2 correct answer"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    state = advance(store, run_id, flow, S)

    # Assertions:
    # - only ONE backward_loop event occurred
    assert len(store.history(run_id, "backward_loop")) == 1
    # - correct Socratic answer progresses normally to transfer task
    assert state == RunState.AWAITING_EXPERT
    assert store.latest(run_id, "transfer") is not None
    latest_ls = store.latest(run_id, "learning_state")
    assert latest_ls["status"] == "SOCRATIC_PASS"
    assert latest_ls["wrong_socratic_count"] == 0


def test_4_fourth_question_angle_is_not_required(tmp_path, monkeypatch):
    """TEST 4 — FOURTH QUESTION/ANGLE IS NOT REQUIRED

    Prove that backward loop is based on wrong-answer count, not angle exhaustion.
    With only 2 angles defined in ANGLES, exactly 3 wrong answers still trigger the backward loop.
    """
    two_angles = [
        {"id": "LIMITED_ANGLE_1", "goal": "Goal 1"},
        {"id": "LIMITED_ANGLE_2", "goal": "Goal 2"},
    ]
    monkeypatch.setattr(angles_module, "ANGLES", two_angles)

    store = Store(str(tmp_path / "test4.db"))
    run_id = store.create_run("boundary_loop")
    store.append(
        run_id,
        "student_attempt",
        {"text": "while left <= right: ... left = left + 1"},
        produced_by="student",
    )

    stub = StubCall(evaluator_outcomes=["REINFORCE", "REINFORCE", "REINFORCE"])
    flow = build_flow(call=stub)

    advance(store, run_id, flow, S)
    for i in range(1, 4):
        store.append(run_id, "student_response", {"response": f"wrong {i}"}, produced_by="student")
        store.set_state(run_id, RunState.EVALUATING)
        advance(store, run_id, flow, S)

    loops = store.history(run_id, "backward_loop")
    assert len(loops) == 1
    assert loops[0].payload["reason"] == "three_wrong_socratic_answers"
    assert loops[0].payload["wrong_socratic_count"] == 3
    assert loops[0].payload["backward_loop_count"] == 1


def test_5_transfer_failure_does_not_trigger_socratic_backward_loop(tmp_path):
    """TEST 5 — TRANSFER FAILURE DOES NOT TRIGGER SOCRATIC BACKWARD LOOP

    Prove that:
    transfer wrong -> transfer reinforcement
    does NOT increment Socratic wrong-answer counter and does NOT trigger Socratic backward_loop.
    """
    store = Store(str(tmp_path / "test5.db"))
    run_id = store.create_run("boundary_loop")
    store.append(
        run_id,
        "student_attempt",
        {"text": "while left <= right: ... left = left + 1"},
        produced_by="student",
    )

    stub = StubCall(
        evaluator_outcomes=[
            "REINFORCE", "REINFORCE",  # 2 wrong socratic
            "PASS",                    # 1 pass socratic -> triggers transfer
            "REINFORCE",               # wrong transfer response
        ]
    )
    flow = build_flow(call=stub)

    # Q1: wrong Socratic
    advance(store, run_id, flow, S)
    store.append(run_id, "student_response", {"response": "socratic wrong 1"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    advance(store, run_id, flow, S)

    # Q2: wrong Socratic
    store.append(run_id, "student_response", {"response": "socratic wrong 2"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    advance(store, run_id, flow, S)

    # Q3: correct Socratic -> advances to transfer
    store.append(run_id, "student_response", {"response": "socratic correct"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    state = advance(store, run_id, flow, S)
    assert state == RunState.AWAITING_EXPERT
    assert store.latest(run_id, "transfer") is not None
    assert len(store.history(run_id, "backward_loop")) == 0

    # Transfer answer: wrong -> evaluated as REINFORCE for stage='transfer'
    store.append(run_id, "student_response", {"response": "transfer wrong response"}, produced_by="student")
    store.set_state(run_id, RunState.EVALUATING)
    state = advance(store, run_id, flow, S)

    # Assertions:
    # 1. No backward_loop was triggered
    assert len(store.history(run_id, "backward_loop")) == 0

    # 2. Latest evaluator record is transfer stage
    evaluator_record = store.latest(run_id, "evaluator")
    assert evaluator_record["stage"] == "transfer"
    assert evaluator_record["outcome"] == "REINFORCE"

    # 3. Learning state reflects transfer reinforcement, not backward loop
    learning_state = store.latest(run_id, "learning_state")
    assert learning_state["status"] == "TRANSFER_REINFORCEMENT_NEEDED"
    assert learning_state.get("backward_loop_count", 0) == 0
