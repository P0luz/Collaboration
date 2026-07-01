#!/usr/bin/env python
"""
v5.2 acceptance report for Collaboration.

What it is: a machine-readable milestone evidence report for the v5.2 delivery.
What it does: verifies that each v5.2 milestone has concrete code, test, script,
              or documentation evidence in the repository.
What it does not do: run the full test suite, deploy services, or mutate files.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MILESTONES = [
    {
        "id": "M1",
        "title": "Clean base and license boundary",
        "evidence": [
            "LICENSE",
            "THIRD_PARTY_NOTICES.md",
            "docs/collaboration/LICENSE_BOUNDARY.md",
            "scripts/collaboration-compliance/brand_boundary_check.py",
        ],
    },
    {
        "id": "M2",
        "title": "Local intent lock and queue protocol",
        "evidence": [
            "backend/collaboration/rooms.py",
            "backend/collaboration/locks.py",
            "backend/collaboration/queues.py",
            "tests/collaboration/test_locks.py",
            "tests/collaboration/test_queues.py",
        ],
    },
    {
        "id": "M3",
        "title": "Relay metadata sync foundation",
        "evidence": [
            "backend/collaboration/relay.py",
            "backend/collaboration/relay_client.py",
            "tests/collaboration/test_relay.py",
            "tests/collaboration/test_relay_client.py",
        ],
    },
    {
        "id": "M4",
        "title": "Watcher and Git hook enforcement",
        "evidence": [
            "backend/collaboration/watcher.py",
            "backend/collaboration/git_gate.py",
            "scripts/collaboration-hooks/pre-commit",
            "scripts/collaboration-hooks/pre-push",
            "tests/collaboration/test_watcher.py",
            "tests/collaboration/test_git_gate.py",
        ],
    },
    {
        "id": "M5",
        "title": "AI behavior and audit evidence",
        "evidence": [
            "backend/collaboration/audit.py",
            "scripts/collaboration-behavior/forced_layer_checks.py",
            "scripts/collaboration-behavior/prompt_acceptance_report.py",
            "docs/collaboration/AI_BEHAVIOR_TESTS.md",
            "docs/collaboration/PROMPT_ACCEPTANCE.md",
            "tests/collaboration/test_audit.py",
        ],
    },
    {
        "id": "M6",
        "title": "Real rehearsal and dashboard review",
        "evidence": [
            "backend/collaboration/dashboard.py",
            "backend/collaboration/rehearsal.py",
            "scripts/collaboration-behavior/rehearsal_report.py",
            "docs/collaboration/REAL_REHEARSAL.md",
            "tests/collaboration/test_dashboard.py",
            "tests/collaboration/test_rehearsal_evidence.py",
        ],
    },
    {
        "id": "M7",
        "title": "Commercial readiness metadata and relay paths",
        "evidence": [
            "backend/collaboration/policy.py",
            "backend/collaboration/capabilities.py",
            "docs/collaboration/SELF_HOSTED_RELAY.md",
            "docs/collaboration/PRODUCT_TIERS.md",
            "tests/collaboration/test_capabilities.py",
            "tests/collaboration/test_product_tiers.py",
        ],
    },
    {
        "id": "M8",
        "title": "Deployment, readiness, and user handoff",
        "evidence": [
            "README.md",
            "Dockerfile",
            "docker-compose.yml",
            "docs/collaboration/DEPLOYMENT.md",
            "docs/collaboration/RELEASE_READINESS.md",
            "scripts/collaboration-release/readiness_check.py",
            "tests/collaboration/test_release_readiness.py",
        ],
    },
]


def run_acceptance(root: Path) -> dict[str, Any]:
    """Return v5.2 milestone evidence status for the repository."""
    root = root.resolve()
    milestones = []
    for milestone in MILESTONES:
        present = []
        missing = []
        for relative in milestone["evidence"]:
            path = root / relative
            if path.is_file() and path.stat().st_size > 0:
                present.append(relative)
            else:
                missing.append(relative)
        milestones.append({
            "id": milestone["id"],
            "title": milestone["title"],
            "status": "pass" if not missing else "fail",
            "evidence": present,
            "missing": missing,
        })

    failed = sum(1 for item in milestones if item["status"] == "fail")
    passed = len(milestones) - failed
    return {
        "status": "pass" if failed == 0 else "fail",
        "root": str(root),
        "summary": {"passed": passed, "failed": failed},
        "milestones": milestones,
    }


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Collaboration v5.2 acceptance evidence.")
    parser.add_argument("--root", type=Path, default=root or Path.cwd())
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args(argv)

    report = run_acceptance(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report)
    return 0 if report["status"] == "pass" else 1


def _print_report(report: dict[str, Any]) -> None:
    for milestone in report["milestones"]:
        label = "PASS" if milestone["status"] == "pass" else "FAIL"
        print(f"[{label}] {milestone['id']} {milestone['title']}")
        if milestone["missing"]:
            print(f"  missing: {', '.join(milestone['missing'])}")
    summary = report["summary"]
    print(f"v5.2 acceptance: {summary['passed']} passed, {summary['failed']} failed")


if __name__ == "__main__":
    sys.exit(main())
