"""
DEMO 2: Socratic Angle Rotation on Recurrence & Fallback to Targeted Tutor.

Scenario:
- Student repeatedly exhibits misconception (M1_INCOMPLETE_ELIMINATION)
- Attempt 1: Angle A used -> student demonstrates misconception again (recurrence)
- Attempt 2: System selects a DIFFERENT angle B -> student fails again
- Attempt 3: System selects a DIFFERENT angle C -> student fails again
- Maximum Socratic attempts (3) exhausted
- System transitions to TARGETED TUTOR AGENT (explicit explanation + worked example)
- Targeted tutor prompts student to apply reasoning
- Fresh transfer task generated
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.engine import TutoringEngine
from runtime.store import TutorStore
from slice.state_machine import TutorState

SEP = "=" * 60
SUB = "-" * 40


def run_demo(db_path: str = "data/tutor.db") -> None:
    print(SEP)
    print("DEMO 2: RECURRENCE & TARGETED TUTOR ESCALATION")
    print(SEP)

    store = TutorStore(db_path=db_path)
    engine = TutoringEngine(store=store, max_socratic_attempts=3)

    student_id = "demo_student_recurrence"
    store.reset_student(student_id)

    query = "Why does left++ fail in binary search when nums[mid] < target?"
    print(f"\nStudent Query: {query}")

    session = engine.start_session(student_id=student_id, initial_query=query)

    # 1. Step to first Socratic question
    engine.step(session)
    print(f"\n[Attempt 1] Socratic Angle: {session.current_angle}")
    print(f"Question: {session.current_question}")

    # Student fails (repeats left++ error)
    bad_resp_1 = "I still think left++ is right because we only need to move past the current left pointer."
    print(f"Student Answer: {bad_resp_1}")
    engine.step(session, student_input=bad_resp_1)

    print(f"Evaluation: {session.current_eval.result.value} | Misconception Recurred: {session.current_eval.misconception_recurred}")
    print(f"Next State: {session.state.value}")

    # 2. Second Socratic question with NEW angle
    print(f"\n[Attempt 2] Socratic Angle: {session.current_angle} (different angle)")
    print(f"Question: {session.current_question}")

    bad_resp_2 = "If I increment left by 1, I won't miss any elements. Moving by more might skip the target."
    print(f"Student Answer: {bad_resp_2}")
    engine.step(session, student_input=bad_resp_2)

    print(f"Evaluation: {session.current_eval.result.value} | Misconception Recurred: {session.current_eval.misconception_recurred}")
    print(f"Next State: {session.state.value}")

    # 3. Third Socratic question with NEW angle
    print(f"\n[Attempt 3] Socratic Angle: {session.current_angle} (third distinct angle)")
    print(f"Question: {session.current_question}")

    bad_resp_3 = "Left should just move by one step so we check index by index."
    print(f"Student Answer: {bad_resp_3}")
    engine.step(session, student_input=bad_resp_3)

    print(f"Evaluation: {session.current_eval.result.value}")
    print("Socratic budget exhausted (3/3 attempts)!")

    # 4. Advance to Targeted Tutor
    print(f"\n{SUB}\n[4] TARGETED TUTOR AGENT ACTIVATED")
    if session.current_tutor:
        print(f"Misconception Stated: {session.current_tutor.misconception_stated}")
        print(f"Explanation:\n{session.current_tutor.explanation}")
        print(f"Worked Example:\n{session.current_tutor.worked_example}")
        print(f"Key Insight:          {session.current_tutor.key_insight}")

    # 5. Advance to Fresh Transfer Task
    print(f"\n{SUB}\n[5] FRESH TRANSFER TASK AFTER TARGETED TUTOR")
    print(f"Task: {session.current_question}")

    print(f"\n{SEP}\nDEMO 2 COMPLETE: TARGETED TUTOR TRIGGERED\n{SEP}")


if __name__ == "__main__":
    run_demo()
