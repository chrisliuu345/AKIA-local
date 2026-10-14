"""v4.4.0 八链路演示脚本回归（v4.4.0 B7-1）。"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_demo_v44_case_end_to_end(tmp_path):
    output = tmp_path / "demo_v44"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "demo_v44_case.py"),
         "--output", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=180, check=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "全链路通过" in proc.stdout
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["alert_case"]["opened"] is True
    assert summary["alert_case"]["merged"] is True
    assert summary["sampling"]["state"] == "tightened"
    assert summary["gauge"]["state"] == "drift"
    assert summary["skills"]["baseline_feasible"] is False
    assert summary["skills"]["trained_feasible"] is True
    assert summary["case_closure"]["status"] == "closed"
    assert summary["benefit"]["recompute_updates"] == 1
    assert summary["evidence"]["pack_ok"] is True
