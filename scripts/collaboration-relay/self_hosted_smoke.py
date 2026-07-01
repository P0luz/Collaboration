#!/usr/bin/env python
"""
Self-hosted relay smoke check for Collaboration.

What it is: a deploy-time smoke runner for a self-hosted Collaboration API.
What it does: verifies room creation, relay connection, intent lifecycle,
              capabilities, relay event streaming, and audit export.
What it does not do: transmit source code, provision infrastructure, or mutate
                     the current repository.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any, Callable

import httpx


SMOKE_FILE = "docs/collaboration/SELF_HOSTED_RELAY.md"


@dataclass
class CheckResult:
    name: str
    status: str
    details: dict[str, Any]


def run_smoke(
    *,
    base_url: str,
    room_id: str,
    relay_url: str,
    relay_mode: str,
    http_client: Any | None = None,
) -> dict[str, Any]:
    """Run the self-hosted relay smoke flow and return a JSON-safe report."""
    client = _ApiClient(base_url=base_url, http_client=http_client)
    checks: list[CheckResult] = []
    context: dict[str, Any] = {}

    def step(name: str, fn: Callable[[], dict[str, Any]]) -> None:
        if _has_failure(checks):
            return
        try:
            details = fn()
        except Exception as exc:  # pragma: no cover - CLI failure path
            checks.append(CheckResult(name=name, status="fail", details={"error": str(exc)}))
            return
        checks.append(CheckResult(name=name, status="pass", details=details))

    step("create_room", lambda: _create_room(client, room_id, relay_mode))
    step("connect_relay", lambda: _connect_relay(client, room_id, relay_url))
    step("declare_intent", lambda: _declare_intent(client, room_id, context))
    step("report_done", lambda: _report_done(client, context))
    step("capabilities", lambda: _capabilities(client, room_id, relay_mode))
    step("relay_events", lambda: _relay_events(client, room_id))
    step("audit_export", lambda: _audit_export(client, room_id))
    client.close()

    passed = sum(1 for item in checks if item.status == "pass")
    failed = sum(1 for item in checks if item.status == "fail")
    return {
        "status": "pass" if failed == 0 else "fail",
        "base_url": base_url.rstrip("/"),
        "room_id": room_id,
        "relay_url": relay_url,
        "relay_mode": relay_mode,
        "summary": {"passed": passed, "failed": failed},
        "checks": [
            {"name": item.name, "status": item.status, "details": item.details}
            for item in checks
        ],
    }


def main(argv: list[str] | None = None, *, http_client: Any | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a Collaboration self-hosted relay smoke check."
    )
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--room-id", default="self-hosted-relay-smoke")
    parser.add_argument("--relay-url", default="local://memory")
    parser.add_argument(
        "--relay-mode",
        default="self_hosted",
        choices=["local", "self_hosted", "saas", "private"],
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args(argv)

    report = run_smoke(
        base_url=args.base_url,
        room_id=args.room_id,
        relay_url=args.relay_url,
        relay_mode=args.relay_mode,
        http_client=http_client,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report)
    return 0 if report["status"] == "pass" else 1


def _create_room(client: "_ApiClient", room_id: str, relay_mode: str) -> dict[str, Any]:
    payload = client.post("/api/collaboration/room/create", {
        "room_id": room_id,
        "plan": "free",
        "relay_mode": relay_mode,
    })
    _require(payload["status"] == "created", "room was not created")
    return {
        "status": payload["status"],
        "plan": payload["room"]["plan"],
        "relay_mode": payload["room"]["relay_mode"],
    }


def _connect_relay(client: "_ApiClient", room_id: str, relay_url: str) -> dict[str, Any]:
    payload = client.post("/api/collaboration/relay/connect", {
        "room_id": room_id,
        "relay_url": relay_url,
    })
    _require(payload["status"] == "connected", "relay was not connected")
    return {
        "status": payload["status"],
        "mode": payload["mode"],
        "relay_url": payload["relay_url"],
    }


def _declare_intent(
    client: "_ApiClient",
    room_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    payload = client.post("/api/collaboration/intent/declare", {
        "room_id": room_id,
        "owner": "self-hosted-smoke",
        "agent": "smoke-runner",
        "files": [SMOKE_FILE],
        "intent": "verify self-hosted relay lifecycle",
    })
    _require(payload["status"] == "clear", "intent declaration did not clear")
    context["lock_id"] = payload["lock_id"]
    return {"status": payload["status"], "files": payload["files"]}


def _report_done(client: "_ApiClient", context: dict[str, Any]) -> dict[str, Any]:
    lock_id = context.get("lock_id")
    _require(bool(lock_id), "missing lock_id from declare_intent")
    payload = client.post("/api/collaboration/intent/done", {
        "lock_id": lock_id,
        "summary": "self-hosted relay smoke passed intent lifecycle",
    })
    _require(payload["status"] == "done", "intent was not released")
    return {"status": payload["status"], "lock_id": payload["lock_id"]}


def _capabilities(
    client: "_ApiClient",
    room_id: str,
    relay_mode: str,
) -> dict[str, Any]:
    payload = client.get(f"/api/collaboration/capabilities/{room_id}")
    _require(payload["policy"]["relay_mode"] == relay_mode, "capability relay mode mismatch")
    _require(payload["relay"]["connected"] is True, "capability relay not connected")
    _require(payload["features"]["audit_export"] is True, "audit export feature is disabled")
    return payload


def _relay_events(client: "_ApiClient", room_id: str) -> dict[str, Any]:
    payload = client.get(f"/api/collaboration/relay/events/{room_id}", params={"since": 0})
    event_types = [item["event"]["type"] for item in payload["events"]]
    _require("intent_declared" in event_types, "missing intent_declared relay event")
    _require("lock_released" in event_types, "missing lock_released relay event")
    return {"last_seq": payload["last_seq"], "event_types": event_types}


def _audit_export(client: "_ApiClient", room_id: str) -> dict[str, Any]:
    text = client.get_text(f"/api/collaboration/audit/{room_id}/export")
    _require("declare_intent" in text, "missing declare_intent audit line")
    _require("report_done" in text, "missing report_done audit line")
    return {"lines": len([line for line in text.splitlines() if line.strip()])}


def _has_failure(checks: list[CheckResult]) -> bool:
    return any(item.status == "fail" for item in checks)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _print_report(report: dict[str, Any]) -> None:
    for check in report["checks"]:
        label = "PASS" if check["status"] == "pass" else "FAIL"
        print(f"[{label}] {check['name']}")
        if check["status"] == "fail":
            print(f"  {check['details'].get('error', '')}")
    summary = report["summary"]
    print(
        f"Self-hosted relay smoke: {summary['passed']} passed, "
        f"{summary['failed']} failed"
    )


class _ApiClient:
    def __init__(self, *, base_url: str, http_client: Any | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http_client or httpx.Client(base_url=self.base_url)
        self._owns_http = http_client is None

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.http.post(path, json=payload)
        return self._json(response)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.http.get(path, params=params)
        return self._json(response)

    def get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        response = self.http.get(path, params=params)
        response.raise_for_status()
        return response.text

    def close(self) -> None:
        if self._owns_http:
            self.http.close()

    @staticmethod
    def _json(response: Any) -> dict[str, Any]:
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise AssertionError("response root is not a JSON object")
        return payload


if __name__ == "__main__":
    sys.exit(main())
