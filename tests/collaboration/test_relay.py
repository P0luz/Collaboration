"""Relay 测试:本地事件流与状态快照,为 M3 多机同步打底。"""

from __future__ import annotations

import pytest

from backend.collaboration import events, locks, queues, relay, rooms
from backend.collaboration.schema import EventType


@pytest.fixture(autouse=True)
def reset_state():
    rooms._rooms.clear()
    rooms._participants.clear()
    locks._locks.clear()
    locks._file_holders.clear()
    queues._queues.clear()
    events._events.clear()
    if hasattr(relay, "_connections"):
        relay._connections.clear()
    if hasattr(relay, "_event_streams"):
        relay._event_streams.clear()
    if hasattr(relay, "_next_seq"):
        relay._next_seq.clear()
    rooms.create_room("test", repo_remote="https://github.com/test/repo.git")
    rooms.join_room("test", "Alice", "Claude Code")
    rooms.join_room("test", "Bob", "Codex")
    yield


def test_connect_and_event_record_publish_to_relay_stream():
    connected = relay.connect("local://memory", "test")

    recorded = events.record("test", EventType.INTENT_DECLARED, "Alice", {"files": ["a.py"]})
    stream = relay.subscribe("test")

    assert connected["status"] == "connected"
    assert stream["last_seq"] == 1
    assert stream["events"] == [{
        "seq": 1,
        "room_id": "test",
        "event": {
            "event_id": recorded.event_id,
            "type": "intent_declared",
            "actor": "Alice",
            "payload": {"files": ["a.py"]},
            "created_at": recorded.created_at,
        },
    }]


def test_subscribe_since_returns_only_newer_events():
    relay.connect("local://memory", "test")
    events.record("test", EventType.ROOM_CREATED, "system")
    events.record("test", EventType.MESSAGE_SENT, "Alice", {"message": "hi"})

    stream = relay.subscribe("test", since=1)

    assert stream["last_seq"] == 2
    assert len(stream["events"]) == 1
    assert stream["events"][0]["seq"] == 2
    assert stream["events"][0]["event"]["type"] == "message_sent"


def test_snapshot_contains_room_participants_locks_and_queues():
    relay.connect("local://memory", "test")
    locks.declare_intent("test", "Alice", "Claude Code", ["src/main.py"], "fix bug")
    locks.declare_intent("test", "Bob", "Codex", ["src/main.py"], "add feature")

    snapshot = relay.snapshot("test")

    assert snapshot["room"]["room_id"] == "test"
    assert [p["name"] for p in snapshot["participants"]] == ["Alice", "Bob"]
    assert snapshot["active_locks"][0]["owner"] == "Alice"
    assert snapshot["waiting_locks"][0]["owner"] == "Bob"
    assert snapshot["queues"]["src/main.py"][0]["owner"] == "Bob"

