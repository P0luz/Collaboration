#!/usr/bin/env python
"""
Collaboration brand-boundary compliance check.

What it is: a local scanner for legacy or third-party brand mentions.
What it does: scans text files and reports forbidden terms outside the allowlist.
What it does not do: rewrite files, inspect binaries, or make legal judgments.

Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_TERMS = [
    "Open WebUI",
    "Open-WebUI",
    "open_webui",
    "Savoir-Fair",
    "Savoir Pair",
    "Pair Mesh",
]
TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
ALLOWLIST_PATHS = {
    "plan.md",
    "requirements.txt",
    "scripts/collaboration-compliance/brand_boundary_check.py",
    "tests/collaboration/test_brand_boundary_check.py",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Collaboration brand-boundary terms.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root to scan")
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args(argv)

    report = run_check(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_text_report(report)
    return 0 if report["status"] == "pass" else 1


def run_check(root: Path) -> dict:
    """Scan root and return a machine-readable report."""
    root = root.resolve()
    violations = []
    for path in _iter_text_files(root):
        relative = _relative_posix(path, root)
        if relative in ALLOWLIST_PATHS:
            continue
        violations.extend(_scan_file(path, relative))
    return {
        "status": "pass" if not violations else "fail",
        "summary": {"violations": len(violations)},
        "violations": violations,
    }


def _iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield path


def _scan_file(path: Path, relative: str) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []

    violations = []
    for line_no, line in enumerate(lines, start=1):
        for term in FORBIDDEN_TERMS:
            if term in line:
                violations.append({
                    "path": relative,
                    "line": line_no,
                    "term": term,
                    "excerpt": line.strip(),
                })
    return violations


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _print_text_report(report: dict) -> None:
    if report["status"] == "pass":
        print("Brand boundary check: PASS")
        return
    print("Brand boundary check: FAIL")
    for item in report["violations"]:
        print(f"{item['path']}:{item['line']}: {item['term']} :: {item['excerpt']}")


if __name__ == "__main__":
    sys.exit(main())
