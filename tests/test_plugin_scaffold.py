"""Plugin scaffold and static compatibility-check tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.plugin_check import check_plugin_dir, discover_plugin_dirs
from tools.new_plugin import build_scaffold

ROOT = Path(__file__).resolve().parent.parent


def test_generated_plugin_passes_static_contract(tmp_path):
    target = build_scaffold(
        "demo_plugin", "Demo Plugin",
        ["tab", "agent_tools", "settings", "data_source"],
        tmp_path,
    )
    report = check_plugin_dir(target)
    assert report.ok, [issue.as_dict() for issue in report.issues]
    assert report.manifest is not None
    assert report.manifest["api_version"] == "2.1"
    assert discover_plugin_dirs(tmp_path) == [target]

    completed = subprocess.run(
        [sys.executable, "tools/plugin_check.py", str(target), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload[0]["ok"] is True
    assert payload[0]["error_count"] == 0


def test_static_checker_reports_capability_and_entry_errors(tmp_path):
    target = build_scaffold("broken_plugin", "Broken Plugin", ["tab"], tmp_path)
    manifest_path = target / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["capabilities"] = ["tab", "data_source"]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    report = check_plugin_dir(target)
    codes = {issue.code for issue in report.errors}
    assert "capability_method_missing" in codes

    manifest["entry"] = "../outside:Plugin"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    report = check_plugin_dir(target)
    assert any(issue.code == "entry_missing" for issue in report.errors)


def test_scaffold_rejects_invalid_or_existing_targets(tmp_path):
    with pytest.raises(ValueError):
        build_scaffold("Bad-ID", "Bad", ["tab"], tmp_path)
    with pytest.raises(ValueError):
        build_scaffold("no_capability", "None", [], tmp_path)
    build_scaffold("existing_plugin", "Existing", ["tab"], tmp_path)
    with pytest.raises(FileExistsError):
        build_scaffold("existing_plugin", "Existing", ["tab"], tmp_path)


def test_new_plugin_cli(tmp_path):
    output = tmp_path / "plugins"
    completed = subprocess.run(
        [
            sys.executable, "tools/new_plugin.py",
            "--id", "cli_plugin",
            "--name", "CLI Plugin",
            "--capabilities", "agent_tools,data_source",
            "--output", str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    target = output / "cli_plugin"
    assert (target / "plugin.json").is_file()
    assert "def register_agent_tools" in (target / "cli_plugin_impl.py").read_text(
        encoding="utf-8")
    report = check_plugin_dir(target)
    assert report.ok, [issue.as_dict() for issue in report.issues]
