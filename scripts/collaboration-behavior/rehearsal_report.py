#!/usr/bin/env python
"""
M6 real collaboration rehearsal report helper.

What it is: a tiny CLI for recording 60-90 minute real Pair Mesh rehearsals.
What it does: creates a JSON report template and validates completed evidence.
What it does not do: drive agents, mutate the repo, or call Collaboration APIs.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCENARIOS = [
    {
        "id": "room_setup",
        "title": "Room, participants, dashboard, branch are ready",
        "required_evidence": [
            "repo_remote",
            "branch",
            "dashboard_url",
        ],
    },
    {
        "id": "collaborative_task_completed",
        "title": "A real collaboration task is completed",
        "required_evidence": [
            "task_summary",
            "commit_or_pr",
            "test_command",
        ],
    },
    {
        "id": "declare_conflict_wait",
        "title": "Declare, conflict, and wait are observed",
        "required_evidence": [
            "declare_result",
            "conflict_result",
            "wait_result",
            "audit_excerpt",
        ],
    },
    {
        "id": "report_done_handoff",
        "title": "Report done releases lock and hands off",
        "required_evidence": [
            "report_done_result",
            "promoted_owner",
            "pull_rebase_excerpt",
        ],
    },
    {
        "id": "hook_blocked_recovery",
        "title": "Hook blocks unsafe change and recovery succeeds",
        "required_evidence": [
            "hook_result",
            "collaboration_action",
            "recovery_result",
        ],
    },
    {
        "id": "retrospective",
        "title": "Retrospective captures findings and source integrity",
        "required_evidence": [
            "findings",
            "follow_up_items",
            "source_integrity",
        ],
    },
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create or validate Collaboration M6 rehearsal reports."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a rehearsal report template")
    init_parser.add_argument("path", type=Path, help="output JSON report path")
    init_parser.add_argument("--room", required=True, help="Collaboration room id")
    init_parser.add_argument("--operator", required=True, help="human rehearsal operator")
    init_parser.add_argument(
        "--participant",
        action="append",
        default=[],
        help='participant as "name:agent"; can be repeated',
    )
    init_parser.add_argument("--run-id", help="stable run identifier")

    validate_parser = subparsers.add_parser("validate", help="validate a completed report")
    validate_parser.add_argument("path", type=Path, help="report JSON path")
    validate_parser.add_argument("--json", action="store_true", help="print machine-readable output")

    args = parser.parse_args(argv)
    if args.command == "init":
        return _init_report(args.path, args.room, args.operator, args.participant, args.run_id)
    if args.command == "validate":
        return _validate_report(args.path, as_json=args.json)
    raise AssertionError(f"unknown command {args.command}")


def _init_report(
    path: Path,
    room_id: str,
    operator: str,
    participants: list[str],
    run_id: str | None,
) -> int:
    report = {
        "milestone": "M6",
        "room_id": room_id,
        "operator": operator,
        "run_id": run_id or _default_run_id(room_id),
        "status": "draft",
        "duration_minutes": 0,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "participants": [_parse_participant(item) for item in participants],
        "scenarios": [
            {
                "id": scenario["id"],
                "title": scenario["title"],
                "status": "draft",
                "required_evidence": scenario["required_evidence"],
                "evidence": {},
                "notes": "",
            }
            for scenario in SCENARIOS
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(path))
    return 0


def _validate_report(path: Path, *, as_json: bool) -> int:
    report = _read_json(path)
    result = _validate_payload(report)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_text_result(result)
    return 0 if result["status"] == "pass" else 1


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"report not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("report root must be a JSON object")
    return payload


def _validate_payload(report: dict[str, Any]) -> dict[str, Any]:
    missing = []
    participants = report.get("participants", [])
    if not isinstance(participants, list):
        participants = []
    duration = report.get("duration_minutes", 0)
    if not isinstance(duration, (int, float)):
        duration = 0

    if len(participants) < 2:
        missing.append({"scenario": "__report__", "field": "participants>=2"})
    if duration < 60:
        missing.append({"scenario": "__report__", "field": "duration_minutes>=60"})

    scenario_map = {
        scenario.get("id"): scenario
        for scenario in report.get("scenarios", [])
        if isinstance(scenario, dict)
    }
    passed = 0
    failed = 0

    for required in SCENARIOS:
        scenario_id = required["id"]
        scenario = scenario_map.get(scenario_id)
        if scenario is None:
            missing.append({"scenario": scenario_id, "field": "__scenario__"})
            failed += 1
            continue

        if scenario.get("status") == "pass":
            passed += 1
        else:
            failed += 1

        evidence = scenario.get("evidence", {})
        if not isinstance(evidence, dict):
            evidence = {}
        for field in required["required_evidence"]:
            if _is_missing(evidence.get(field)):
                missing.append({"scenario": scenario_id, "field": field})

    return {
        "status": "pass" if failed == 0 and not missing else "fail",
        "room_id": report.get("room_id", ""),
        "participants": len(participants),
        "duration_minutes": duration,
        "scenarios": len(SCENARIOS),
        "passed": passed,
        "failed": failed,
        "missing": missing,
    }


def _parse_participant(value: str) -> dict[str, str]:
    if ":" not in value:
        return {"name": value.strip(), "agent": ""}
    name, agent = value.split(":", 1)
    return {"name": name.strip(), "agent": agent.strip()}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) == 0
    return False


def _print_text_result(result: dict[str, Any]) -> None:
    label = "PASS" if result["status"] == "pass" else "FAIL"
    print(f"M6 rehearsal report: {label}")
    print(
        f"Room={result['room_id']} participants={result['participants']} "
        f"duration={result['duration_minutes']}m scenarios={result['scenarios']} "
        f"passed={result['passed']} failed={result['failed']}"
    )
    if result["missing"]:
        print("Missing evidence:")
        for item in result["missing"]:
            print(f"  - {item['scenario']}: {item['field']}")


def _default_run_id(room_id: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    normalized = "".join(
        char.lower() if char.isalnum() else "-"
        for char in room_id.strip()
    ).strip("-")
    return f"{today}-{normalized or 'room'}-m6"


if __name__ == "__main__":
    sys.exit(main())
