"""Room capabilities endpoint tests for M7 readiness metadata."""

import pytest
from fastapi.testclient import TestClient

from backend.collaboration import audit, events, locks, queues, relay, rooms
from backend.collaboration.app import app


@pytest.fixture(autouse=True)
def reset_state():
    rooms._rooms.clear()
    rooms._participants.clear()
    locks._locks.clear()
    locks._file_holders.clear()
    queues._queues.clear()
    events._events.clear()
    audit._call_logs.clear()
    relay._connections.clear()
    relay._event_streams.clear()
    relay._next_seq.clear()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def test_capabilities_endpoint_returns_policy_relay_and_feature_metadata(client):
    client.post("/api/collaboration/room/create", json={
        "room_id": "R",
        "plan": "enterprise",
        "relay_mode": "self_hosted",
        "audit_retention_days": 120,
    })
    client.post("/api/collaboration/relay/connect", json={
        "room_id": "R",
        "relay_url": "https://relay.example.test/R",
    })

    response = client.get("/api/collaboration/capabilities/R")

    assert response.status_code == 200
    data = response.json()
    assert data["room_id"] == "R"
    assert data["policy"] == {
        "plan": "enterprise",
        "max_participants": 50,
        "relay_mode": "self_hosted",
        "audit_retention_days": 120,
        "policy_rules_enabled": True,
    }
    assert data["relay"] == {
        "mode": "self_hosted",
        "connected": True,
        "connection_mode": "remote",
        "last_seq": 0,
        "supports": {
            "local": True,
            "self_hosted": True,
            "saas": True,
            "private": True,
        },
    }
    assert data["features"] == {
        "intent_locks": True,
        "watcher": True,
        "relay": True,
        "audit_log": True,
        "audit_export": True,
        "dashboard": True,
        "rehearsal_evidence": True,
        "brand_boundary_check": True,
        "policy_rules": True,
    }


def test_capabilities_endpoint_returns_404_for_missing_room(client):
    response = client.get("/api/collaboration/capabilities/ghost")

    assert response.status_code == 404
