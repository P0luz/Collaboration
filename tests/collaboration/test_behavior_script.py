"""强制层行为脚本测试:验证本地脚本能模拟不听话 AI 并产出机器可读结果。"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/collaboration-behavior/forced_layer_checks.py")


def test_forced_layer_script_reports_all_required_scenarios():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
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
    assert payload["summary"] == {"passed": 5, "failed": 0}

    scenarios = {item["name"]: item for item in payload["scenarios"]}
    assert set(scenarios) == {
        "watcher_flags_unclaimed_change",
        "watcher_flags_locked_by_other",
        "hook_blocks_no_lock",
        "hook_blocks_locked_by_other",
        "push_gate_detects_waiting_lock",
    }
    assert scenarios["watcher_flags_unclaimed_change"]["details"]["reason"] == "no_active_lock"
    assert scenarios["watcher_flags_locked_by_other"]["details"]["holder"] == "Alice"
    assert scenarios["hook_blocks_no_lock"]["details"]["action_tool"] == "wait_for_clear"
    assert scenarios["hook_blocks_locked_by_other"]["details"]["blocked_files"] == ["src/main.py"]
    assert scenarios["push_gate_detects_waiting_lock"]["details"]["waiting_locks"] == 1


def test_forced_layer_script_text_output_is_human_readable():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "[PASS] watcher_flags_unclaimed_change" in result.stdout
    assert "[PASS] push_gate_detects_waiting_lock" in result.stdout
    assert "Forced layer behavior checks: 5 passed, 0 failed" in result.stdout
