"""Intent Lock 核心测试:声明/冲突/完成/提升/扩展/hook 检查。"""

import pytest

from backend.collabration import locks, queues, rooms


@pytest.fixture(autouse=True)
def reset_state():
    """每个测试前重置全部内存状态。"""
    rooms._rooms.clear()
    rooms._participants.clear()
    locks._locks.clear()
    locks._file_holders.clear()
    queues._queues.clear()
    rooms.create_room("test", repo_remote="https://github.com/test/repo.git")
    rooms.join_room("test", "Alice", "Claude Code")
    rooms.join_room("test", "Bob", "Codex")
    yield


def test_declare_intent_clear():
    result = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    assert result["status"] == "clear"
    assert result["lock_id"]


def test_declare_intent_conflict():
    locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    result = locks.declare_intent("test", "Bob", "Codex", ["src/main.py"], "add feature")
    assert result["status"] == "conflict"
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["holder"]["owner"] == "Alice"


def test_report_done_promotes_queue():
    r1 = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    r2 = locks.declare_intent("test", "Bob", "Codex", ["src/main.py"], "add feature")
    assert r2["status"] == "conflict"

    done = locks.report_done(r1["lock_id"], "fixed the bug")
    assert done["status"] == "done"
    assert len(done["promoted"]) == 1
    assert done["promoted"][0]["owner"] == "Bob"

    # 提升后 Bob 的锁应变为 active 并持有该文件
    bob_lock = locks.get_lock(r2["lock_id"])
    assert bob_lock.status.value == "active"
    assert locks.get_file_holder("test", "src/main.py").owner == "Bob"


def test_extend_lock_no_conflict():
    r = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    ext = locks.extend_lock(r["lock_id"], ["src/utils.py"], "need utils too")
    assert ext["status"] == "extended"
    assert "src/utils.py" in ext["files"]


def test_extend_lock_partial_conflict():
    # Alice 占 main.py;Bob 拿到一个 active 锁(other.py),再尝试扩展到 Alice 的 main.py
    locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    rb = locks.declare_intent("test", "Bob", "Codex", ["src/other.py"], "other work")
    assert rb["status"] == "clear"

    ext = locks.extend_lock(rb["lock_id"], ["src/main.py"])
    assert ext["status"] == "partial_conflict"
    assert ext["conflict_files"][0]["file"] == "src/main.py"
    assert "src/main.py" not in ext["extended_files"]


def test_extend_lock_requires_active():
    r = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    locks.report_done(r["lock_id"])  # 锁变 done
    ext = locks.extend_lock(r["lock_id"], ["src/x.py"])
    assert ext["status"] == "error"


def test_different_files_no_conflict():
    r1 = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    r2 = locks.declare_intent("test", "Bob", "Codex", ["src/utils.py"], "add feature")
    assert r1["status"] == "clear"
    assert r2["status"] == "clear"


def test_same_user_same_file_no_conflict():
    r1 = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    assert r1["status"] == "clear"
    r2 = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "continue fix")
    assert r2["status"] == "clear"  # 不应跟自己冲突


def test_expire_stale_lock_releases_file():
    from datetime import datetime, timedelta, timezone

    r = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    lock = locks.get_lock(r["lock_id"])
    lock.idle_timeout_seconds = 60
    # 把最后活动时间挪到 2 分钟前,确保超过 60s 阈值
    lock.last_activity = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    # 触发过期:Bob 再声明同文件应直接 clear(Alice 锁已过期)
    rb = locks.declare_intent("test", "Bob", "Codex", ["src/main.py"], "take over")
    assert rb["status"] == "clear"
    assert lock.status.value == "expired"


def test_hook_check_no_lock():
    results = locks.check_files_locked("test", ["src/main.py"], "Alice")
    assert results[0]["status"] == "no_lock"


def test_hook_check_locked_by_other():
    locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    results = locks.check_files_locked("test", ["src/main.py"], "Bob")
    assert results[0]["status"] == "locked_by_other"


def test_hook_check_own_lock():
    locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    results = locks.check_files_locked("test", ["src/main.py"], "Alice")
    assert results[0]["status"] == "ok"
