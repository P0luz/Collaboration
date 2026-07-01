"""M6 真实协作演练报告脚本测试:生成模板并校验演练证据。"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/collaboration-behavior/rehearsal_report.py")


def test_rehearsal_report_script_creates_template(tmp_path):
    report_path = tmp_path / "m6-rehearsal.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "init",
            str(report_path),
            "--room",
            "R",
            "--operator",
            "WanShi",
            "--participant",
            "WanShi:Codex",
            "--participant",
            "Tingyi:Claude Code",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["milestone"] == "M6"
    assert payload["room_id"] == "R"
    assert payload["operator"] == "WanShi"
    assert payload["status"] == "draft"
    assert payload["participants"] == [
        {"name": "WanShi", "agent": "Codex"},
        {"name": "Tingyi", "agent": "Claude Code"},
    ]
    assert [item["id"] for item in payload["scenarios"]] == [
        "room_setup",
        "collaborative_task_completed",
        "declare_conflict_wait",
        "report_done_handoff",
        "hook_blocked_recovery",
        "retrospective",
    ]


def test_rehearsal_report_script_validates_complete_report(tmp_path):
    report_path = tmp_path / "complete-rehearsal.json"
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
    assert json.loads(result.stdout) == {
        "status": "pass",
        "room_id": "R",
        "participants": 2,
        "duration_minutes": 75,
        "scenarios": 6,
        "passed": 6,
        "failed": 0,
        "missing": [],
    }


def test_rehearsal_report_script_rejects_incomplete_report(tmp_path):
    report = _complete_report()
    report["duration_minutes"] = 45
    report["participants"].pop()
    report["scenarios"][2]["evidence"].pop("wait_result")
    report["scenarios"][4]["status"] = "fail"
    report_path = tmp_path / "bad-rehearsal.json"
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
    assert payload["participants"] == 1
    assert payload["duration_minutes"] == 45
    assert payload["failed"] == 1
    assert {"scenario": "__report__", "field": "participants>=2"} in payload["missing"]
    assert {"scenario": "__report__", "field": "duration_minutes>=60"} in payload["missing"]
    assert {"scenario": "declare_conflict_wait", "field": "wait_result"} in payload["missing"]


def _complete_report() -> dict:
    evidence_by_id = {
        "room_setup": {
            "repo_remote": "git@github.com:P0luz/Collaboration.git",
            "branch": "main",
            "dashboard_url": "http://localhost:8080/api/collaboration/dashboard/R",
        },
        "collaborative_task_completed": {
            "task_summary": "small Collaboration doc change",
            "commit_or_pr": "abc123",
            "test_command": "py -3.10 -m pytest tests/ -q",
        },
        "declare_conflict_wait": {
            "declare_result": "Alice clear, Bob conflict",
            "conflict_result": "Bob queued",
            "wait_result": "Bob held then cleared",
            "audit_excerpt": "declare_intent conflict",
        },
        "report_done_handoff": {
            "report_done_result": "done",
            "promoted_owner": "Bob",
            "pull_rebase_excerpt": "git pull --rebase origin main",
        },
        "hook_blocked_recovery": {
            "hook_result": "blocked",
            "collaboration_action": "wait_for_clear",
            "recovery_result": "re-declared and committed",
        },
        "retrospective": {
            "findings": ["dashboard needs tighter timeline"],
            "follow_up_items": ["add timeline filters"],
            "source_integrity": "no source overwritten",
        },
    }
    return {
        "milestone": "M6",
        "room_id": "R",
        "operator": "WanShi",
        "status": "complete",
        "duration_minutes": 75,
        "participants": [
            {"name": "WanShi", "agent": "Codex"},
            {"name": "Tingyi", "agent": "Claude Code"},
        ],
        "scenarios": [
            {
                "id": scenario_id,
                "status": "pass",
                "evidence": evidence,
                "notes": "",
            }
            for scenario_id, evidence in evidence_by_id.items()
        ],
    }
