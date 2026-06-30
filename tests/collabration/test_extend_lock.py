"""extend_lock 专项测试:扩展成功 / 部分冲突 / 重复文件 / 版本号递增。"""

import pytest

from backend.collabration import locks, queues, rooms


@pytest.fixture(autouse=True)
def reset_state():
    rooms._rooms.clear()
    rooms._participants.clear()
    locks._locks.clear()
    locks._file_holders.clear()
    queues._queues.clear()
    rooms.create_room("test")
    yield


def test_extend_adds_files_and_bumps_version():
    r = locks.declare_intent("test", "Alice", "Claude", ["a.py"], "work")
    v0 = locks.get_lock(r["lock_id"]).lock_version
    ext = locks.extend_lock(r["lock_id"], ["b.py", "c.py"], "more")
    assert ext["status"] == "extended"
    assert set(ext["files"]) == {"a.py", "b.py", "c.py"}
    assert locks.get_lock(r["lock_id"]).lock_version == v0 + 1
    assert locks.get_file_holder("test", "b.py").owner == "Alice"


def test_extend_duplicate_file_no_double_add():
    r = locks.declare_intent("test", "Alice", "Claude", ["a.py"], "work")
    locks.extend_lock(r["lock_id"], ["a.py"])  # 已持有的文件
    assert locks.get_lock(r["lock_id"]).files.count("a.py") == 1


def test_extend_partial_conflict_keeps_clean_files():
    locks.declare_intent("test", "Bob", "Codex", ["x.py"], "bob work")
    r = locks.declare_intent("test", "Alice", "Claude", ["a.py"], "alice work")
    ext = locks.extend_lock(r["lock_id"], ["b.py", "x.py"])  # x.py 被 Bob 占
    assert ext["status"] == "partial_conflict"
    assert "b.py" in ext["extended_files"]
    assert ext["conflict_files"][0]["file"] == "x.py"
    # b.py 应已被 Alice 持有,x.py 仍属 Bob
    assert locks.get_file_holder("test", "b.py").owner == "Alice"
    assert locks.get_file_holder("test", "x.py").owner == "Bob"


def test_extend_unknown_lock():
    assert locks.extend_lock("nope", ["a.py"])["status"] == "error"
