#!/usr/bin/env python
"""
Collaboration release readiness gate.

What it is: a local M8 release gate for deployment and user-documentation
            readiness.
What it does: verifies required entry docs, app health, self-hosted relay smoke,
              brand-boundary compliance, and optionally the full pytest suite.
What it does not do: deploy infrastructure, publish packages, or change repo
                     state.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

warnings.filterwarnings(
    "ignore",
    message=r"Using `httpx` with `starlette\.testclient` is deprecated.*",
    category=Warning,
)

from fastapi.testclient import TestClient

from backend.collaboration.app import app


REQUIRED_DOCS = [
    "README.md",
    "docs/collaboration/GIT_WORKFLOW.md",
    "docs/collaboration/MCP_RULES.md",
    "docs/collaboration/SELF_HOSTED_RELAY.md",
    "docs/collaboration/RELEASE_READINESS.md",
    "docs/collaboration/LICENSE_BOUNDARY.md",
]


@dataclass
class CheckResult:
    name: str
    status: str
    details: dict[str, Any]


def run_readiness(root: Path, *, include_pytest: bool = False) -> dict[str, Any]:
    """Run release-readiness checks and return a machine-readable report."""
    root = root.resolve()
    checks = [
        _run_check("required_docs", lambda: _check_required_docs(root)),
        _run_check("app_health", _check_app_health),
        _run_check("self_hosted_relay_smoke", lambda: _check_self_hosted_relay(root)),
        _run_check("brand_boundary", lambda: _check_brand_boundary(root)),
    ]
    if include_pytest:
        checks.append(_run_check("pytest", lambda: _check_pytest(root)))

    passed = sum(1 for item in checks if item.status == "pass")
    failed = sum(1 for item in checks if item.status == "fail")
    return {
        "status": "pass" if failed == 0 else "fail",
        "root": str(root),
        "summary": {"passed": passed, "failed": failed},
        "checks": [
            {"name": item.name, "status": item.status, "details": item.details}
            for item in checks
        ],
    }


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Collaboration release readiness checks.")
    parser.add_argument("--root", type=Path, default=root or Path.cwd())
    parser.add_argument("--with-pytest", action="store_true", help="also run py -3.10 -m pytest tests/ -q")
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args(argv)

    report = run_readiness(args.root, include_pytest=args.with_pytest)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_report(report)
    return 0 if report["status"] == "pass" else 1


def _run_check(name: str, fn: Callable[[], dict[str, Any]]) -> CheckResult:
    try:
        return CheckResult(name=name, status="pass", details=fn())
    except Exception as exc:  # pragma: no cover - exercised by CLI failure behavior
        return CheckResult(name=name, status="fail", details={"error": str(exc)})


def _check_required_docs(root: Path) -> dict[str, Any]:
    present = []
    missing = []
    for relative in REQUIRED_DOCS:
        path = root / relative
        if path.is_file() and path.stat().st_size > 0:
            present.append(relative)
        else:
            missing.append(relative)
    if missing:
        raise AssertionError(f"missing required docs: {', '.join(missing)}")
    return {"present": present}


def _check_app_health() -> dict[str, Any]:
    client = TestClient(app)
    response = client.get("/")
    response.raise_for_status()
    payload = response.json()
    if payload != {"service": "collaboration", "status": "ok"}:
        raise AssertionError(f"unexpected health payload: {payload}")
    return payload


def _check_self_hosted_relay(root: Path) -> dict[str, Any]:
    smoke = _load_module(
        root / "scripts/collaboration-relay/self_hosted_smoke.py",
        "self_hosted_smoke_for_readiness",
    )
    report = smoke.run_smoke(
        base_url="http://testserver",
        room_id="release-readiness",
        relay_url="local://memory",
        relay_mode="self_hosted",
        http_client=TestClient(app),
    )
    if report["status"] != "pass":
        raise AssertionError(json.dumps(report, ensure_ascii=False))
    return {"summary": report["summary"], "checks": [item["name"] for item in report["checks"]]}


def _check_brand_boundary(root: Path) -> dict[str, Any]:
    brand = _load_module(
        root / "scripts/collaboration-compliance/brand_boundary_check.py",
        "brand_boundary_for_readiness",
    )
    report = brand.run_check(root)
    if report["status"] != "pass":
        raise AssertionError(json.dumps(report["violations"], ensure_ascii=False))
    return report["summary"]


def _check_pytest(root: Path) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return {"command": f"{sys.executable} -m pytest tests/ -q"}


def _load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _print_report(report: dict[str, Any]) -> None:
    for check in report["checks"]:
        label = "PASS" if check["status"] == "pass" else "FAIL"
        print(f"[{label}] {check['name']}")
        if check["status"] == "fail":
            print(f"  {check['details'].get('error', '')}")
    summary = report["summary"]
    print(f"Release readiness: {summary['passed']} passed, {summary['failed']} failed")


if __name__ == "__main__":
    sys.exit(main())
