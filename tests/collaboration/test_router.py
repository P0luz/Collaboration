"""Router 端点测试:走 FastAPI TestClient,验证完整 HTTP 流程。"""

import pytest
from fastapi.testclient import TestClient

from backend.collaboration import events, locks, queues, relay, rooms
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
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_full_flow(client):
    # 建房 + 两人加入
    assert client.post("/api/collaboration/room/create", json={"room_id": "R"}).json()["status"] == "created"
    client.post("/api/collaboration/room/join", json={"room_id": "R", "name": "Alice", "agent": "Claude Code"})
    client.post("/api/collaboration/room/join", json={"room_id": "R", "name": "Bob", "agent": "Codex"})

    # Alice 声明 -> clear
    d1 = client.post("/api/collaboration/intent/declare", json={
        "room_id": "R", "owner": "Alice", "agent": "Claude Code",
        "files": ["src/main.py"], "intent": "fix bug",
    }).json()
    assert d1["status"] == "clear"

    # Bob 声明同文件 -> conflict
    d2 = client.post("/api/collaboration/intent/declare", json={
        "room_id": "R", "owner": "Bob", "agent": "Codex",
        "files": ["src/main.py"], "intent": "feature",
    }).json()
    assert d2["status"] == "conflict"

    # 状态查询:active_locks 有 Alice,queue 有 Bob
    st = client.get("/api/collaboration/status/R").json()
    assert len(st["active_locks"]) == 1
    assert st["active_locks"][0]["owner"] == "Alice"
    assert st["active_locks"][0]["status"] == "active"  # Enum 已序列化成字符串
    assert len(st["waiting_locks"]) == 1
    assert st["waiting_locks"][0]["owner"] == "Bob"
    assert st["waiting_locks"][0]["status"] == "waiting"
    assert "src/main.py" in st["queues"]

    # wait_for_clear:Bob 等的文件仍被 Alice 占
    w = client.post("/api/collaboration/intent/wait_for_clear", json={
        "room_id": "R", "files": ["src/main.py"],
    }).json()
    assert w["all_clear"] is False
    assert w["files"][0]["holder"] == "Alice"

    # Alice 完成 -> Bob 上位
    done = client.post("/api/collaboration/intent/done", json={
        "lock_id": d1["lock_id"], "summary": "done",
    }).json()
    assert done["promoted"][0]["owner"] == "Bob"

    # hook/check:Bob 现在合法持有
    hc = client.post("/api/collaboration/hook/check", json={
        "room_id": "R", "requester": "Bob", "staged_files": ["src/main.py"],
    }).json()
    assert hc["blocked"] is False

    # hook/check:Alice 已无锁 -> 阻止
    hc2 = client.post("/api/collaboration/hook/check", json={
        "room_id": "R", "requester": "Alice", "staged_files": ["src/main.py"],
    }).json()
    assert hc2["blocked"] is True
    assert "COLLABORATION_ACTION" in hc2

    # 事件流非空
    ev = client.get("/api/collaboration/events/R").json()
    assert len(ev["events"]) > 0


def test_status_404(client):
    assert client.get("/api/collaboration/status/ghost").status_code == 404


def test_extend_via_api(client):
    client.post("/api/collaboration/room/create", json={"room_id": "R"})
    d = client.post("/api/collaboration/intent/declare", json={
        "room_id": "R", "owner": "Alice", "files": ["a.py"], "intent": "x",
    }).json()
    ext = client.post("/api/collaboration/intent/extend", json={
        "lock_id": d["lock_id"], "additional_files": ["b.py"], "reason": "more",
    }).json()
    assert ext["status"] == "extended"
    assert "b.py" in ext["files"]


def test_relay_http_flow(client):
    client.post("/api/collaboration/room/create", json={"room_id": "R"})
    client.post("/api/collaboration/room/join", json={
        "room_id": "R", "name": "Alice", "agent": "Codex",
    })

    connected = client.post("/api/collaboration/relay/connect", json={
        "room_id": "R", "relay_url": "local://memory",
    }).json()
    assert connected["status"] == "connected"
    assert connected["mode"] == "local"

    client.post("/api/collaboration/message", json={
        "room_id": "R", "sender": "Alice", "message": "hello",
    })
    stream = client.get("/api/collaboration/relay/events/R?since=0").json()
    assert stream["last_seq"] == 1
    assert stream["events"][0]["event"]["type"] == "message_sent"
    assert stream["events"][0]["event"]["payload"] == {"message": "hello"}

    snapshot = client.get("/api/collaboration/relay/snapshot/R").json()
    assert snapshot["room"]["room_id"] == "R"
    assert snapshot["participants"][0]["name"] == "Alice"

    disconnected = client.post("/api/collaboration/relay/disconnect", json={"room_id": "R"}).json()
    assert disconnected == {"status": "disconnected", "room_id": "R"}


def test_relay_http_publish_accepts_remote_event(client):
    client.post("/api/collaboration/room/create", json={"room_id": "R"})
    client.post("/api/collaboration/relay/connect", json={
        "room_id": "R", "relay_url": "local://memory",
    })

    published = client.post("/api/collaboration/relay/publish", json={
        "room_id": "R",
        "event": {
            "event_id": "remote_evt_1",
            "type": "participant_heartbeat",
            "actor": "Bob",
            "payload": {"branch": "feature/m3"},
            "created_at": "2026-07-01T00:00:00+00:00",
        },
    }).json()
    stream = client.get("/api/collaboration/relay/events/R").json()

    assert published == {"status": "published", "room_id": "R", "seq": 1}
    assert stream["events"][0]["event"]["event_id"] == "remote_evt_1"
    assert stream["events"][0]["event"]["type"] == "participant_heartbeat"
    assert stream["events"][0]["event"]["payload"] == {"branch": "feature/m3"}
