"""MCP/API 调用日志测试:记录真实 agent 协作动作,支撑 M5 prompt 层验收。"""

import pytest
import json
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
    events._events.clear()
    relay._connections.clear()
    relay._event_streams.clear()
    relay._next_seq.clear()
    if hasattr(audit, "_call_logs"):
        audit._call_logs.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_record_call_log_and_get_latest_order():
    audit.record_call(
        room_id="R",
        actor="Alice",
        agent="Codex",
        tool="declare_intent",
        result="clear",
        files=["src/main.py"],
        payload={"intent": "fix bug"},
    )
    audit.record_call(
        room_id="R",
        actor="Alice",
        agent="Codex",
        tool="report_done",
        result="done",
        files=["src/main.py"],
        payload={"summary": "fixed"},
    )

    got = audit.get_call_logs("R")

    assert [item.tool for item in got] == ["report_done", "declare_intent"]
    assert got[0].result == "done"
    assert got[1].payload["intent"] == "fix bug"


def test_export_call_logs_as_jsonl_oldest_first():
    audit.record_call(
        room_id="R",
        actor="Alice",
        agent="Codex",
        tool="declare_intent",
        result="clear",
        files=["src/main.py"],
    )
    audit.record_call(
        room_id="R",
        actor="Bob",
        agent="Claude Code",
        tool="hook_check",
        result="blocked",
        files=["src/main.py"],
        payload={"action": {"tool": "wait_for_clear"}},
    )

    lines = audit.export_calls("R", fmt="jsonl").splitlines()

    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["actor"] == "Alice"
    assert first["tool"] == "declare_intent"
    assert second["actor"] == "Bob"
    assert second["payload"]["action"]["tool"] == "wait_for_clear"


def test_export_call_logs_rejects_unknown_format():
    with pytest.raises(ValueError, match="only jsonl"):
        audit.export_calls("R", fmt="csv")


def test_router_records_intent_and_report_done_calls(client):
    client.post("/api/collaboration/room/create", json={"room_id": "R"})
    first = client.post("/api/collaboration/intent/declare", json={
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
        "intent": "feature",
    })
    client.post("/api/collaboration/intent/done", json={
        "lock_id": first["lock_id"],
        "summary": "done",
    })

    logs = client.get("/api/collaboration/audit/R?limit=10").json()["audit"]

    assert [item["tool"] for item in logs] == [
        "report_done",
        "declare_intent",
        "declare_intent",
    ]
    assert logs[0]["actor"] == "Alice"
    assert logs[0]["result"] == "done"
    assert logs[1]["actor"] == "Bob"
    assert logs[1]["result"] == "conflict"
    assert logs[1]["files"] == ["src/main.py"]


def test_router_exports_audit_log_as_jsonl(client):
    client.post("/api/collaboration/room/create", json={"room_id": "R"})
    client.post("/api/collaboration/intent/declare", json={
        "room_id": "R",
        "owner": "Alice",
        "agent": "Codex",
        "files": ["src/main.py"],
        "intent": "fix bug",
    })

    response = client.get("/api/collaboration/audit/R/export?fmt=jsonl")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    lines = response.text.strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["actor"] == "Alice"
    assert payload["tool"] == "declare_intent"
    assert payload["files"] == ["src/main.py"]


def test_router_rejects_unknown_audit_export_format(client):
    response = client.get("/api/collaboration/audit/R/export?fmt=csv")

    assert response.status_code == 400
