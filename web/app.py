"""
Flask Web Application & API Layer for THINKAGAIN Multi-Agent Tutoring System.

Provides the frontend routes and a thin JSON API bridge to the existing
TutoringEngine, preserving all agents, states, and SQLite persistence.
"""
from __future__ import annotations

import os
import secrets
import sqlite3
from pathlib import Path
from typing import Any, Optional

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session as flask_session,
    url_for,
)

from runtime.engine import TutoringEngine, TutoringSession
from runtime.session import resume_session
from runtime.store import TutorStore, SCHEMA
from slice.config import settings
from slice.state_machine import TutorState


class WebTutorStore(TutorStore):
    """
    TutorStore subclass that opens the SQLite connection with
    check_same_thread=False, allowing Flask's threaded request
    handling without modifying the original store.py.
    """

    def __init__(self, db_path: str | Path = "run.db") -> None:
        self.path = Path(db_path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        # Allow the connection to be used across Flask threads
        self.db = sqlite3.connect(
            str(self.path),
            isolation_level=None,
            check_same_thread=False,
        )
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)


def serialize_session_state(session: TutoringSession) -> dict[str, Any]:
    """Helper to extract clean UI-facing state from a TutoringSession."""
    # Current agent determination based on state and stage
    current_agent = "System"
    agent_status = "Active"
    current_phase = "Initializing"

    if session.state == TutorState.WAITING_FOR_STUDENT:
        if session.stage == "transfer":
            current_agent = "Transfer Task Agent"
            current_phase = "Transfer Challenge"
            agent_status = "Waiting for your answer"
        else:
            current_agent = "Socratic Agent"
            current_phase = "Socratic Guidance"
            agent_status = "Waiting for your answer"
    elif session.state == TutorState.SOCRATIC_GUIDANCE:
        current_agent = "Socratic Agent"
        current_phase = "Socratic Guidance"
        agent_status = "Formulating question"
    elif session.state == TutorState.GENERATE_TRANSFER_TASK:
        current_agent = "Transfer Task Agent"
        current_phase = "Transfer Challenge"
        agent_status = "Generating transfer task"
    elif session.state == TutorState.DIAGNOSING:
        current_agent = "Diagnostic Agent"
        current_phase = "Diagnosing Approach"
        agent_status = "Analyzing code & reasoning"
    elif session.state == TutorState.EVALUATING:
        current_agent = "Evaluator Agent"
        current_phase = "Evaluating Reasoning"
        agent_status = "Evaluating student response"
    elif session.state == TutorState.TARGETED_TUTORING:
        current_agent = "Targeted Tutor Agent"
        current_phase = "Targeted Tutoring"
        agent_status = "Explaining core invariant"
    elif session.state == TutorState.PLAN_NEXT:
        current_agent = "Planner Agent"
        current_phase = "Planning Next Steps"
        agent_status = "Synthesizing learning path"
    elif session.state == TutorState.COMPLETE:
        current_agent = "Learning System"
        current_phase = "Session Completed"
        agent_status = "Completed"
    elif session.state in (TutorState.ESCALATED, TutorState.HUMAN_REVIEW_WAITING):
        current_agent = "Human Reviewer"
        current_phase = "Instructor Escalation"
        agent_status = "Escalated for human review"

    topic_name = "DSA Concept"
    subconcept_name = ""
    if session.classification:
        topic_name = session.classification.topic.replace("_", " ").title()
        if session.classification.subconcept:
            subconcept_name = session.classification.subconcept.replace("_", " ").title()

    # Determine completed states from events audit log
    events = session.store.get_session_events(session.session_id)
    visited_states: set[str] = {TutorState.START.value}
    for ev in events:
        if ev.get("event_type") == "STATE_TRANSITION":
            data = ev.get("data", {})
            if "from" in data:
                visited_states.add(data["from"])
            if "to" in data:
                visited_states.add(data["to"])
    if session.state.value:
        visited_states.add(session.state.value)

    # Check if student options (Try Again / Hint / Worked Example) should be offered
    options_available = False
    if (
        session.current_eval
        and session.current_eval.result != TutorState.COMPLETE
        and not session.current_eval.reasoning_correct
        and session.state == TutorState.WAITING_FOR_STUDENT
        and session.stage == "socratic"
    ):
        options_available = True

    eval_data = None
    if session.current_eval:
        eval_data = {
            "result": session.current_eval.result.value if hasattr(session.current_eval.result, "value") else str(session.current_eval.result),
            "reasoning_correct": session.current_eval.reasoning_correct,
            "transfer_success": session.current_eval.transfer_success,
            "feedback": session.current_eval.feedback,
            "misconception_recurred": session.current_eval.misconception_recurred,
        }

    tutor_data = None
    if session.current_tutor:
        tutor_data = {
            "misconception_stated": session.current_tutor.misconception_stated,
            "explanation": session.current_tutor.explanation,
            "worked_example": session.current_tutor.worked_example,
            "key_insight": session.current_tutor.key_insight,
        }

    plan_data = None
    if session.current_plan:
        plan_data = {
            "action": session.current_plan.action.value if hasattr(session.current_plan.action, "value") else str(session.current_plan.action),
            "reason": session.current_plan.reason,
            "message": session.current_plan.message,
        }

    diagnosis_data = None
    if session.diagnosis:
        diagnosis_data = {
            "misconception_id": session.diagnosis.misconception_id,
            "invariant": session.diagnosis.invariant,
            "evidence": session.diagnosis.evidence,
        }

    return {
        "session_id": session.session_id,
        "student_id": session.student_id,
        "state": session.state.value,
        "is_terminal": session.state.is_terminal,
        "stage": session.stage,
        "current_agent": current_agent,
        "agent_status": agent_status,
        "current_phase": current_phase,
        "topic": topic_name,
        "subconcept": subconcept_name,
        "current_question": session.current_question,
        "current_angle": session.current_angle,
        "options_available": options_available,
        "evaluation": eval_data,
        "targeted_tutor": tutor_data,
        "diagnosis": diagnosis_data,
        "plan": plan_data,
        "general_response": session.general_response,
        "completed_states": sorted(list(visited_states)),
        "messages": getattr(session, "chat_history", []),
    }


def create_app(test_config: Optional[dict[str, Any]] = None) -> Flask:
    """Application factory for the Flask UI and API."""
    app_dir = Path(__file__).parent.resolve()
    app = Flask(
        __name__,
        template_folder=str(app_dir / "templates"),
        static_folder=str(app_dir / "static"),
    )

    app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(16))

    cfg = settings()
    db_path = cfg.database_path
    if test_config and "DATABASE_PATH" in test_config:
        db_path = test_config["DATABASE_PATH"]

    store = TutorStore(db_path=db_path)
    engine = TutoringEngine(store=store, db_path=db_path)

    # In-memory registry of active sessions for live interaction
    active_sessions: dict[str, TutoringSession] = {}

    def get_or_restore_session(session_id: Optional[str]) -> Optional[TutoringSession]:
        if not session_id:
            return None
        if session_id in active_sessions:
            return active_sessions[session_id]
        # Attempt to resume existing session from store
        resumed = resume_session(engine, session_id)
        if resumed:
            if not hasattr(resumed, "chat_history"):
                resumed.chat_history = []
            active_sessions[session_id] = resumed
            return resumed
        return None

    # ── Page Routes ──────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return redirect(url_for("chatbot_page"))

    @app.route("/chatbot")
    def chatbot_page():
        active_id = flask_session.get("session_id")
        return render_template("chatbot.html", active_session_id=active_id)

    @app.route("/graph")
    def graph_page():
        active_id = flask_session.get("session_id")
        return render_template("graph.html", active_session_id=active_id)

    # ── API Routes ───────────────────────────────────────────────────────────

    @app.route("/api/state", methods=["GET"])
    def get_state():
        session_id = flask_session.get("session_id")
        sess = get_or_restore_session(session_id)
        if not sess:
            return jsonify({
                "active": False,
                "session_id": None,
                "state": None,
                "messages": [],
                "completed_states": [],
                "current_agent": "Standby",
                "agent_status": "Ready",
                "current_phase": "Welcome",
                "topic": "DSA Tutoring",
                "subconcept": "",
            })

        data = serialize_session_state(sess)
        data["active"] = True
        return jsonify(data)

    @app.route("/api/session/start", methods=["POST"])
    def start_session():
        payload = request.get_json(silent=True) or {}
        initial_query = payload.get("initial_query", "").strip()
        student_id = payload.get("student_id", "student_001").strip() or "student_001"

        if not initial_query:
            return jsonify({"error": "Initial DSA query/code is required"}), 400

        # Start new session through the existing engine
        session = engine.start_session(student_id=student_id, initial_query=initial_query)
        session.chat_history = []

        # Record user's initial query in chat history
        session.chat_history.append({
            "id": f"msg_{len(session.chat_history)+1}",
            "role": "user",
            "type": "initial_query",
            "text": initial_query,
        })

        # Advance engine until it reaches WAITING_FOR_STUDENT or terminal COMPLETE
        while not session.state.is_terminal and session.state != TutorState.WAITING_FOR_STUDENT:
            engine.step(session)
            engine.store.sync_session_json_summary(session.session_id)

        # Append assistant question/response
        if session.state == TutorState.WAITING_FOR_STUDENT:
            if session.stage == "socratic" and session.current_question:
                session.chat_history.append({
                    "id": f"msg_{len(session.chat_history)+1}",
                    "role": "assistant",
                    "type": "socratic_question",
                    "angle": session.current_angle,
                    "text": session.current_question,
                })
        elif session.state == TutorState.COMPLETE:
            if session.classification and not session.classification.adaptive:
                session.chat_history.append({
                    "id": f"msg_{len(session.chat_history)+1}",
                    "role": "assistant",
                    "type": "general_explanation",
                    "text": session.general_response or "General DSA explanation completed.",
                })

        # Store in active sessions and cookie
        active_sessions[session.session_id] = session
        flask_session["session_id"] = session.session_id
        flask_session["student_id"] = student_id

        # Save persistent state in SQLite store
        store.save_session_state(
            session.session_id,
            student_id,
            {"chat_history": session.chat_history},
        )
        engine.store.sync_session_json_summary(session.session_id)

        data = serialize_session_state(session)
        data["active"] = True
        return jsonify(data)

    @app.route("/api/chat", methods=["POST"])
    def send_chat_message():
        session_id = flask_session.get("session_id")
        session = get_or_restore_session(session_id)
        if not session:
            return jsonify({"error": "No active tutoring session. Please start a session."}), 400

        if session.state.is_terminal:
            return jsonify({"error": "Session is completed or escalated."}), 400

        payload = request.get_json(silent=True) or {}
        message = payload.get("message", "").strip()
        if not message:
            return jsonify({"error": "Message cannot be empty."}), 400

        if not hasattr(session, "chat_history"):
            session.chat_history = []

        # Record student answer
        session.chat_history.append({
            "id": f"msg_{len(session.chat_history)+1}",
            "role": "user",
            "type": "answer",
            "text": message,
        })

        # Step engine with student answer
        engine.step(session, student_input=message)
        engine.store.sync_session_json_summary(session.session_id)

        # Check for evaluation result
        if session.current_eval:
            eval_payload = {
                "id": f"msg_{len(session.chat_history)+1}",
                "role": "evaluator",
                "type": "evaluation",
                "result": session.current_eval.result.value if hasattr(session.current_eval.result, "value") else str(session.current_eval.result),
                "reasoning_correct": session.current_eval.reasoning_correct,
                "transfer_success": session.current_eval.transfer_success,
                "feedback": session.current_eval.feedback,
            }
            session.chat_history.append(eval_payload)

        # If targeted tutoring was triggered during steps
        if session.current_tutor and not any(m.get("type") == "targeted_tutor" for m in session.chat_history[-2:]):
            session.chat_history.append({
                "id": f"msg_{len(session.chat_history)+1}",
                "role": "assistant",
                "type": "targeted_tutor",
                "misconception_stated": session.current_tutor.misconception_stated,
                "explanation": session.current_tutor.explanation,
                "worked_example": session.current_tutor.worked_example,
                "key_insight": session.current_tutor.key_insight,
            })

        # Advance engine if in an intermediate step
        while not session.state.is_terminal and session.state != TutorState.WAITING_FOR_STUDENT:
            engine.step(session)
            engine.store.sync_session_json_summary(session.session_id)

        # Record next question or terminal message
        if session.state == TutorState.WAITING_FOR_STUDENT:
            if session.stage == "transfer" and session.current_transfer:
                session.chat_history.append({
                    "id": f"msg_{len(session.chat_history)+1}",
                    "role": "assistant",
                    "type": "transfer_task",
                    "task_id": session.current_transfer.task_id,
                    "text": session.current_question,
                })
            elif session.stage == "socratic" and session.current_question:
                session.chat_history.append({
                    "id": f"msg_{len(session.chat_history)+1}",
                    "role": "assistant",
                    "type": "socratic_question",
                    "angle": session.current_angle,
                    "text": session.current_question,
                })

        elif session.state == TutorState.COMPLETE:
            session.chat_history.append({
                "id": f"msg_{len(session.chat_history)+1}",
                "role": "assistant",
                "type": "completion",
                "text": "You successfully demonstrated the required reasoning.",
                "plan": session.current_plan.message if session.current_plan else "",
            })

        elif session.state in (TutorState.ESCALATED, TutorState.HUMAN_REVIEW_WAITING):
            session.chat_history.append({
                "id": f"msg_{len(session.chat_history)+1}",
                "role": "assistant",
                "type": "escalation",
                "text": "The maximum attempts were reached. Session escalated to HUMAN INSTRUCTOR REVIEW.",
            })

        # Sync persistent state in SQLite & JSON
        store.save_session_state(
            session.session_id,
            session.student_id,
            {"chat_history": session.chat_history},
        )
        engine.store.sync_session_json_summary(session.session_id)

        data = serialize_session_state(session)
        data["active"] = True
        return jsonify(data)

    @app.route("/api/option", methods=["POST"])
    def handle_option():
        """Handles the 3 student options when reasoning needs another step: Try Again, Get Hint, Worked Example."""
        session_id = flask_session.get("session_id")
        session = get_or_restore_session(session_id)
        if not session:
            return jsonify({"error": "No active session."}), 400

        payload = request.get_json(silent=True) or {}
        option = payload.get("option", "").strip().lower()

        if not hasattr(session, "chat_history"):
            session.chat_history = []

        if option == "hint":
            invariant = session.diagnosis.invariant if session.diagnosis else "Key boundary invariant"
            hint_msg = (
                f"Focus on the invariant: {invariant}. "
                "When an element at mid fails the target test, what can you say about ALL elements before/after it?"
            )
            msg = {
                "id": f"msg_{len(session.chat_history)+1}",
                "role": "assistant",
                "type": "hint",
                "text": hint_msg,
            }
            session.chat_history.append(msg)
            store.save_session_state(session.session_id, session.student_id, {"chat_history": session.chat_history})
            engine.store.sync_session_json_summary(session.session_id)
            return jsonify({"success": True, "message": msg, "state": serialize_session_state(session)})

        elif option == "worked_example":
            if session.diagnosis:
                tutor_out = engine.tutor.explain(
                    misconception_id=session.diagnosis.misconception_id,
                    invariant=session.diagnosis.invariant,
                    topic=session.classification.topic if session.classification else "binary_search",
                    subconcept=session.classification.subconcept if session.classification else None,
                    student_input=session.current_query,
                )
                msg = {
                    "id": f"msg_{len(session.chat_history)+1}",
                    "role": "assistant",
                    "type": "targeted_tutor",
                    "misconception_stated": tutor_out.misconception_stated,
                    "explanation": tutor_out.explanation,
                    "worked_example": tutor_out.worked_example,
                    "key_insight": tutor_out.key_insight,
                }
                session.chat_history.append(msg)
                store.save_session_state(session.session_id, session.student_id, {"chat_history": session.chat_history})
                engine.store.sync_session_json_summary(session.session_id)
                return jsonify({"success": True, "message": msg, "state": serialize_session_state(session)})

        elif option in ("retry", "try_again"):
            # Acknowledge Try Again - student proceeds with the current Socratic question
            return jsonify({"success": True, "state": serialize_session_state(session)})

        return jsonify({"error": f"Invalid option: {option}"}), 400

    @app.route("/api/session/new", methods=["POST"])
    def reset_session():
        """Explicitly clear the active session cookie so the user can start a fresh session."""
        flask_session.pop("session_id", None)
        return jsonify({"success": True})

    @app.route("/api/session/<session_id>/download", methods=["GET"])
    def download_session(session_id: str):
        """Secure download endpoint for the active session's JSON profile."""
        active_id = flask_session.get("session_id")
        if not active_id or active_id != session_id:
            return jsonify({"error": "Unauthorized access to session data."}), 403

        # Call the existing store's sync method to ensure latest data is written
        json_path = engine.store.sync_session_json_summary(session_id)
        if not json_path.exists():
            return jsonify({"error": "Session profile file not found."}), 404

        return send_file(
            str(json_path.resolve()),
            as_attachment=True,
            download_name=f"{session_id}_profile.json",
            mimetype="application/json",
        )

    return app
