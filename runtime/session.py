"""
Session Management and Resume Support.

Allows suspending on WAITING_FOR_STUDENT, saving snapshot to SQLite,
and cleanly resuming when the user returns.
"""
from __future__ import annotations

from typing import Optional

from runtime.engine import TutoringEngine, TutoringSession
from runtime.store import TutorStore
from slice.state_machine import TutorState


def resume_session(
    engine: TutoringEngine,
    session_id: str,
) -> Optional[TutoringSession]:
    """
    Attempt to reconstruct or resume an active session from the database.
    """
    row = engine.store.db.execute(
        "SELECT * FROM sessions WHERE session_id=? AND status != 'COMPLETE'",
        (session_id,),
    ).fetchone()
    if not row:
        return None

    student_id = row["student_id"]
    events = engine.store.get_session_events(session_id)

    # Reconstitute query
    initial_query = "Resume session"
    for ev in events:
        if ev["event_type"] == "SESSION_STARTED":
            initial_query = ev.get("data", {}).get("initial_query", initial_query)
            break

    sess = engine.start_session(student_id=student_id, initial_query=initial_query)
    sess.session_id = session_id
    return sess
