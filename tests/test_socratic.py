"""
Test Socratic Agent (angle selection, no question repeats).
"""
from agents.socratic import SocraticAgent


def test_socratic_question_generation():
    socratic = SocraticAgent()
    res = socratic.ask(
        misconception_id="M1_INCOMPLETE_ELIMINATION",
        angle_id="ELIMINATED_RANGE_PROOF",
        angle_description="Ask which indices are provably eliminated",
        topic="binary_search",
        subconcept="boundary_update",
        used_questions=[],
        student_input="Why does left++ fail?",
    )
    assert res.angle_id == "ELIMINATED_RANGE_PROOF"
    assert len(res.question) > 10
    assert "target" in res.question.lower() or "mid" in res.question.lower()


def test_socratic_does_not_repeat_used_question():
    socratic = SocraticAgent()
    first_q = "If nums[mid] is smaller than the target, which indices can you prove can no longer contain the target — including mid itself? List the exact range that is eliminated."

    res = socratic.ask(
        misconception_id="M1_INCOMPLETE_ELIMINATION",
        angle_id="COUNTEREXAMPLE",
        angle_description="Provide a concrete counterexample",
        topic="binary_search",
        subconcept="boundary_update",
        used_questions=[first_q],
        student_input="Why does left++ fail?",
    )
    assert res.question != first_q
