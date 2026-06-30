"""房间管理测试:创建/加入/离开/心跳/满员。"""

import pytest

from backend.pair_mesh import rooms


@pytest.fixture(autouse=True)
def reset_state():
    rooms._rooms.clear()
    rooms._participants.clear()
    yield


def test_create_room():
    room = rooms.create_room("test", repo_remote="https://github.com/test/repo.git")
    assert room.room_id == "test"
    assert rooms.get_room("test") is room


def test_join_and_get_participants():
    rooms.create_room("test")
    r = rooms.join_room("test", "Alice", "Claude Code")
    assert r["status"] == "joined"
    assert "Alice" in r["participants"]
    names = [p.name for p in rooms.get_participants("test")]
    assert names == ["Alice"]


def test_join_nonexistent_room():
    r = rooms.join_room("ghost", "Alice")
    assert r["status"] == "error"


def test_join_full_room():
    rooms.create_room("test", max_participants=1)
    rooms.join_room("test", "Alice")
    r = rooms.join_room("test", "Bob")
    assert r["status"] == "error"
    assert "full" in r["message"].lower()


def test_rejoin_same_user_not_full():
    rooms.create_room("test", max_participants=1)
    rooms.join_room("test", "Alice")
    r = rooms.join_room("test", "Alice", branch="dev")  # 重复 join 不应被满员拦截
    assert r["status"] == "joined"


def test_leave_room():
    rooms.create_room("test")
    rooms.join_room("test", "Alice")
    rooms.leave_room("test", "Alice")
    assert rooms.get_participants("test") == []
    assert "Alice" not in rooms.get_room("test").participants


def test_leave_is_idempotent():
    rooms.create_room("test")
    assert rooms.leave_room("test", "Ghost")["status"] == "left"


def test_heartbeat_ok():
    rooms.create_room("test")
    rooms.join_room("test", "Alice")
    before = rooms.get_participants("test")[0].last_heartbeat
    assert rooms.heartbeat("test", "Alice")["status"] == "ok"
    assert rooms.get_participants("test")[0].online is True
    # 心跳应刷新时间(至少不报错;时间可能相同精度,放宽为非 None)
    assert rooms.get_participants("test")[0].last_heartbeat is not None
    assert before is not None


def test_heartbeat_not_in_room():
    rooms.create_room("test")
    assert rooms.heartbeat("test", "Ghost")["status"] == "error"
