"""Release readiness gate tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from backend.collaboration import audit, events, locks, queues, relay, rooms, watcher


SCRIPT_PATH = Path("scripts/collaboration-release/readiness_check.py")


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
    watcher._reported_unclaimed.clear()
    yield


@pytest.fixture
def readiness_module():
    spec = importlib.util.spec_from_file_location("release_readiness", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["release_readiness"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_release_readiness_gate_runs_core_checks(readiness_module):
    report = readiness_module.run_readiness(Path.cwd(), include_pytest=False)

    assert report["status"] == "pass"
    assert report["summary"] == {"passed": 5, "failed": 0}
    assert [item["name"] for item in report["checks"]] == [
        "required_docs",
        "app_health",
        "self_hosted_relay_smoke",
        "deployment_packaging",
        "brand_boundary",
    ]
    assert "README.md" in report["checks"][0]["details"]["present"]
    assert "docs/collaboration/DEPLOYMENT.md" in report["checks"][0]["details"]["present"]
    assert report["checks"][1]["details"] == {
        "service": "collaboration",
        "status": "ok",
    }
    assert report["checks"][3]["details"] == {
        "files": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
    }


def test_release_readiness_cli_prints_json(readiness_module, capsys):
    exit_code = readiness_module.main(["--json"], root=Path.cwd())

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["checks"][2]["name"] == "self_hosted_relay_smoke"
    assert payload["checks"][3]["name"] == "deployment_packaging"


def test_release_readiness_script_runs_from_file_path():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
