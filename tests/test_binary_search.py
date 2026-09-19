"""
Test Binary Search Full Adaptive Workflow.
"""
import tempfile
from pathlib import Path

from runtime.engine import TutoringEngine
from runtime.store import TutorStore
from slice.state_machine import TutorState


def test_full_binary_search_workflow_pass():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = TutorStore(db_path=db_path)
        try:
            engine = TutoringEngine(store=store)
            student_id = "test_bs_full"

            query = (
                "while (left <= right) {\n"
                "    int mid = (left + right) / 2;\n"
                "    if (target > nums[mid]) left++;\n"
                "}\n"
                "Why is left++ considered wrong here?"
            )
            session = engine.start_session(student_id, query)

            # 1. Advance to Socratic
            engine.step(session)
            assert session.state == TutorState.WAITING_FOR_STUDENT
            assert session.diagnosis.misconception_id == "M1_INCOMPLETE_ELIMINATION"

            # 2. Student answers Socratic correctly
            socratic_ans = "All indices from 0 to mid are smaller than target, so they are provably eliminated. Target cannot be anywhere in 0..mid, so left must be updated to mid + 1."
            engine.step(session, student_input=socratic_ans)

            # Now in transfer stage
            assert session.stage == "transfer"
            assert session.state == TutorState.WAITING_FOR_STUDENT
            assert session.current_transfer is not None

            # 3. Student answers transfer correctly
            transfer_ans = "Because array elements from 0 to mid are strictly less than target, all of them are ruled out. Thus, left boundary must be updated to mid + 1 to skip all eliminated elements."
            engine.step(session, student_input=transfer_ans)


            # Check final completion
            assert session.state == TutorState.COMPLETE
            assert session.current_plan is not None

            # Check SQLite store
            learning_state = store.get_learning_state(student_id, "binary_search", "boundary_update")
            assert learning_state is not None
            assert learning_state["mastery_status"] == "PROVISIONALLY_MASTERED"
            assert learning_state["successful_transfer_count"] == 1
        finally:
            store.close()
    finally:
        Path(db_path).unlink(missing_ok=True)

