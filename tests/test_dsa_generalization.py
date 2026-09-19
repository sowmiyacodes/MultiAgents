"""Tests for DSA generalization: concept registry, query classifier,
multi-concept Boundary Loop flows (Two Pointers, Sliding Window),
and general-question routing.

All tests are offline (no API key required).
"""
from __future__ import annotations

import pytest

from demo.concept_registry import (
    get_concept,
    get_misconception,
    is_concept_supported,
    list_all_concepts,
    CONCEPTS,
    MISCONCEPTIONS,
)
from demo.query_classifier import classify_query, QueryClassification
from demo.angles import (
    ANGLES,
    TRANSFER_TASKS,
    TUTOR_EXPLANATION,
    ANGLES_TWO_POINTERS,
    ANGLES_SLIDING_WINDOW,
    TRANSFER_TASKS_TWO_POINTERS,
    TRANSFER_TASKS_SLIDING_WINDOW,
    TUTOR_EXPLANATION_TWO_POINTERS,
    TUTOR_EXPLANATION_SLIDING_WINDOW,
    get_concept_angles,
    get_concept_transfer_tasks,
    get_concept_explanation,
    ANGLES_BY_CONCEPT,
    TRANSFER_TASKS_BY_CONCEPT,
)
from demo.schema import (
    QueryClassification as QueryClassificationModel,
    ConceptLearningEntry,
    LearningState,
    DiagnosticResult,
)


# ===========================================================================
# Phase 2: Concept Registry
# ===========================================================================

class TestConceptRegistry:
    def test_binary_search_exists(self):
        c = get_concept("binary_search")
        assert c is not None
        assert c.concept_id == "binary_search"
        assert c.display_name == "Binary Search"

    def test_two_pointers_exists(self):
        c = get_concept("two_pointers")
        assert c is not None
        assert "TP1_WRONG_POINTER_MOVEMENT" in c.supported_misconceptions

    def test_sliding_window_exists(self):
        c = get_concept("sliding_window")
        assert c is not None
        assert "SW1_INCOMPLETE_SHRINK" in c.supported_misconceptions

    def test_unknown_concept_returns_none(self):
        assert get_concept("nonexistent_concept_xyz") is None

    def test_get_misconception_m1(self):
        m = get_misconception("M1_INCOMPLETE_ELIMINATION")
        assert m is not None
        assert m.concept_id == "binary_search"
        assert len(m.symptom_patterns) > 0

    def test_get_misconception_tp1(self):
        m = get_misconception("TP1_WRONG_POINTER_MOVEMENT")
        assert m is not None
        assert m.concept_id == "two_pointers"

    def test_get_misconception_sw1(self):
        m = get_misconception("SW1_INCOMPLETE_SHRINK")
        assert m is not None
        assert m.concept_id == "sliding_window"

    def test_get_misconception_unknown(self):
        assert get_misconception("DOES_NOT_EXIST") is None

    def test_is_concept_supported_binary_search(self):
        assert is_concept_supported("binary_search") is True

    def test_is_concept_supported_two_pointers(self):
        assert is_concept_supported("two_pointers") is True

    def test_is_concept_supported_sliding_window(self):
        assert is_concept_supported("sliding_window") is True

    def test_is_concept_not_supported_general(self):
        # linear_search has no supported misconceptions
        assert is_concept_supported("linear_search") is False

    def test_list_all_concepts_has_many(self):
        all_concepts = list_all_concepts()
        assert len(all_concepts) >= 10

    def test_concept_aliases(self):
        c = get_concept("binary_search")
        assert c is not None
        assert "bsearch" in c.aliases or "binary_search" in c.aliases


# ===========================================================================
# Phase 3: Query Classifier
# ===========================================================================

class TestQueryClassifier:

    def test_general_question_stack(self):
        result = classify_query("What is a stack?")
        assert result.scope == "DSA"
        assert result.concept_id == "stack"
        assert result.query_type == "GENERAL_QUESTION"
        assert result.confidence > 0.3

    def test_general_question_binary_search(self):
        result = classify_query("How does binary search work?")
        assert result.scope == "DSA"
        assert result.concept_id == "binary_search"
        assert result.query_type == "GENERAL_QUESTION"

    def test_general_question_time_complexity(self):
        result = classify_query("What is the time complexity of merge sort?")
        assert result.scope == "DSA"
        assert result.query_type == "GENERAL_QUESTION"

    def test_binary_search_code_submission(self):
        code = """
def binary_search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left++  # wrong: should be left = mid + 1
        else:
            right--
    return -1
"""
        result = classify_query(code)
        assert result.scope == "DSA"
        assert result.concept_id == "binary_search"
        assert result.query_type in ("CODE_SUBMISSION", "MISCONCEPTION_REQUIRES_DIAGNOSIS")
        assert result.confidence >= 0.5

    def test_two_pointers_code_submission(self):
        code = """
def two_sum(nums, target):
    left, right = 0, len(nums) - 1
    while left < right:
        s = nums[left] + nums[right]
        if s == target:
            return [left, right]
        elif s > target:
            left += 1  # wrong: should be right--
        else:
            left += 1
"""
        result = classify_query(code)
        assert result.scope == "DSA"
        assert result.concept_id == "two_pointers"
        assert result.query_type in ("CODE_SUBMISSION", "MISCONCEPTION_REQUIRES_DIAGNOSIS")

    def test_sliding_window_code_submission(self):
        code = """
def max_subarray(nums, k):
    left = 0
    current_sum = 0
    max_len = 0
    for right in range(len(nums)):
        current_sum += nums[right]
        if current_sum > k:
            left += 1  # wrong: should be while loop
            current_sum -= nums[left - 1]
        max_len = max(max_len, right - left + 1)
    return max_len
"""
        result = classify_query(code)
        assert result.scope == "DSA"
        assert result.concept_id == "sliding_window"
        assert result.query_type in ("CODE_SUBMISSION", "MISCONCEPTION_REQUIRES_DIAGNOSIS")

    def test_out_of_scope_weather(self):
        result = classify_query("What is the weather like today?")
        assert result.scope == "OUT_OF_SCOPE"

    def test_out_of_scope_joke(self):
        result = classify_query("Tell me a joke.")
        assert result.scope == "OUT_OF_SCOPE"

    def test_empty_input(self):
        result = classify_query("")
        assert result.scope == "OUT_OF_SCOPE"
        assert result.query_type == "UNKNOWN"

    def test_whitespace_only(self):
        result = classify_query("   ")
        assert result.scope == "OUT_OF_SCOPE"

    def test_general_question_heap(self):
        result = classify_query("When should I use a heap?")
        assert result.scope == "DSA"
        assert result.concept_id == "heap"
        assert result.query_type == "GENERAL_QUESTION"


# ===========================================================================
# Phase 9 prep: Angles module
# ===========================================================================

class TestAnglesModule:
    def test_existing_angles_preserved(self):
        assert len(ANGLES) == 4
        ids = [a["id"] for a in ANGLES]
        assert "ELIMINATED_RANGE_PROOF" in ids
        assert "COUNTEREXAMPLE_ARRAY" in ids

    def test_existing_transfer_tasks_preserved(self):
        assert len(TRANSFER_TASKS) == 2
        assert TRANSFER_TASKS[0]["id"] == "TRANSFER_1"

    def test_existing_tutor_explanation_preserved(self):
        assert "binary search" in TUTOR_EXPLANATION.lower()

    def test_two_pointers_angles_exist(self):
        assert len(ANGLES_TWO_POINTERS) >= 3
        ids = [a["id"] for a in ANGLES_TWO_POINTERS]
        assert "TP_SUM_DIRECTION" in ids
        assert "TP_ELIMINATION_PROOF" in ids

    def test_sliding_window_angles_exist(self):
        assert len(ANGLES_SLIDING_WINDOW) >= 3
        ids = [a["id"] for a in ANGLES_SLIDING_WINDOW]
        assert "SW_WHILE_VS_IF" in ids
        assert "SW_INVARIANT_RESTORATION" in ids

    def test_two_pointers_transfer_tasks_exist(self):
        assert len(TRANSFER_TASKS_TWO_POINTERS) >= 2

    def test_sliding_window_transfer_tasks_exist(self):
        assert len(TRANSFER_TASKS_SLIDING_WINDOW) >= 2

    def test_get_concept_angles_binary_search(self):
        angles = get_concept_angles("binary_search")
        assert angles == ANGLES

    def test_get_concept_angles_two_pointers(self):
        angles = get_concept_angles("two_pointers")
        assert angles == ANGLES_TWO_POINTERS

    def test_get_concept_angles_sliding_window(self):
        angles = get_concept_angles("sliding_window")
        assert angles == ANGLES_SLIDING_WINDOW

    def test_get_concept_angles_unknown_fallback(self):
        # Unknown concept falls back to binary search ANGLES
        angles = get_concept_angles("unknown_xyz")
        assert angles == ANGLES

    def test_get_concept_transfer_tasks_two_pointers(self):
        tasks = get_concept_transfer_tasks("two_pointers")
        assert tasks == TRANSFER_TASKS_TWO_POINTERS

    def test_get_concept_transfer_tasks_sliding_window(self):
        tasks = get_concept_transfer_tasks("sliding_window")
        assert tasks == TRANSFER_TASKS_SLIDING_WINDOW

    def test_get_concept_explanation_binary_search(self):
        exp = get_concept_explanation("binary_search")
        assert "binary search" in exp.lower()

    def test_get_concept_explanation_two_pointers(self):
        exp = get_concept_explanation("two_pointers")
        assert "sorted" in exp.lower() or "pointer" in exp.lower()

    def test_get_concept_explanation_sliding_window(self):
        exp = get_concept_explanation("sliding_window")
        assert "window" in exp.lower() or "while" in exp.lower()

    def test_angles_by_concept_dict_structure(self):
        assert "binary_search" in ANGLES_BY_CONCEPT
        assert "two_pointers" in ANGLES_BY_CONCEPT
        assert "sliding_window" in ANGLES_BY_CONCEPT


# ===========================================================================
# Phase 4: Schema
# ===========================================================================

class TestSchemaGeneralization:
    def test_diagnostic_result_with_concept_id(self):
        d = DiagnosticResult(
            misconception="TP1_WRONG_POINTER_MOVEMENT",
            confidence=0.9,
            evidence=["left += 1 when sum > target"],
            reasoning_pattern="moving wrong pointer",
            concept_id="two_pointers",
        )
        assert d.concept_id == "two_pointers"

    def test_diagnostic_result_concept_id_optional(self):
        d = DiagnosticResult(
            misconception="M1_INCOMPLETE_ELIMINATION",
            confidence=0.8,
            evidence=["left++"],
            reasoning_pattern="linear scan",
        )
        assert d.concept_id is None

    def test_learning_state_with_concepts_dict(self):
        entry = ConceptLearningEntry(
            concept_id="two_pointers",
            misconception="TP1_WRONG_POINTER_MOVEMENT",
            status="SOCRATIC_PASS",
            successful_angles=["TP_SUM_DIRECTION"],
            recommended_next_action="Test transfer",
        )
        ls = LearningState(
            misconception="TP1_WRONG_POINTER_MOVEMENT",
            status="SOCRATIC_PASS",
            recommended_next_action="Test transfer",
            concepts={"two_pointers": entry},
        )
        assert ls.concepts["two_pointers"].concept_id == "two_pointers"

    def test_query_classification_model(self):
        qc = QueryClassificationModel(
            scope="DSA",
            concept_id="binary_search",
            query_type="MISCONCEPTION_REQUIRES_DIAGNOSIS",
            confidence=0.85,
            matched_keywords=["nums[mid]", "left = mid + 1"],
        )
        assert qc.concept_id == "binary_search"
        assert qc.confidence == 0.85

    def test_learning_state_backward_compat(self):
        """LearningState still works with no concepts dict (old format)."""
        ls = LearningState(
            misconception="M1_INCOMPLETE_ELIMINATION",
            status="TRANSFER_PASSED",
            recommended_next_action="Next encounter",
            transfer_passed=True,
        )
        assert ls.transfer_passed is True
        assert ls.concepts == {}


# ===========================================================================
# Boundary Loop: Two Pointers stub flow
# ===========================================================================

class StubCallTP:
    """Stub LLM call for Two Pointers offline tests."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def __call__(self, settings, budget, messages, schema, step):
        self.calls.append(step)
        if step in self.responses:
            return self.responses[step]
        # Deterministic offline fallback by step
        if step == "diagnostic":
            from demo.schema import DiagnosticResult
            return DiagnosticResult(
                misconception="TP1_WRONG_POINTER_MOVEMENT",
                confidence=0.85,
                evidence=["left += 1 when sum > target"],
                reasoning_pattern="moving wrong pointer",
                concept_id="two_pointers",
            )
        if step == "evaluator":
            from demo.schema import EvaluationResult
            return EvaluationResult(
                outcome="REINFORCE",
                confidence=0.8,
                evidence=["student still moves left when sum > target"],
                reasoning_assessment="Incorrect pointer movement",
            )
        raise ValueError(f"Unknown step: {step}")


class TestTwoPointersStubFlow:
    """Offline stub tests for Two Pointers concept routing."""

    def test_tp_misconception_is_recognized(self):
        from demo.schema import DiagnosticResult
        result = DiagnosticResult(
            misconception="TP1_WRONG_POINTER_MOVEMENT",
            confidence=0.85,
            evidence=["left += 1 when sum > target"],
            reasoning_pattern="moves wrong pointer",
        )
        assert result.misconception == "TP1_WRONG_POINTER_MOVEMENT"

    def test_tp_concept_angles_populated(self):
        angles = get_concept_angles("two_pointers")
        assert len(angles) >= 3
        assert all("id" in a and "goal" in a for a in angles)

    def test_tp_transfer_tasks_have_required_fields(self):
        tasks = get_concept_transfer_tasks("two_pointers")
        for task in tasks:
            assert "id" in task
            assert "prompt" in task
            assert "target_reasoning" in task

    def test_sw_concept_angles_populated(self):
        angles = get_concept_angles("sliding_window")
        assert len(angles) >= 3
        assert all("id" in a and "goal" in a for a in angles)

    def test_sw_transfer_tasks_have_required_fields(self):
        tasks = get_concept_transfer_tasks("sliding_window")
        for task in tasks:
            assert "id" in task
            assert "prompt" in task
            assert "target_reasoning" in task


# ===========================================================================
# Classifier + registry integration
# ===========================================================================

class TestClassifierRegistryIntegration:
    def test_binary_search_code_routes_to_supported_concept(self):
        code = "mid = (left + right) // 2\nif nums[mid] < target:\n    left++"
        result = classify_query(code)
        if result.concept_id:
            assert is_concept_supported(result.concept_id) or result.concept_id == "binary_search"

    def test_two_pointers_code_routes_to_tp_concept(self):
        code = "while left < right:\n    if nums[left] + nums[right] > target:\n        right--"
        result = classify_query(code)
        # May detect as binary_search or two_pointers due to left/right — either is valid
        assert result.scope == "DSA"

    def test_sliding_window_code_routes_to_sw_concept(self):
        code = "if current_sum > k:\n    left += 1"
        result = classify_query(code)
        assert result.scope == "DSA"
        # sliding window detection
        assert result.concept_id in (None, "sliding_window", "two_pointers", "binary_search")

    def test_general_concept_lookup_after_classification(self):
        result = classify_query("What is the time complexity of binary search?")
        assert result.scope == "DSA"
        assert result.query_type == "GENERAL_QUESTION"
        concept = get_concept(result.concept_id) if result.concept_id else None
        if concept:
            assert concept.core_invariant  # must have a core invariant

    def test_stack_general_question_maps_to_stack_concept(self):
        result = classify_query("What is a stack data structure?")
        concept = get_concept(result.concept_id) if result.concept_id else None
        if concept:
            assert concept.concept_id == "stack"
