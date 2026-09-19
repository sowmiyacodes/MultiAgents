"""
DEMO 1: Standard Binary Search Adaptive Tutoring Workflow.

Scenario:
- Student asks: "Why does left++ fail in binary search?"
- Question Classifier identifies: Topic=binary_search, Mode=Adaptive Tutoring
- Diagnostic Agent identifies: M1_INCOMPLETE_ELIMINATION
- Socratic Agent asks focused question on eliminated range
- Student answers with correct elimination reasoning
- Transfer Agent generates fresh transfer problem
- Student answers transfer problem correctly
- Evaluator marks PASS
- Learning state updated in SQLite (PROVISIONALLY_MASTERED)
- Planner recommends variant practice
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.engine import TutoringEngine
from runtime.store import TutorStore
from slice.state_machine import TutorState

SEP = "=" * 60
SUB = "-" * 40


def run_demo(db_path: str = "data/tutor.db") -> None:
    print(SEP)
    print("DEMO 1: BINARY SEARCH ADAPTIVE TUTORING")
    print(SEP)

    store = TutorStore(db_path=db_path)
    engine = TutoringEngine(store=store)

    student_id = "demo_student_bs"
    store.reset_student(student_id)

    query = (
        "int left = 0, right = nums.length - 1;\n"
        "while (left <= right) {\n"
        "    int mid = (left + right) / 2;\n"
        "    if (nums[mid] == target) return mid;\n"
        "    else if (target > nums[mid]) left++;\n"
        "    else right--;\n"
        "}\n"
        "If target > nums[mid], I move the left pointer forward by 1. "
        "Why is moving it by one considered wrong?"
    )

    print(f"\nStudent Query:\n{query}")

    session = engine.start_session(student_id=student_id, initial_query=query)

    # 1. Step to Diagnosis & Socratic question
    engine.step(session)

    print(f"\n{SUB}\n[1] CLASSIFIER")
    print(f"Domain/Topic: {session.classification.topic}")
    print(f"Intent:       {session.classification.intent.value}")
    print(f"Adaptive:     {session.classification.adaptive}")

    print(f"\n{SUB}\n[2] DIAGNOSTIC AGENT")
    print(f"Diagnosed Misconception: {session.diagnosis.misconception_id}")
    print(f"Invariant:               {session.diagnosis.invariant}")
    print(f"Evidence:                {session.diagnosis.evidence[0]}")

    print(f"\n{SUB}\n[3] SOCRATIC AGENT [Angle: {session.current_angle}]")
    print(f"Question: {session.current_question}")

    # Student answers Socratic question correctly
    socratic_answer = (
        "Since the array is sorted and nums[mid] is smaller than target, "
        "all indices from 0 up to mid are provably too small. "
        "They can never contain target, so the entire range 0..mid is eliminated."
    )
    print(f"\nStudent Response:\n> {socratic_answer}")

    # 2. Advance to Evaluation & Transfer Generation
    engine.step(session, student_input=socratic_answer)

    print(f"\n{SUB}\n[4] EVALUATOR AGENT (Socratic)")
    print(f"Result:            {session.current_eval.result.value}")
    print(f"Reasoning Correct: {session.current_eval.reasoning_correct}")
    print(f"Feedback:          {session.current_eval.feedback}")

    print(f"\n{SUB}\n[5] FRESH TRANSFER TASK")
    print(f"Task Problem:\n{session.current_question}")

    # Student answers transfer task correctly
    transfer_answer = (
        "Since nums[mid] is smaller than target 23, all indices through mid are ruled out. "
        "The remaining valid range is [mid+1, right]. "
        "Therefore left should become mid + 1, not left++."
    )
    print(f"\nStudent Transfer Response:\n> {transfer_answer}")

    # 3. Advance to Transfer Evaluation, Update State, and Plan
    engine.step(session, student_input=transfer_answer)

    print(f"\n{SUB}\n[6] EVALUATOR AGENT (Transfer)")
    print(f"Result:           {session.current_eval.result.value}")
    print(f"Transfer Success: {session.current_eval.transfer_success}")

    print(f"\n{SUB}\n[7] LEARNING STATE (SQLite Updated)")
    db_state = store.get_learning_state(student_id, "binary_search", session.classification.subconcept or "general")
    if db_state:
        print(f"Mastery Status:      {db_state['mastery_status']}")
        print(f"Successful Transfer: {db_state['successful_transfer_count']}")
        print(f"Used Angles:         {db_state['used_angles']}")

    print(f"\n{SUB}\n[8] PLANNER AGENT")
    if session.current_plan:
        print(f"Next Action: {session.current_plan.action.value}")
        print(f"Reason:      {session.current_plan.reason}")
        print(f"Message:     {session.current_plan.message}")

    print(f"\n{SEP}\nDEMO 1 COMPLETE: SUCCESS (PASS)\n{SEP}")


if __name__ == "__main__":
    run_demo()
