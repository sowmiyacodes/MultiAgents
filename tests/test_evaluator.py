"""
Test Evaluator Agent (verifies reasoning, transfer success, recurrence).
"""
from agents.evaluator import EvaluatorAgent
from llm.schemas import EvalResult


def test_evaluator_pass():
    evaluator = EvaluatorAgent()
    res = evaluator.evaluate(
        student_response="Because nums[mid] < target, every element up to mid is impossible. Left must become mid + 1.",
        misconception_id="M1_INCOMPLETE_ELIMINATION",
        topic="binary_search",
        stage="socratic",
        target_reasoning="Eliminate all indices 0..mid",
        invariant="Target cannot be in 0..mid",
        question_or_task="Which indices can no longer contain target?",
    )
    assert res.result == EvalResult.PASS
    assert res.reasoning_correct is True
    assert res.misconception_recurred is False


def test_evaluator_fail_recurrence():
    evaluator = EvaluatorAgent()
    res = evaluator.evaluate(
        student_response="I think left++ is enough because we only need to move by one step.",
        misconception_id="M1_INCOMPLETE_ELIMINATION",
        topic="binary_search",
        stage="socratic",
        target_reasoning="Eliminate all indices 0..mid",
        invariant="Target cannot be in 0..mid",
        question_or_task="Which indices can no longer contain target?",
    )
    assert res.result == EvalResult.FAIL
    assert res.reasoning_correct is False
    assert res.misconception_recurred is True
