"""
Test Recurrence Detection and Socratic Angle Rotation.
"""
import tempfile
from pathlib import Path

from runtime.engine import TutoringEngine
from runtime.store import TutorStore
from slice.state_machine import TutorState


def test_recurrence_switches_socratic_angle():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = TutorStore(db_path=db_path)
        engine = TutoringEngine(store=store, max_socratic_attempts=3)
        student_id = "test_student_recurrence"

        query = "Why does left++ fail in binary search?"
        session = engine.start_session(student_id=student_id, initial_query=query)

        # 1. Step to Socratic
        engine.step(session)
        angle1 = session.current_angle
        assert angle1 is not None

        # 2. Student fails with recurrence
        engine.step(session, student_input="left++ moves to the next element so it is fine.")
        angle2 = session.current_angle
        assert angle2 != angle1, f"Expected different angle, got {angle2}"




        store.close()
    finally:
        Path(db_path).unlink(missing_ok=True)
