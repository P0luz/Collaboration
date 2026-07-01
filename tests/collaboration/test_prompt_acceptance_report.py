"""Prompt 层验收报告脚本测试:生成模板并校验真实 agent 验收证据。"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/collaboration-behavior/prompt_acceptance_report.py")


def test_prompt_acceptance_script_creates_json_template(tmp_path):
    report_path = tmp_path / "codex-report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "init",
            str(report_path),
            "--agent",
            "Codex",
            "--operator",
            "WanShi",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["agent"] == "Codex"
    assert payload["operator"] == "WanShi"
    assert payload["status"] == "draft"
    assert [item["id"] for item in payload["scenarios"]] == [
        "declare_before_edit",
        "conflict_wait_for_clear",
        "report_done_releases_lock",
        "hook_blocked_action_followed",
    ]
    assert payload["scenarios"][0]["required_evidence"] == [
        "intent_result",
        "changed_files",
        "command_excerpt",
    ]


def test_prompt_acceptance_script_validates_complete_report(tmp_path):
    report_path = tmp_path / "complete-report.json"
    report_path.write_text(json.dumps(_complete_report(), ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", str(report_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "status": "pass",
        "agent": "Codex",
        "scenarios": 4,
        "passed": 4,
        "failed": 0,
        "missing": [],
    }


def test_prompt_acceptance_script_rejects_missing_evidence(tmp_path):
    report = _complete_report()
    report["scenarios"][1]["evidence"].pop("command_excerpt")
    report["scenarios"][2]["status"] = "fail"
    report_path = tmp_path / "bad-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", str(report_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["failed"] == 1
    assert {
        "scenario": "conflict_wait_for_clear",
        "field": "command_excerpt",
    } in payload["missing"]


def _complete_report() -> dict:
    scenarios = []
    for scenario_id, evidence in {
        "declare_before_edit": {
            "intent_result": "clear",
            "changed_files": ["src/main.py"],
            "command_excerpt": "declare_intent -> clear",
        },
        "conflict_wait_for_clear": {
            "intent_result": "conflict",
            "wait_result": "held_then_cleared",
            "command_excerpt": "wait_for_clear -> all_clear=true",
        },
        "report_done_releases_lock": {
            "done_result": "done",
            "promoted_owner": "Bob",
            "command_excerpt": "report_done -> promoted Bob",
        },
        "hook_blocked_action_followed": {
            "hook_result": "blocked",
            "action_tool": "wait_for_clear",
            "command_excerpt": "COLLABORATION_ACTION parsed",
        },
    }.items():
        scenarios.append({
            "id": scenario_id,
            "status": "pass",
            "evidence": evidence,
            "notes": "",
        })
    return {
        "agent": "Codex",
        "operator": "WanShi",
        "run_id": "2026-07-02-codex",
        "status": "complete",
        "scenarios": scenarios,
    }
