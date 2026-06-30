"""Router 端点测试:走 FastAPI TestClient,验证完整 HTTP 流程。"""

import pytest
from fastapi.testclient import TestClient

from backend.pair_mesh import events, locks, queues, rooms
from backend.pair_mesh.app import app


@pytest.fixture(autouse=True)
def reset_state():
    rooms._rooms.clear()
    rooms._participants.clear()
    locks._locks.clear()
    locks._file_holders.clear()
    queues._queues.clear()
    events._events.clear()
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
    assert client.post("/api/pair-mesh/room/create", json={"room_id": "R"}).json()["status"] == "created"
    client.post("/api/pair-mesh/room/join", json={"room_id": "R", "name": "Alice", "agent": "Claude Code"})
    client.post("/api/pair-mesh/room/join", json={"room_id": "R", "name": "Bob", "agent": "Codex"})

    # Alice 声明 -> clear
    d1 = client.post("/api/pair-mesh/intent/declare", json={
        "room_id": "R", "owner": "Alice", "agent": "Claude Code",
        "files": ["src/main.py"], "intent": "fix bug",
    }).json()
    assert d1["status"] == "clear"

    # Bob 声明同文件 -> conflict
    d2 = client.post("/api/pair-mesh/intent/declare", json={
        "room_id": "R", "owner": "Bob", "agent": "Codex",
        "files": ["src/main.py"], "intent": "feature",
    }).json()
    assert d2["status"] == "conflict"

    # 状态查询:active_locks 有 Alice,queue 有 Bob
    st = client.get("/api/pair-mesh/status/R").json()
    assert len(st["active_locks"]) == 1
    assert st["active_locks"][0]["owner"] == "Alice"
    assert st["active_locks"][0]["status"] == "active"  # Enum 已序列化成字符串
    assert "src/main.py" in st["queues"]

    # wait_for_clear:Bob 等的文件仍被 Alice 占
    w = client.post("/api/pair-mesh/intent/wait_for_clear", json={
        "room_id": "R", "files": ["src/main.py"],
    }).json()
    assert w["all_clear"] is False
    assert w["files"][0]["holder"] == "Alice"

    # Alice 完成 -> Bob 上位
    done = client.post("/api/pair-mesh/intent/done", json={
        "lock_id": d1["lock_id"], "summary": "done",
    }).json()
    assert done["promoted"][0]["owner"] == "Bob"

    # hook/check:Bob 现在合法持有
    hc = client.post("/api/pair-mesh/hook/check", json={
        "room_id": "R", "requester": "Bob", "staged_files": ["src/main.py"],
    }).json()
    assert hc["blocked"] is False

    # hook/check:Alice 已无锁 -> 阻止
    hc2 = client.post("/api/pair-mesh/hook/check", json={
        "room_id": "R", "requester": "Alice", "staged_files": ["src/main.py"],
    }).json()
    assert hc2["blocked"] is True
    assert "PAIR_MESH_ACTION" in hc2

    # 事件流非空
    ev = client.get("/api/pair-mesh/events/R").json()
    assert len(ev["events"]) > 0


def test_status_404(client):
    assert client.get("/api/pair-mesh/status/ghost").status_code == 404


def test_extend_via_api(client):
    client.post("/api/pair-mesh/room/create", json={"room_id": "R"})
    d = client.post("/api/pair-mesh/intent/declare", json={
        "room_id": "R", "owner": "Alice", "files": ["a.py"], "intent": "x",
    }).json()
    ext = client.post("/api/pair-mesh/intent/extend", json={
        "lock_id": d["lock_id"], "additional_files": ["b.py"], "reason": "more",
    }).json()
    assert ext["status"] == "extended"
    assert "b.py" in ext["files"]
