"""RelayClient 测试:通过 HTTP relay API 维护 snapshot 和 last_seq。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.collaboration import events, locks, queues, relay, rooms
from backend.collaboration.app import app
from backend.collaboration.relay_client import RelayClient


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
def http_client():
    return TestClient(app)


def test_relay_client_connect_sync_publish_and_poll(http_client):
    http_client.post("/api/collaboration/room/create", json={"room_id": "R"})
    http_client.post("/api/collaboration/room/join", json={
        "room_id": "R", "name": "Alice", "agent": "Codex",
    })
    client = RelayClient(http_client=http_client)

    connected = client.connect("R")
    synced = client.sync("R")
    assert connected["status"] == "connected"
    assert synced.snapshot["room"]["room_id"] == "R"
    assert synced.snapshot["participants"][0]["name"] == "Alice"
    assert client.last_seq("R") == 0

    published = client.publish("R", {
        "event_id": "remote_evt_1",
        "type": "participant_heartbeat",
        "actor": "Alice",
        "payload": {"branch": "main"},
        "created_at": "2026-07-01T00:00:00+00:00",
    })
    first_poll = client.poll_events("R")
    second_poll = client.poll_events("R")

    assert published == {"status": "published", "room_id": "R", "seq": 1}
    assert [item["event"]["event_id"] for item in first_poll.events] == ["remote_evt_1"]
    assert first_poll.last_seq == 1
    assert client.last_seq("R") == 1
    assert second_poll.events == []
    assert second_poll.last_seq == 1


def test_relay_client_disconnect_keeps_local_cursor(http_client):
    http_client.post("/api/collaboration/room/create", json={"room_id": "R"})
    client = RelayClient(http_client=http_client)
    client.connect("R")
    client.publish("R", {
        "event_id": "remote_evt_1",
        "type": "message_sent",
        "actor": "Alice",
        "payload": {"message": "hi"},
        "created_at": "2026-07-01T00:00:00+00:00",
    })
    client.poll_events("R")

    disconnected = client.disconnect("R")

    assert disconnected == {"status": "disconnected", "room_id": "R"}
    assert client.last_seq("R") == 1
