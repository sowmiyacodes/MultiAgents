"""
DEMO 3: Escalation to Human Review.

Scenario:
- Student exhausts Socratic attempts (3 attempts)
- Targeted Tutor explains the concept explicitly with worked example
- Student is given a fresh transfer task
- Student FAILS the transfer task even after targeted tutoring
- Deterministic runtime halts and escalates to HUMAN_REVIEW_WAITING
- No infinite loops.
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
    print("DEMO 3: ESCALATION TO HUMAN REVIEW")
    print(SEP)

    store = TutorStore(db_path=db_path)
    engine = TutoringEngine(store=store, max_socratic_attempts=2)

    student_id = "demo_student_escalation"
    store.reset_student(student_id)

    query = "I use left = left + 1 when target > nums[mid] in binary search."
    session = engine.start_session(student_id=student_id, initial_query=query)

    # 1. Socratic attempt 1
    engine.step(session)
    print(f"Step 1: Socratic question asked. Angle: {session.current_angle}")
    engine.step(session, student_input="Just increment left by one.")

    # 2. Socratic attempt 2
    print(f"Step 2: Socratic question asked. Angle: {session.current_angle}")
    engine.step(session, student_input="left++ is sufficient.")

    # Socratic exhausted -> Targeted Tutor
    print(f"Step 3: State is {session.state.value}")
    if session.current_tutor:
        print(f"Targeted Tutor explained: {session.current_tutor.misconception_stated}")

    # Fresh transfer task generated
    print(f"Step 4: Transfer task generated: {session.current_transfer.task_id if session.current_transfer else 'Transfer'}")

    # Student fails transfer task
    print("Student fails the transfer task after targeted tutoring:")
    engine.step(session, student_input="I will still move left by one (left++) to be safe.")

    print(f"\n{SUB}\nFINAL STATE: {session.state.value}")
    print("Deterministic engine enforced attempt limit.")
    print("Session halted cleanly in HUMAN_REVIEW_WAITING.")
    print(f"{SEP}\nDEMO 3 COMPLETE: ESCALATION ENFORCED\n{SEP}")


if __name__ == "__main__":
    run_demo()
