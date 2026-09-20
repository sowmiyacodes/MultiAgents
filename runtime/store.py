"""
Persistent SQLite Store for the DSA Adaptive Tutoring System.

Database: data/tutor.db (configurable via DATABASE_PATH)
Maintains:
- students
- sessions
- learning_state (mastery, transfer counts, used angles, history)
- misconceptions (occurrences, evidence, resolution)
- attempts (Socratic & transfer responses with outcomes)
- events (audit log of all state machine transitions and actions)

Append-only audit patterns and transactional safety. Survives process restarts.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id  TEXT PRIMARY KEY,
    name        TEXT,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    student_id  TEXT NOT NULL REFERENCES students(student_id),
    topic       TEXT NOT NULL,
    mode        TEXT NOT NULL,
    status      TEXT NOT NULL,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_state (
    student_id                TEXT NOT NULL REFERENCES students(student_id),
    topic                     TEXT NOT NULL,
    subconcept                TEXT NOT NULL,
    mastery_status            TEXT NOT NULL DEFAULT 'UNKNOWN',
    confidence                REAL NOT NULL DEFAULT 0.0,
    successful_transfer_count INTEGER NOT NULL DEFAULT 0,
    failed_transfer_count     INTEGER NOT NULL DEFAULT 0,
    last_seen                 REAL NOT NULL,
    last_strategy             TEXT NOT NULL DEFAULT '',
    used_angles_json          TEXT NOT NULL DEFAULT '[]',
    history_json              TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (student_id, topic, subconcept)
);

CREATE TABLE IF NOT EXISTS misconceptions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        TEXT NOT NULL REFERENCES students(student_id),
    topic             TEXT NOT NULL,
    subconcept        TEXT NOT NULL,
    misconception_id  TEXT NOT NULL,
    detected_at       REAL NOT NULL,
    evidence_json     TEXT NOT NULL DEFAULT '[]',
    resolved          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS attempts (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id              TEXT NOT NULL,
    student_id              TEXT NOT NULL,
    stage                   TEXT NOT NULL,
    angle_id                TEXT,
    task_id                 TEXT,
    student_response        TEXT NOT NULL,
    outcome                 TEXT NOT NULL,
    reasoning_correct       INTEGER NOT NULL DEFAULT 0,
    transfer_success        INTEGER NOT NULL DEFAULT 0,
    misconception_recurred  INTEGER NOT NULL DEFAULT 0,
    created_at              REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT,
    student_id  TEXT,
    event_type  TEXT NOT NULL,
    timestamp   REAL NOT NULL,
    data_json   TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS persistent_state (
    session_id  TEXT PRIMARY KEY,
    student_id  TEXT NOT NULL,
    state_json  TEXT NOT NULL DEFAULT '{}',
    updated_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_learning_state_student ON learning_state(student_id);
CREATE INDEX IF NOT EXISTS idx_misconceptions_student ON misconceptions(student_id, topic);
CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_persistent_state_student ON persistent_state(student_id);
"""


class TutorStore:
    """Manages all persistent student learning data in SQLite."""

    def __init__(self, db_path: str | Path = "run.db") -> None:
        self.path = Path(db_path)
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path),isolation_level=None,check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # ── Persistent Session State ─────────────────────────────────────────────

    def save_session_state(self, session_id: str, student_id: str, state_dict: dict[str, Any]) -> None:
        self.ensure_student(student_id)
        now = time.time()
        self.db.execute(
            """
            INSERT INTO persistent_state (session_id, student_id, state_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                state_json=excluded.state_json,
                updated_at=excluded.updated_at
            """,
            (session_id, student_id, json.dumps(state_dict), now),
        )

    def get_session_state(self, session_id: str) -> Optional[dict[str, Any]]:
        row = self.db.execute("SELECT state_json FROM persistent_state WHERE session_id=?", (session_id,)).fetchone()
        if row:
            return json.loads(row["state_json"])
        return None

    # ── Students ─────────────────────────────────────────────────────────────

    def ensure_student(self, student_id: str, name: Optional[str] = None) -> dict[str, Any]:
        now = time.time()
        self.db.execute(
            """
            INSERT INTO students (student_id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET updated_at=excluded.updated_at
            """,
            (student_id, name or student_id, now, now),
        )
        row = self.db.execute("SELECT * FROM students WHERE student_id=?", (student_id,)).fetchone()
        return dict(row)

    def reset_student(self, student_id: str) -> None:
        """Reset all learning state for a student."""
        self.db.execute("DELETE FROM events WHERE student_id=?", (student_id,))
        self.db.execute("DELETE FROM attempts WHERE student_id=?", (student_id,))
        self.db.execute("DELETE FROM misconceptions WHERE student_id=?", (student_id,))
        self.db.execute("DELETE FROM learning_state WHERE student_id=?", (student_id,))
        self.db.execute("DELETE FROM sessions WHERE student_id=?", (student_id,))
        self.db.execute("DELETE FROM students WHERE student_id=?", (student_id,))

    # ── Sessions ─────────────────────────────────────────────────────────────

    def create_session(self, session_id: str, student_id: str, topic: str, mode: str = "adaptive") -> None:
        self.ensure_student(student_id)
        now = time.time()
        self.db.execute(
            """
            INSERT INTO sessions (session_id, student_id, topic, mode, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)
            """,
            (session_id, student_id, topic, mode, now, now),
        )

    def update_session_status(self, session_id: str, status: str) -> None:
        self.db.execute(
            "UPDATE sessions SET status=?, updated_at=? WHERE session_id=?",
            (status, time.time(), session_id),
        )

    # ── Learning State ───────────────────────────────────────────────────────

    def get_learning_state(self, student_id: str, topic: str, subconcept: str) -> Optional[dict[str, Any]]:
        row = self.db.execute(
            """
            SELECT * FROM learning_state
            WHERE student_id=? AND topic=? AND subconcept=?
            """,
            (student_id, topic, subconcept),
        ).fetchone()
        if not row:
            return None
        res = dict(row)
        res["used_angles"] = json.loads(res["used_angles_json"])
        res["history"] = json.loads(res["history_json"])
        return res

    def get_student_topic_states(self, student_id: str, topic: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM learning_state WHERE student_id=? AND topic=?",
            (student_id, topic),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["used_angles"] = json.loads(d["used_angles_json"])
            d["history"] = json.loads(d["history_json"])
            result.append(d)
        return result

    def get_all_student_states(self, student_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM learning_state WHERE student_id=? ORDER BY last_seen DESC",
            (student_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["used_angles"] = json.loads(d["used_angles_json"])
            d["history"] = json.loads(d["history_json"])
            result.append(d)
        return result

    def save_learning_state(
        self,
        student_id: str,
        topic: str,
        subconcept: str,
        mastery_status: str,
        confidence: float,
        successful_transfer_count: int,
        failed_transfer_count: int,
        last_strategy: str = "",
        used_angles: Optional[list[str]] = None,
        history_entry: Optional[dict[str, Any]] = None,
    ) -> None:
        self.ensure_student(student_id)
        existing = self.get_learning_state(student_id, topic, subconcept)

        used_set = set(existing["used_angles"]) if existing else set()
        if used_angles:
            used_set.update(used_angles)

        hist_list = existing["history"] if existing else []
        if history_entry:
            hist_list.append(history_entry)

        now = time.time()
        self.db.execute(
            """
            INSERT INTO learning_state (
                student_id, topic, subconcept, mastery_status, confidence,
                successful_transfer_count, failed_transfer_count,
                last_seen, last_strategy, used_angles_json, history_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id, topic, subconcept) DO UPDATE SET
                mastery_status=excluded.mastery_status,
                confidence=excluded.confidence,
                successful_transfer_count=excluded.successful_transfer_count,
                failed_transfer_count=excluded.failed_transfer_count,
                last_seen=excluded.last_seen,
                last_strategy=excluded.last_strategy,
                used_angles_json=excluded.used_angles_json,
                history_json=excluded.history_json
            """,
            (
                student_id,
                topic,
                subconcept,
                mastery_status,
                confidence,
                successful_transfer_count,
                failed_transfer_count,
                now,
                last_strategy,
                json.dumps(list(used_set)),
                json.dumps(hist_list),
            ),
        )

    # ── Misconceptions ───────────────────────────────────────────────────────

    def record_misconception(
        self,
        student_id: str,
        topic: str,
        subconcept: str,
        misconception_id: str,
        evidence: list[str],
    ) -> int:
        self.ensure_student(student_id)
        cur = self.db.execute(
            """
            INSERT INTO misconceptions (student_id, topic, subconcept, misconception_id, detected_at, evidence_json, resolved)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (student_id, topic, subconcept, misconception_id, time.time(), json.dumps(evidence)),
        )
        return cur.lastrowid

    def get_student_misconceptions(
        self,
        student_id: str,
        topic: Optional[str] = None,
        resolved: Optional[bool] = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM misconceptions WHERE student_id=?"
        params: list[Any] = [student_id]
        if topic:
            query += " AND topic=?"
            params.append(topic)
        if resolved is not None:
            query += " AND resolved=?"
            params.append(1 if resolved else 0)
        query += " ORDER BY detected_at DESC"
        rows = self.db.execute(query, tuple(params)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["evidence"] = json.loads(d["evidence_json"])
            result.append(d)
        return result

    def resolve_misconceptions(self, student_id: str, topic: str, subconcept: str, misconception_id: str) -> None:
        self.db.execute(
            """
            UPDATE misconceptions SET resolved=1
            WHERE student_id=? AND topic=? AND subconcept=? AND misconception_id=?
            """,
            (student_id, topic, subconcept, misconception_id),
        )

    # ── Attempts ─────────────────────────────────────────────────────────────

    def record_attempt(
        self,
        session_id: str,
        student_id: str,
        stage: str,
        student_response: str,
        outcome: str,
        reasoning_correct: bool,
        transfer_success: bool,
        misconception_recurred: bool,
        angle_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> int:
        cur = self.db.execute(
            """
            INSERT INTO attempts (
                session_id, student_id, stage, angle_id, task_id,
                student_response, outcome, reasoning_correct,
                transfer_success, misconception_recurred, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                student_id,
                stage,
                angle_id,
                task_id,
                student_response,
                outcome,
                1 if reasoning_correct else 0,
                1 if transfer_success else 0,
                1 if misconception_recurred else 0,
                time.time(),
            ),
        )
        return cur.lastrowid

    def get_session_attempts(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM attempts WHERE session_id=? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Events ───────────────────────────────────────────────────────────────

    def record_event(
        self,
        event_type: str,
        session_id: Optional[str] = None,
        student_id: Optional[str] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> int:
        cur = self.db.execute(
            """
            INSERT INTO events (session_id, student_id, event_type, timestamp, data_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, student_id, event_type, time.time(), json.dumps(data or {})),
        )
        return cur.lastrowid

    def get_session_events(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT * FROM events WHERE session_id=? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        res = []
        for r in rows:
            d = dict(r)
            d["data"] = json.loads(d["data_json"])
            res.append(d)
        return res

    # ── JSON Session State Export & Pickup ───────────────────────────────────

    def sync_session_json_summary(self, session_id: str, json_dir: str | Path = "data/sessions") -> Path:
        """
        Saves session learning state summary to a JSON file:
        <json_dir>/<session_id>_profile.json
        Includes:
        - session_id
        - misconception_detected
        - transfer_passed (boolean)
        - socratic_rounds_count
        - history of attempts
        """
        p_dir = Path(json_dir)
        p_dir.mkdir(parents=True, exist_ok=True)
        json_file = p_dir / f"{session_id}_profile.json"

        # Query session attempts
        attempts = self.get_session_attempts(session_id)
        socratic_attempts = sum(1 for a in attempts if a.get("stage") == "socratic")
        transfer_passed = any(a.get("transfer_success") == 1 for a in attempts)

        # Query session events to get misconception / topic info
        events = self.get_session_events(session_id)
        misconceptions = []
        last_topic = "binary_search"
        last_misconception = None

        for e in events:
            data = e.get("data", {})
            if e.get("event_type") == "DIAGNOSIS_CREATED" or "misconception_id" in data:
                m_id = data.get("misconception_id")
                if m_id:
                    last_misconception = m_id
                    misconceptions.append(data)

        summary = {
            "session_id": session_id,
            "last_updated": time.time(),
            "last_topic": last_topic,
            "misconception_detected": last_misconception,
            "transfer_passed": transfer_passed,
            "socratic_rounds_count": socratic_attempts,
            "attempts": attempts,
            "events": events,
        }

        json_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return json_file

    def load_session_json_summary(self, session_id: str, json_dir: str | Path = "data/sessions") -> Optional[dict[str, Any]]:
        """Reads session summary JSON if available to pick up where it left off."""
        json_file = Path(json_dir) / f"{session_id}_profile.json"
        if not json_file.exists():
            return None
        try:
            return json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            return None


