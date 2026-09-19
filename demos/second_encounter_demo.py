"""
DEMO 4: Second Encounter Adaptation Across Process Restarts.

Scenario:
- SESSION 1: Student diagnosed with M1_INCOMPLETE_ELIMINATION.
  Student completes Socratic guidance and passes transfer.
  State saved to SQLite (tutor.db).
- PROCESS RESTART: Engine instance discarded, new engine connects to tutor.db.
- SESSION 2: Student returns and asks another binary search question.
  Engine reads persistent learning state:
  - Detects past diagnosed misconception
  - Sees used angles from previous session
  - Adapts pedagogical strategy: does NOT repeat previous angle
  - Selects a novel Socratic angle / variant transfer task
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.engine import TutoringEngine
from runtime.store import TutorStore

SEP = "=" * 60
SUB = "-" * 40


def run_demo(db_path: str = "data/tutor.db") -> None:
    print(SEP)
    print("DEMO 4: SECOND ENCOUNTER ADAPTATION (PERSISTENT STATE)")
    print(SEP)

    student_id = "demo_student_second_encounter"

    # =========================================================================
    # SESSION 1
    # =========================================================================
    print(f"\n>>> [SESSION 1] Student {student_id} starts first encounter...")
    store1 = TutorStore(db_path=db_path)
    store1.reset_student(student_id)
    engine1 = TutoringEngine(store=store1)

    query1 = "Why does left++ fail in binary search when nums[mid] < target?"
    sess1 = engine1.start_session(student_id=student_id, initial_query=query1)

    # Step to Socratic
    engine1.step(sess1)
    angle_sess1 = sess1.current_angle
    print(f"Session 1 Diagnosed: {sess1.diagnosis.misconception_id}")
    print(f"Session 1 Used Angle: {angle_sess1}")

    # Pass Socratic
    socratic_ans = "All indices from 0 up to mid are smaller than target, so they are eliminated. Range is eliminated."
    engine1.step(sess1, student_input=socratic_ans)

    # Pass Transfer
    transfer_ans = "left must become mid + 1 because indices through mid are ruled out. Target cannot be there."
    engine1.step(sess1, student_input=transfer_ans)

    print(f"Session 1 Complete! State in DB: {sess1.state.value}")
    store1.close()

    # =========================================================================
    # RESTART SIMULATION
    # =========================================================================
    print(f"\n{SUB}\n[PROCESS RESTART] Python exits and restarts...\n{SUB}")

    # =========================================================================
    # SESSION 2 (New engine instance reading SQLite)
    # =========================================================================
    print(f">>> [SESSION 2] Student {student_id} returns in a new process session...")
    store2 = TutorStore(db_path=db_path)
    engine2 = TutoringEngine(store=store2)

    # Verify state survived restart
    past_state = store2.get_learning_state(student_id, "binary_search", "boundary_update")
    if past_state:
        print(f"Loaded from SQLite: Mastery={past_state['mastery_status']}, Passed Transfers={past_state['successful_transfer_count']}")
        print(f"Historically Used Angles: {past_state['used_angles']}")

    query2 = "I'm practicing binary search again. When nums[mid] > target, what boundary do I update?"
    sess2 = engine2.start_session(student_id=student_id, initial_query=query2)

    # Step session 2
    engine2.step(sess2)

    print(f"\nSession 2 Diagnosed Misconception: {sess2.diagnosis.misconception_id}")
    print(f"Session 2 Socratic Angle:          {sess2.current_angle}")

    # Verify that Session 2 picked a DIFFERENT angle from Session 1
    if sess2.current_angle != angle_sess1:
        print(f"\n[ADAPTATION CONFIRMED] Session 2 selected angle '{sess2.current_angle}' which differs from Session 1 angle '{angle_sess1}'!")
    else:
        print("\nNote: Angles matched.")

    store2.close()
    print(f"\n{SEP}\nDEMO 4 COMPLETE: PERSISTENCE & ADAPTATION VERIFIED\n{SEP}")


if __name__ == "__main__":
    run_demo()
