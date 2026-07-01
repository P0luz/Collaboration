#!/usr/bin/env python
"""
Collaboration forced-layer behavior checks
==========================================

What it is: a local scenario runner for M5 forced-layer AI behavior checks.
What it does: simulates disobedient AI edits in temporary git repositories and
              verifies watcher, hook feedback, and push-gate state.
What it does not do: run real AI agents, mutate the current working tree, or
                     install git hooks into user repositories.
Exports: run_checks and a CLI that prints text or JSON results.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import warnings
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

warnings.filterwarnings(
    "ignore",
    message=r"Using `httpx` with `starlette\.testclient` is deprecated.*",
    category=Warning,
)

from fastapi.testclient import TestClient

from backend.collaboration import audit, events, locks, queues, relay, rooms, watcher
from backend.collaboration.app import app
from backend.collaboration.schema import EventType


ROOM_ID = "behavior"


@dataclass
class ScenarioResult:
    name: str
    status: str
    details: dict


def run_checks() -> dict:
    """Run all forced-layer behavior scenarios and return a machine-readable report."""
    scenarios = [
        _run_scenario("watcher_flags_unclaimed_change", _watcher_flags_unclaimed_change),
        _run_scenario("watcher_flags_locked_by_other", _watcher_flags_locked_by_other),
        _run_scenario("hook_blocks_no_lock", _hook_blocks_no_lock),
        _run_scenario("hook_blocks_locked_by_other", _hook_blocks_locked_by_other),
        _run_scenario("push_gate_detects_waiting_lock", _push_gate_detects_waiting_lock),
        _run_scenario("idle_timeout_releases_unreported_lock", _idle_timeout_releases_unreported_lock),
        _run_scenario("partial_conflict_blocks_conflict_file", _partial_conflict_blocks_conflict_file),
    ]
    passed = sum(1 for item in scenarios if item.status == "pass")
    failed = len(scenarios) - passed
    return {
        "status": "pass" if failed == 0 else "fail",
        "summary": {"passed": passed, "failed": failed},
        "scenarios": [asdict(item) for item in scenarios],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Collaboration forced-layer behavior checks.")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args(argv)

    report = run_checks()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_text_report(report)
    return 0 if report["status"] == "pass" else 1


def _run_scenario(name: str, fn: Callable[[], dict]) -> ScenarioResult:
    try:
        details = fn()
    except Exception as exc:  # pragma: no cover - exercised by CLI failure behavior
        return ScenarioResult(name=name, status="fail", details={"error": str(exc)})
    return ScenarioResult(name=name, status="pass", details=details)


def _watcher_flags_unclaimed_change() -> dict:
    with _clean_state(), _temp_repo() as repo:
        rooms.create_room(ROOM_ID)
        _write(repo, "src/unclaimed.py", "print('unclaimed')\n")

        summary = watcher.scan_once(ROOM_ID, str(repo), actor="Codex")
        event = _latest_event(EventType.UNCLAIMED_CHANGE)

        assert summary["unclaimed_changes"] == ["src/unclaimed.py"]
        assert event.payload["reason"] == "no_active_lock"
        return {"file": event.payload["file"], "reason": event.payload["reason"]}


def _watcher_flags_locked_by_other() -> dict:
    with _clean_state(), _temp_repo() as repo:
        rooms.create_room(ROOM_ID)
        locks.declare_intent(
            ROOM_ID,
            "Alice",
            "Claude Code",
            ["src/main.py"],
            "own the file",
        )
        _write(repo, "src/main.py", "print('bob touched it')\n")

        summary = watcher.scan_once(ROOM_ID, str(repo), actor="Bob")
        event = _latest_event(EventType.UNCLAIMED_CHANGE)

        assert summary["unclaimed_changes"] == ["src/main.py"]
        assert event.payload["reason"] == "locked_by_other"
        return {
            "file": event.payload["file"],
            "reason": event.payload["reason"],
            "holder": event.payload["holder"],
        }


def _hook_blocks_no_lock() -> dict:
    with _clean_state():
        client = _client_with_room()

        response = client.post("/api/collaboration/hook/check", json={
            "room_id": ROOM_ID,
            "requester": "Bob",
            "staged_files": ["src/no_lock.py"],
        }).json()

        assert response["blocked"] is True
        action = response["COLLABORATION_ACTION"]
        assert action["tool"] == "wait_for_clear"
        return {
            "blocked_files": response["COLLABORATION_ACTION"]["args"]["files"],
            "action_tool": action["tool"],
        }


def _hook_blocks_locked_by_other() -> dict:
    with _clean_state():
        client = _client_with_room()
        client.post("/api/collaboration/intent/declare", json={
            "room_id": ROOM_ID,
            "owner": "Alice",
            "agent": "Claude Code",
            "files": ["src/main.py"],
            "intent": "fix bug",
        })

        response = client.post("/api/collaboration/hook/check", json={
            "room_id": ROOM_ID,
            "requester": "Bob",
            "staged_files": ["src/main.py"],
        }).json()

        assert response["blocked"] is True
        assert response["results"][0]["status"] == "locked_by_other"
        return {
            "blocked_files": response["COLLABORATION_ACTION"]["args"]["files"],
            "holder": response["results"][0]["holder"],
        }


def _push_gate_detects_waiting_lock() -> dict:
    with _clean_state():
        client = _client_with_room()
        client.post("/api/collaboration/intent/declare", json={
            "room_id": ROOM_ID,
            "owner": "Alice",
            "agent": "Claude Code",
            "files": ["src/main.py"],
            "intent": "fix bug",
        })
        client.post("/api/collaboration/intent/declare", json={
            "room_id": ROOM_ID,
            "owner": "Bob",
            "agent": "Codex",
            "files": ["src/main.py"],
            "intent": "add feature",
        })

        status = client.get(f"/api/collaboration/status/{ROOM_ID}").json()

        assert len(status["waiting_locks"]) == 1
        return {
            "waiting_locks": len(status["waiting_locks"]),
            "waiting_owner": status["waiting_locks"][0]["owner"],
        }


def _idle_timeout_releases_unreported_lock() -> dict:
    with _clean_state():
        rooms.create_room(ROOM_ID)
        first = locks.declare_intent(
            ROOM_ID,
            "Alice",
            "Claude Code",
            ["src/stale.py"],
            "start work but never report done",
        )
        stale = locks.get_lock(first["lock_id"])
        stale.idle_timeout_seconds = 30
        stale.last_activity = (
            datetime.now(timezone.utc) - timedelta(seconds=90)
        ).isoformat()

        takeover = locks.declare_intent(
            ROOM_ID,
            "Bob",
            "Codex",
            ["src/stale.py"],
            "take over after timeout",
        )
        holder = locks.get_file_holder(ROOM_ID, "src/stale.py")

        assert stale.status.value == "expired"
        assert takeover["status"] == "clear"
        assert holder.owner == "Bob"
        return {
            "file": "src/stale.py",
            "expired_owner": stale.owner,
            "new_holder": holder.owner,
        }


def _partial_conflict_blocks_conflict_file() -> dict:
    with _clean_state():
        client = _client_with_room()
        client.post("/api/collaboration/intent/declare", json={
            "room_id": ROOM_ID,
            "owner": "Alice",
            "agent": "Claude Code",
            "files": ["src/main.py"],
            "intent": "own main",
        })
        bob = client.post("/api/collaboration/intent/declare", json={
            "room_id": ROOM_ID,
            "owner": "Bob",
            "agent": "Codex",
            "files": ["src/other.py"],
            "intent": "own other",
        }).json()

        extended = client.post("/api/collaboration/intent/extend", json={
            "lock_id": bob["lock_id"],
            "additional_files": ["src/main.py", "src/bob_test.py"],
            "reason": "need implementation and test",
        }).json()
        response = client.post("/api/collaboration/hook/check", json={
            "room_id": ROOM_ID,
            "requester": "Bob",
            "staged_files": ["src/main.py", "src/bob_test.py"],
        }).json()

        assert extended["status"] == "partial_conflict"
        assert extended["extended_files"] == ["src/bob_test.py"]
        assert extended["conflict_files"][0]["file"] == "src/main.py"
        assert response["blocked"] is True
        assert response["COLLABORATION_ACTION"]["args"]["files"] == ["src/main.py"]
        return {
            "extended_files": extended["extended_files"],
            "blocked_files": response["COLLABORATION_ACTION"]["args"]["files"],
            "holder": response["results"][0]["holder"],
        }


class _clean_state:
    def __enter__(self):
        rooms._rooms.clear()
        rooms._participants.clear()
        locks._locks.clear()
        locks._file_holders.clear()
        queues._queues.clear()
        audit._call_logs.clear()
        events._events.clear()
        relay._connections.clear()
        relay._event_streams.clear()
        relay._next_seq.clear()
        watcher._reported_unclaimed.clear()
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _temp_repo:
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        _git(self.path, "init")
        _git(self.path, "config", "user.email", "behavior@example.com")
        _git(self.path, "config", "user.name", "Behavior Check")
        return self.path

    def __exit__(self, exc_type, exc, tb):
        self._tmp.cleanup()
        return False


def _client_with_room() -> TestClient:
    client = TestClient(app)
    client.post("/api/collaboration/room/create", json={"room_id": ROOM_ID})
    return client


def _latest_event(event_type: EventType):
    for event in events.get_events(ROOM_ID, limit=20):
        if event.event_type == event_type:
            return event
    raise AssertionError(f"missing event {event_type}")


def _write(repo: Path, relative_path: str, content: str) -> None:
    path = repo / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _print_text_report(report: dict) -> None:
    for scenario in report["scenarios"]:
        label = "PASS" if scenario["status"] == "pass" else "FAIL"
        print(f"[{label}] {scenario['name']}")
        if scenario["details"]:
            print(f"  {json.dumps(scenario['details'], ensure_ascii=False, sort_keys=True)}")
    summary = report["summary"]
    print(
        f"Forced layer behavior checks: {summary['passed']} passed, "
        f"{summary['failed']} failed"
    )


if __name__ == "__main__":
    sys.exit(main())
