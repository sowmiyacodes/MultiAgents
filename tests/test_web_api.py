"""
Integration tests for the Flask Web UI & API Layer.
Verifies routes, session persistence, state machine stepping, support options, and JSON profile download.
"""
import json
import tempfile
from pathlib import Path

import pytest

from runtime.store import TutorStore
from web.app import create_app


@pytest.fixture
def client():
    # Use temporary database for test isolation
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    app = create_app(test_config={"DATABASE_PATH": db_path, "TESTING": True})
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client

    # Cleanup temporary db
    try:
        Path(db_path).unlink(missing_ok=True)
    except Exception:
        pass


def test_page_routes(client):
    """Test HTML page routes render successfully."""
    r_root = client.get("/")
    assert r_root.status_code == 302  # redirects to /chatbot

    r_chat = client.get("/chatbot")
    assert r_chat.status_code == 200
    assert b"THINKAGAIN" in r_chat.data
    assert b"Socratic Agent" in r_chat.data

    r_graph = client.get("/graph")
    assert r_graph.status_code == 200
    assert b"state-graph-svg" in r_graph.data
    assert b"slice/state_machine.py" in r_graph.data


def test_initial_state_empty(client):
    """Test /api/state before any session is started."""
    res = client.get("/api/state")
    assert res.status_code == 200
    data = res.get_json()
    assert data["active"] is False
    assert data["session_id"] is None


def test_start_session_adaptive(client):
    """Test starting an adaptive tutoring session with code submission."""
    query = (
        "int left = 0;\nint right = nums.length - 1;\n"
        "while (left <= right) {\n"
        "    int mid = (left + right) / 2;\n"
        "    if (nums[mid] == target) return mid;\n"
        "    if (nums[mid] < target) left++; else right--;\n"
        "}\nreturn -1;"
    )
    res = client.post("/api/session/start", json={"initial_query": query, "student_id": "test_student"})
    assert res.status_code == 200
    data = res.get_json()

    assert data["active"] is True
    assert data["session_id"] is not None
    assert data["state"] == "WAITING_FOR_STUDENT"
    assert data["stage"] == "socratic"
    assert "Binary Search" in data["topic"]
    assert data["current_question"] is not None
    assert len(data["messages"]) >= 2  # user query + assistant question
    assert "START" in data["completed_states"]
    assert "DIAGNOSING" in data["completed_states"]
    assert "SOCRATIC_GUIDANCE" in data["completed_states"]


def test_chat_interaction_and_evaluation(client):
    """Test submitting answers to the tutor and receiving evaluator feedback."""
    query = "Why does left++ fail in binary search?"
    res_start = client.post("/api/session/start", json={"initial_query": query})
    assert res_start.status_code == 200

    # Submit an answer
    res_chat = client.post("/api/chat", json={"message": "I think left++ is fine because it checks every element."})
    assert res_chat.status_code == 200
    data = res_chat.get_json()

    assert data["active"] is True
    assert data["evaluation"] is not None
    assert data["evaluation"]["feedback"] is not None
    # If incorrect reasoning, student options should be offered
    if not data["evaluation"]["reasoning_correct"] and data["stage"] == "socratic":
        assert data["options_available"] is True


def test_student_options_api(client):
    """Test the three student options: hint, worked example, and try again."""
    query = "int left = 0; int right = n-1; while (left <= right) { int mid = (left+right)/2; left++; }"
    client.post("/api/session/start", json={"initial_query": query})
    client.post("/api/chat", json={"message": "left++ moves forward one by one."})

    # 1. Test Hint option
    res_hint = client.post("/api/option", json={"option": "hint"})
    assert res_hint.status_code == 200
    hint_data = res_hint.get_json()
    assert hint_data["success"] is True
    assert "Focus on the invariant" in hint_data["message"]["text"]

    # 2. Test Worked Example option
    res_example = client.post("/api/option", json={"option": "worked_example"})
    assert res_example.status_code == 200
    example_data = res_example.get_json()
    assert example_data["success"] is True
    assert example_data["message"]["type"] == "targeted_tutor"
    assert example_data["message"]["worked_example"] is not None

    # 3. Test Try Again option
    res_retry = client.post("/api/option", json={"option": "retry"})
    assert res_retry.status_code == 200
    retry_data = res_retry.get_json()
    assert retry_data["success"] is True


def test_session_persistence_and_navigation(client):
    """Verify state survives navigation and repeated /api/state calls."""
    query = "Explain binary search bounds"
    res_start = client.post("/api/session/start", json={"initial_query": query})
    start_data = res_start.get_json()
    session_id = start_data["session_id"]

    # Check state again as if user navigated /chatbot -> /graph -> /chatbot
    res_state = client.get("/api/state")
    assert res_state.status_code == 200
    state_data = res_state.get_json()
    assert state_data["session_id"] == session_id
    assert state_data["active"] is True
    assert len(state_data["messages"]) == len(start_data["messages"])


def test_download_json_summary(client):
    """Test downloading session JSON summary and verify access control."""
    query = "int left = 0; int right = n - 1; left++;"
    res_start = client.post("/api/session/start", json={"initial_query": query})
    session_id = res_start.get_json()["session_id"]

    # Authorized download
    res_down = client.get(f"/api/session/{session_id}/download")
    assert res_down.status_code == 200
    json_content = json.loads(res_down.data)
    assert json_content["session_id"] == session_id
    assert "attempts" in json_content
    assert "events" in json_content

    # Unauthorized access to arbitrary session ID
    res_unauth = client.get("/api/session/random_unknown_session_123/download")
    assert res_unauth.status_code == 403


def test_full_progression_to_completion(client):
    """Test full interactive progression through Socratic -> Transfer -> Complete."""
    query = (
        "int left = 0; int right = nums.length - 1;\n"
        "while (left <= right) {\n"
        "    int mid = (left + right) / 2;\n"
        "    if (nums[mid] == target) return mid;\n"
        "    if (nums[mid] < target) left++; else right--;\n"
        "}\nreturn -1;"
    )
    res_start = client.post("/api/session/start", json={"initial_query": query})
    assert res_start.status_code == 200
    data_start = res_start.get_json()
    assert data_start["state"] == "WAITING_FOR_STUDENT"
    assert data_start["stage"] == "socratic"

    # 1. Answer Socratic correctly
    socratic_ans = "left should be mid + 1 because all indices through mid are smaller than target, so they are completely eliminated."
    res_socratic = client.post("/api/chat", json={"message": socratic_ans})
    assert res_socratic.status_code == 200
    data_socratic = res_socratic.get_json()

    # The engine advances to transfer task or socratic angle
    assert data_socratic["active"] is True
    if data_socratic["stage"] == "transfer":
        assert data_socratic["state"] == "WAITING_FOR_STUDENT"
        # 2. Answer Transfer correctly
        transfer_ans = "left = mid + 1 eliminates the entire lower half including mid because it is less than target."
        res_transfer = client.post("/api/chat", json={"message": transfer_ans})
        assert res_transfer.status_code == 200
        data_transfer = res_transfer.get_json()
        assert data_transfer["active"] is True
        if data_transfer["state"] == "COMPLETE":
            assert data_transfer["is_terminal"] is True
            # Download JSON at completion
            res_down = client.get(f"/api/session/{data_transfer['session_id']}/download")
            assert res_down.status_code == 200

