"""Dashboard 端点测试:验证 M3 最小可视状态面板的数据与 HTML 输出。"""

import pytest
from fastapi.testclient import TestClient

from backend.collaboration import audit, events, locks, queues, relay, rooms
from backend.collaboration.app import app


@pytest.fixture(autouse=True)
def reset_state():
    rooms._rooms.clear()
    rooms._participants.clear()
    locks._locks.clear()
    locks._file_holders.clear()
    queues._queues.clear()
    audit._call_logs.clear()
    events._events.clear()
    relay._connections.clear()
    relay._event_streams.clear()
    relay._next_seq.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def _seed_dashboard_room(client):
    client.post("/api/collaboration/room/create", json={
        "room_id": "R",
        "repo_remote": "git@example.com:team/repo.git",
        "max_participants": 10,
    })
    client.post("/api/collaboration/room/join", json={
        "room_id": "R", "name": "Alice", "agent": "Claude Code", "branch": "main",
    })
    client.post("/api/collaboration/room/join", json={
        "room_id": "R", "name": "Bob", "agent": "Codex", "branch": "feature/m3",
    })
    client.post("/api/collaboration/room/join", json={
        "room_id": "R", "name": "Cara", "agent": "Codex", "branch": "review",
    })
    client.post("/api/collaboration/relay/connect", json={
        "room_id": "R", "relay_url": "local://memory",
    })
    client.post("/api/collaboration/intent/declare", json={
        "room_id": "R",
        "owner": "Alice",
        "agent": "Claude Code",
        "files": ["src/main.py"],
        "intent": "fix bug",
    })
    client.post("/api/collaboration/intent/declare", json={
        "room_id": "R",
        "owner": "Bob",
        "agent": "Codex",
        "files": ["src/main.py"],
        "intent": "add feature",
    })
    client.post("/api/collaboration/message", json={
        "room_id": "R",
        "sender": "Cara",
        "message": "watching queue",
    })
    client.post("/api/collaboration/hook/check", json={
        "room_id": "R",
        "requester": "Cara",
        "staged_files": ["src/main.py"],
    })


def test_dashboard_data_aggregates_room_state(client):
    _seed_dashboard_room(client)

    response = client.get("/api/collaboration/dashboard/R/data")

    assert response.status_code == 200
    payload = response.json()
    assert payload["room"]["room_id"] == "R"
    assert payload["summary"] == {
        "participants": 3,
        "active_locks": 1,
        "waiting_locks": 1,
        "queued_files": 1,
        "events": 8,
        "audit": 3,
        "hook_blocks": 1,
    }
    assert payload["relay"]["connected"] is True
    assert payload["relay"]["mode"] == "local"
    assert [p["name"] for p in payload["participants"]] == ["Alice", "Bob", "Cara"]
    assert payload["active_locks"][0]["owner"] == "Alice"
    assert payload["waiting_locks"][0]["owner"] == "Bob"
    assert payload["queues"]["src/main.py"][0]["owner"] == "Bob"
    assert payload["events"][0]["event_type"] == "hook_blocked"
    assert payload["audit"][0]["tool"] == "hook_check"
    assert payload["audit"][0]["result"] == "blocked"
    assert payload["hook_feedback"][0]["actor"] == "Cara"
    assert payload["hook_feedback"][0]["blocked_files"] == ["src/main.py"]


def test_dashboard_html_renders_core_state(client):
    _seed_dashboard_room(client)

    response = client.get("/api/collaboration/dashboard/R")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    assert "Collaboration Dashboard" in body
    assert "Room R" in body
    assert "Relay: local" in body
    assert "Alice" in body
    assert "Bob" in body
    assert "Cara" in body
    assert "src/main.py" in body
    assert "add feature" in body
    assert "Audit Log" in body
    assert "hook_check" in body
    assert "Hook Feedback" in body
    assert "blocked_files" in body


def test_dashboard_unknown_room_returns_404(client):
    data_response = client.get("/api/collaboration/dashboard/ghost/data")
    html_response = client.get("/api/collaboration/dashboard/ghost")

    assert data_response.status_code == 404
    assert html_response.status_code == 404
