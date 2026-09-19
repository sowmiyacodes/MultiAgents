"""
Test Diagnostic Agent (evidence-driven misconception detection).
"""
from agents.diagnostic import DiagnosticAgent


def test_diagnose_incomplete_elimination():
    diagnostic = DiagnosticAgent()
    student_text = (
        "int left = 0, right = nums.length - 1;\n"
        "while (left <= right) {\n"
        "    int mid = (left + right) / 2;\n"
        "    if (target > nums[mid]) left++;\n"
        "}"
    )
    res = diagnostic.diagnose(student_text, topic="binary_search", subconcept="boundary_update")
    assert res.misconception_id == "M1_INCOMPLETE_ELIMINATION"
    assert len(res.evidence) >= 1
    assert "left" in res.invariant.lower() or "mid" in res.invariant.lower()
    assert res.confidence > 0.5


def test_diagnose_loop_condition():
    diagnostic = DiagnosticAgent()
    student_text = "I used while left < right in my binary search, but single element tests fail."
    res = diagnostic.diagnose(student_text, topic="binary_search", subconcept="loop_condition")
    assert res.misconception_id == "M2_INCORRECT_LOOP_CONDITION"


def test_diagnose_unknown_topic_generic_fallback():
    diagnostic = DiagnosticAgent()
    res = diagnostic.diagnose("I don't understand how lowlink values work in Tarjan's", topic="tarjan", subconcept=None)
    assert res is not None
    assert "tarjan" in res.misconception_id.lower() or "tarjan" in res.concept.lower()
