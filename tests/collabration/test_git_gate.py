"""Git 闸门决策测试:build_hook_feedback 把 check 结果翻译成阻止反馈。"""

import pytest

from backend.collabration import git_gate, locks, queues, rooms


@pytest.fixture(autouse=True)
def reset_state():
    rooms._rooms.clear()
    rooms._participants.clear()
    locks._locks.clear()
    locks._file_holders.clear()
    queues._queues.clear()
    rooms.create_room("test")
    yield


def test_all_ok_not_blocked():
    locks.declare_intent("test", "Alice", "Claude", ["a.py"], "work")
    results = locks.check_files_locked("test", ["a.py"], "Alice")
    fb = git_gate.build_hook_feedback(results)
    assert fb.blocked is False


def test_no_lock_blocked():
    results = locks.check_files_locked("test", ["a.py"], "Alice")
    fb = git_gate.build_hook_feedback(results)
    assert fb.blocked is True
    assert "a.py" in fb.blocked_files
    assert "没有 intent lock" in fb.human_message
    assert fb.collabration_action["tool"] == "wait_for_clear"


def test_locked_by_other_blocked():
    locks.declare_intent("test", "Alice", "Claude", ["a.py"], "fix bug")
    results = locks.check_files_locked("test", ["a.py"], "Bob")
    fb = git_gate.build_hook_feedback(results)
    assert fb.blocked is True
    assert fb.holders[0]["owner"] == "Alice"
    assert "Alice" in fb.human_message
    assert fb.collabration_action["args"]["files"] == ["a.py"]


def test_mixed_only_blocked_files_reported():
    # Alice 持有 a.py(合法),b.py 无锁(违规)
    locks.declare_intent("test", "Alice", "Claude", ["a.py"], "work")
    results = locks.check_files_locked("test", ["a.py", "b.py"], "Alice")
    fb = git_gate.build_hook_feedback(results)
    assert fb.blocked is True
    assert fb.blocked_files == ["b.py"]


def test_lock_not_active_blocked():
    r = locks.declare_intent("test", "Alice", "Claude", ["a.py"], "work")
    locks.report_done(r["lock_id"])  # a.py 释放,锁变 done,a.py 变 no_lock
    # 重新声明后立刻 done 制造一个非 active 持有:改用直接构造 results
    results = [{"file": "a.py", "status": "lock_not_active", "lock_status": "done"}]
    fb = git_gate.build_hook_feedback(results)
    assert fb.blocked is True
    assert "非 active" in fb.human_message
