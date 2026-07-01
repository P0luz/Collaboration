"""Watcher 测试:扫描 Git 工作区,刷新合法锁活动并记录未声明改动。"""

from __future__ import annotations

import subprocess

import pytest

from backend.collaboration import events, locks, queues, rooms, watcher
from backend.collaboration.schema import EventType


@pytest.fixture(autouse=True)
def reset_state():
    rooms._rooms.clear()
    rooms._participants.clear()
    locks._locks.clear()
    locks._file_holders.clear()
    queues._queues.clear()
    events._events.clear()
    if hasattr(watcher, "_watchers"):
        watcher._watchers.clear()
    if hasattr(watcher, "_reported_unclaimed"):
        watcher._reported_unclaimed.clear()
    rooms.create_room("test", repo_remote="https://github.com/test/repo.git")
    rooms.join_room("test", "Alice", "Claude Code")
    yield
    if hasattr(watcher, "_watchers"):
        for room_id in list(watcher._watchers):
            watcher.stop_watcher(room_id)


def init_repo(tmp_path):
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return tmp_path


def write_file(repo, relative_path: str, content: str = "x") -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_scan_once_touches_active_lock(tmp_path):
    repo = init_repo(tmp_path)
    write_file(repo, "src/main.py")
    result = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    lock = locks.get_lock(result["lock_id"])
    lock.last_activity = "2000-01-01T00:00:00+00:00"

    summary = watcher.scan_once("test", str(repo))

    assert summary["changed_files"] == ["src/main.py"]
    assert summary["touched_locks"] == [{"file": "src/main.py", "lock_id": result["lock_id"]}]
    assert summary["unclaimed_changes"] == []
    assert lock.last_activity != "2000-01-01T00:00:00+00:00"
    assert events.get_events("test") == []


def test_scan_once_records_unclaimed_change_once(tmp_path):
    repo = init_repo(tmp_path)
    write_file(repo, "src/unclaimed.py")

    first = watcher.scan_once("test", str(repo))
    second = watcher.scan_once("test", str(repo))

    assert first["unclaimed_changes"] == ["src/unclaimed.py"]
    assert second["unclaimed_changes"] == []
    got = events.get_events("test")
    assert len(got) == 1
    assert got[0].event_type == EventType.UNCLAIMED_CHANGE
    assert got[0].actor == "watcher"
    assert got[0].payload == {"file": "src/unclaimed.py", "reason": "no_active_lock"}


def test_scan_once_records_change_inside_other_holder_lock(tmp_path):
    repo = init_repo(tmp_path)
    write_file(repo, "src/main.py")
    result = locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    lock = locks.get_lock(result["lock_id"])
    lock.last_activity = "2000-01-01T00:00:00+00:00"

    summary = watcher.scan_once("test", str(repo), actor="Bob")

    assert summary["touched_locks"] == []
    assert summary["unclaimed_changes"] == ["src/main.py"]
    assert lock.last_activity == "2000-01-01T00:00:00+00:00"
    got = events.get_events("test")
    assert len(got) == 1
    assert got[0].event_type == EventType.UNCLAIMED_CHANGE
    assert got[0].actor == "Bob"
    assert got[0].payload == {
        "file": "src/main.py",
        "reason": "locked_by_other",
        "holder": "Alice",
        "agent": "Claude Code",
        "intent": "fix bug",
    }
