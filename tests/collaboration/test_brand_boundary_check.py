"""品牌边界检查脚本测试:防止旧品牌或第三方名义进入产品表面。"""

import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/collaboration-compliance/brand_boundary_check.py")


def test_brand_boundary_check_flags_forbidden_terms_outside_allowlist(tmp_path):
    (tmp_path / "plan.md").write_text("历史说明: no Open WebUI source.\n", encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.py").write_text('TITLE = "Powered by Open WebUI"\n', encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "page.md").write_text("Pair Mesh public page\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "fail"
    assert payload["summary"] == {"violations": 2}
    assert {item["term"] for item in payload["violations"]} == {"Open WebUI", "Pair Mesh"}
    assert all(item["path"] != "plan.md" for item in payload["violations"])


def test_brand_boundary_check_passes_current_repo():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "status": "pass",
        "summary": {"violations": 0},
        "violations": [],
    }
