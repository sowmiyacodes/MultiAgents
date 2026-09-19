"""
Test Persistent Learning State in SQLite (data/tutor.db).
"""
import tempfile
from pathlib import Path

from runtime.store import TutorStore


def test_sqlite_persistence_and_reload():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store1 = TutorStore(db_path=db_path)
        student_id = "test_persist_student"

        store1.save_learning_state(
            student_id=student_id,
            topic="binary_search",
            subconcept="boundary_update",
            mastery_status="PROVISIONALLY_MASTERED",
            confidence=0.91,
            successful_transfer_count=1,
            failed_transfer_count=0,
            used_angles=["ELIMINATED_RANGE_PROOF"],
        )
        store1.close()

        # Re-open with a brand new TutorStore instance
        store2 = TutorStore(db_path=db_path)
        state = store2.get_learning_state(student_id, "binary_search", "boundary_update")
        assert state is not None
        assert state["mastery_status"] == "PROVISIONALLY_MASTERED"
        assert state["successful_transfer_count"] == 1
        assert "ELIMINATED_RANGE_PROOF" in state["used_angles"]
        store2.close()

    finally:
        Path(db_path).unlink(missing_ok=True)
