"""
Test Socratic Attempt Limits and Tutor Escalation.
"""
import tempfile
from pathlib import Path

from runtime.engine import TutoringEngine
from runtime.store import TutorStore
from slice.state_machine import TutorState


def test_socratic_exhaustion_triggers_targeted_tutor():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        store = TutorStore(db_path=db_path)
        # 2 max socratic attempts
        engine = TutoringEngine(store=store, max_socratic_attempts=2)
        session = engine.start_session("test_esc_student", "Why does left++ fail in binary search?")

        # Attempt 1 fails
        engine.step(session)
        engine.step(session, student_input="Just use left++.")

        # Attempt 2 fails
        engine.step(session, student_input="I still prefer left++.")

        # Budget exhausted -> Targeted Tutor -> Generate Transfer Task -> WAITING_FOR_STUDENT
        assert session.current_tutor is not None
        assert session.state == TutorState.WAITING_FOR_STUDENT
        assert session.stage == "transfer"

        # If student fails transfer again after tutor -> ESCALATED -> HUMAN_REVIEW_WAITING
        engine.step(session, student_input="left++ still works.")
        assert session.state == TutorState.HUMAN_REVIEW_WAITING

        store.close()
    finally:
        Path(db_path).unlink(missing_ok=True)
