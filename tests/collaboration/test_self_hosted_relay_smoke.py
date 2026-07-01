"""Self-hosted relay smoke script tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.collaboration import audit, events, locks, queues, relay, rooms
from backend.collaboration.app import app


SCRIPT_PATH = Path("scripts/collaboration-relay/self_hosted_smoke.py")


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
def smoke_module():
    spec = importlib.util.spec_from_file_location("self_hosted_smoke", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["self_hosted_smoke"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_smoke_runner_verifies_self_hosted_relay_path(smoke_module):
    report = smoke_module.run_smoke(
        base_url="http://testserver",
        room_id="relay-smoke",
        relay_url="local://memory",
        relay_mode="self_hosted",
        http_client=TestClient(app),
    )

    assert report["status"] == "pass"
    assert report["summary"] == {"passed": 7, "failed": 0}
    assert [item["name"] for item in report["checks"]] == [
        "create_room",
        "connect_relay",
        "declare_intent",
        "report_done",
        "capabilities",
        "relay_events",
        "audit_export",
    ]
    capabilities = report["checks"][4]["details"]
    assert capabilities["policy"]["relay_mode"] == "self_hosted"
    assert capabilities["relay"]["connected"] is True
    assert capabilities["features"]["audit_export"] is True


def test_smoke_cli_prints_json_report(smoke_module, capsys):
    exit_code = smoke_module.main(
        [
            "--base-url",
            "http://testserver",
            "--room-id",
            "relay-smoke",
            "--relay-url",
            "local://memory",
            "--relay-mode",
            "self_hosted",
            "--json",
        ],
        http_client=TestClient(app),
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["room_id"] == "relay-smoke"
