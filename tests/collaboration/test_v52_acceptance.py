"""v5.2 acceptance report tests."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path("scripts/collaboration-release/v52_acceptance.py")


@pytest.fixture
def acceptance_module():
    spec = importlib.util.spec_from_file_location("v52_acceptance", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["v52_acceptance"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_v52_acceptance_report_marks_all_milestones_passed(acceptance_module):
    report = acceptance_module.run_acceptance(Path.cwd())

    assert report["status"] == "pass"
    assert report["summary"] == {"passed": 8, "failed": 0}
    assert [item["id"] for item in report["milestones"]] == [
        "M1",
        "M2",
        "M3",
        "M4",
        "M5",
        "M6",
        "M7",
        "M8",
    ]
    assert all(item["status"] == "pass" for item in report["milestones"])
    assert all(item["evidence"] for item in report["milestones"])


def test_v52_acceptance_cli_prints_json(acceptance_module, capsys):
    exit_code = acceptance_module.main(["--json"], root=Path.cwd())

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["milestones"][-1]["id"] == "M8"
