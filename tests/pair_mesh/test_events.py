"""事件记录测试:记录/倒序/上限裁剪。"""

import pytest

from backend.pair_mesh import events
from backend.pair_mesh.schema import EventType


@pytest.fixture(autouse=True)
def reset_state():
    events._events.clear()
    yield


def test_record_and_get_order():
    events.record("r", EventType.ROOM_CREATED, "system")
    events.record("r", EventType.INTENT_DECLARED, "Alice", {"files": ["a.py"]})
    got = events.get_events("r")
    assert len(got) == 2
    # 最新在前
    assert got[0].event_type == EventType.INTENT_DECLARED
    assert got[0].actor == "Alice"
    assert got[0].payload["files"] == ["a.py"]


def test_get_limit():
    for i in range(10):
        events.record("r", EventType.MESSAGE_SENT, "Alice", {"i": i})
    got = events.get_events("r", limit=3)
    assert len(got) == 3
    assert got[0].payload["i"] == 9  # 最新


def test_max_events_cap():
    cap = events._MAX_EVENTS
    for i in range(cap + 50):
        events.record("r", EventType.MESSAGE_SENT, "Alice", {"i": i})
    assert len(events._events["r"]) == cap
    # 最旧的应已被裁掉,最新仍在
    assert events.get_events("r", limit=1)[0].payload["i"] == cap + 49


def test_empty_room():
    assert events.get_events("ghost") == []
