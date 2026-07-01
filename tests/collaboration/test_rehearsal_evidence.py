"""M6 演练证据 bundle 测试:把 dashboard/audit/hook 数据整理成报告素材。"""

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


def test_rehearsal_evidence_bundle_suggests_report_fields(client):
    _seed_rehearsal_flow(client)

    response = client.get("/api/collaboration/rehearsal/R/evidence?limit=20")

    assert response.status_code == 200
    payload = response.json()
    evidence = payload["suggested_evidence"]

    assert payload["room_id"] == "R"
    assert payload["summary"]["participants"] == 2
    assert payload["summary"]["audit"] >= 5
    assert payload["summary"]["hook_blocks"] == 1
    assert evidence["room_setup"] == {
        "repo_remote": "git@example.com:team/repo.git",
        "branch": "feature/m6, main",
        "dashboard_url": "/api/collaboration/dashboard/R",
    }
    assert "Alice: clear" in evidence["declare_conflict_wait"]["declare_result"]
    assert "Bob: conflict" in evidence["declare_conflict_wait"]["conflict_result"]
    assert "Bob: held" in evidence["declare_conflict_wait"]["wait_result"]
    assert "declare_intent:conflict" in evidence["declare_conflict_wait"]["audit_excerpt"]
    assert "Alice: done" in evidence["report_done_handoff"]["report_done_result"]
    assert evidence["report_done_handoff"]["promoted_owner"] == "Bob"
    assert "Alice: blocked" in evidence["hook_blocked_recovery"]["hook_result"]
    assert evidence["hook_blocked_recovery"]["collaboration_action"] == "wait_for_clear"
    assert "collaborative_task_completed" in payload["manual_required"]
    assert payload["raw"]["hook_feedback"][0]["blocked_files"] == ["src/main.py"]


def test_rehearsal_evidence_unknown_room_returns_404(client):
    response = client.get("/api/collaboration/rehearsal/ghost/evidence")

    assert response.status_code == 404


def _seed_rehearsal_flow(client):
    client.post("/api/collaboration/room/create", json={
        "room_id": "R",
        "repo_remote": "git@example.com:team/repo.git",
    })
    client.post("/api/collaboration/room/join", json={
        "room_id": "R",
        "name": "Alice",
        "agent": "Claude Code",
        "branch": "main",
    })
    client.post("/api/collaboration/room/join", json={
        "room_id": "R",
        "name": "Bob",
        "agent": "Codex",
        "branch": "feature/m6",
    })
    alice = client.post("/api/collaboration/intent/declare", json={
        "room_id": "R",
        "owner": "Alice",
        "agent": "Claude Code",
        "files": ["src/main.py"],
        "intent": "fix bug",
    }).json()
    client.post("/api/collaboration/intent/declare", json={
        "room_id": "R",
        "owner": "Bob",
        "agent": "Codex",
        "files": ["src/main.py"],
        "intent": "add feature",
    })
    client.post("/api/collaboration/intent/wait_for_clear", json={
        "room_id": "R",
        "requester": "Bob",
        "files": ["src/main.py"],
    })
    client.post("/api/collaboration/intent/done", json={
        "lock_id": alice["lock_id"],
        "summary": "done",
    })
    client.post("/api/collaboration/hook/check", json={
        "room_id": "R",
        "requester": "Alice",
        "staged_files": ["src/main.py"],
    })
