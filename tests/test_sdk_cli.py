"""AKIA v4.5.0 headless SDK / CLI contract tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from akia_sdk import (
    AKIAClient,
    InvalidParameterError,
    ToolNotFoundError,
)

ROOT = Path(__file__).resolve().parent.parent


def _frame() -> pd.DataFrame:
    rng = np.random.default_rng(12)
    values = rng.normal(10.0, 0.08, 50)
    return pd.DataFrame({
        "直径": values,
        "USL": [10.4] * len(values),
        "LSL": [9.6] * len(values),
    })


def _write_qap(path: Path, frame: pd.DataFrame) -> None:
    csv_text = frame.to_csv(index=False)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps({"version": "2.0"}))
        archive.writestr("data/Sheet1.csv", csv_text)


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["MPLBACKEND"] = "Agg"
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONPATH"] = str(ROOT)
    return env


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "akia_sdk", *args],
        cwd=ROOT,
        env=_child_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_sdk_contract_and_validation():
    client = AKIAClient.from_dataframes({"Sheet1": _frame()})
    names = {spec["name"] for spec in client.tool_specs()}
    assert {"list_data", "run_spc", "run_capability", "run_msa_grr"} <= names
    assert len(names) >= 30

    result = client.run("run_capability", {"column": "直径"})
    assert result.ok, result.error
    assert result.data["cpk"] is not None
    payload = result.as_dict()
    assert payload["schema_version"] == "1.0"
    assert payload["sdk_api_version"] == "1.0"
    assert payload["kind"] == "tool_result"
    json.dumps(payload, allow_nan=False)

    with pytest.raises(ToolNotFoundError):
        client.run("does_not_exist")
    with pytest.raises(InvalidParameterError):
        client.run("run_capability", {"column": "直径", "typo": 1})


def test_sdk_rejects_unknown_non_generic_column_parameters():
    client = AKIAClient.from_dataframes({"Sheet1": _frame()})
    with pytest.raises(InvalidParameterError, match="列不存在"):
        client.run("run_msa_grr", {
            "sheet": "Sheet1",
            "measurement_column": "不存在",
            "part_column": "零件",
            "operator_column": "操作员",
        })


def test_sdk_profile_and_one_click():
    client = AKIAClient.from_dataframes({"Sheet1": _frame()})
    profile = client.profile()
    assert profile["global_summary"]["total_rows"] == 50
    assert "Sheet1" in profile["sheets"]

    result = client.one_click(["capability"])
    assert result["total_count"] == 1
    assert result["success_count"] == 1
    assert result["results"][0]["analysis_type"] == "capability"


def test_sdk_loads_csv_and_qap_without_qt(tmp_path):
    data_path = tmp_path / "data.csv"
    _frame().to_csv(data_path, index=False)
    project_path = tmp_path / "demo.qap"
    _write_qap(project_path, _frame())

    code = r"""
import json
import sys

class BlockQt:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "PySide6" or fullname.startswith("PySide6."):
            raise ImportError("PySide6 is intentionally blocked")
        return None

sys.meta_path.insert(0, BlockQt())
import akia_sdk

assert "PySide6" not in sys.modules
csv_client = akia_sdk.AKIAClient.from_file(sys.argv[1])
csv_result = csv_client.run("run_capability", {"column": "直径"})
assert csv_result.ok, csv_result.error

project_client = akia_sdk.AKIAClient.from_project(sys.argv[2])
project_result = project_client.run("list_data")
assert project_result.ok, project_result.error
assert "Sheet1" in project_result.text
json.dumps(csv_result.as_dict(), allow_nan=False)
print("headless-ok")
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(data_path), str(project_path)],
        cwd=ROOT,
        env=_child_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "headless-ok" in completed.stdout


def test_sdk_project_load_does_not_touch_recent_projects(tmp_path, monkeypatch):
    from core.project_manager import ProjectManager

    project_path = tmp_path / "no-side-effect.qap"
    _write_qap(project_path, _frame())
    calls = []
    monkeypatch.setattr(
        ProjectManager, "add_recent",
        lambda *args, **kwargs: calls.append((args, kwargs)))

    AKIAClient.from_project(project_path)
    assert calls == []


def test_cli_run_success_and_structured_errors(tmp_path):
    data_path = tmp_path / "data.csv"
    _frame().to_csv(data_path, index=False)
    no_spec_path = tmp_path / "no_spec.csv"
    _frame()[["直径"]].to_csv(no_spec_path, index=False)

    completed = _run_cli(
        "run", "--input", str(data_path), "--tool", "run_capability",
        "--params", json.dumps({"column": "直径"}), "--pretty")
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["data"]["cpk"] is not None

    bad_param = _run_cli(
        "run", "--input", str(data_path), "--tool", "run_capability",
        "--params", json.dumps({"column": "直径", "unknown": 1}))
    assert bad_param.returncode == 2
    error = json.loads(bad_param.stderr)
    assert error["error"]["code"] == "invalid_parameters"

    analysis_failure = _run_cli(
        "run", "--input", str(no_spec_path), "--tool", "run_capability",
        "--params", json.dumps({"column": "直径"}))
    assert analysis_failure.returncode == 1
    failed = json.loads(analysis_failure.stdout)
    assert failed["ok"] is False
    assert failed["tool"] == "run_capability"

    invalid_column = _run_cli(
        "run", "--input", str(data_path), "--tool", "run_capability",
        "--params", json.dumps({"column": "不存在"}))
    assert invalid_column.returncode == 2
    assert json.loads(invalid_column.stderr)["error"]["code"] == "invalid_parameters"


def test_cli_tools_and_atomic_output(tmp_path):
    catalog = _run_cli("tools", "--category", "质量分析")
    assert catalog.returncode == 0, catalog.stderr
    payload = json.loads(catalog.stdout)
    assert payload["kind"] == "tool_catalog"
    assert payload["count"] >= 1
    assert all(tool["category"] == "质量分析" for tool in payload["tools"])

    output = tmp_path / "catalog.json"
    first = _run_cli("tools", "--output", str(output))
    assert first.returncode == 0, first.stderr
    assert output.is_file()
    second = _run_cli("tools", "--output", str(output))
    assert second.returncode == 2
    assert json.loads(second.stderr)["error"]["code"] == "output_error"
    forced = _run_cli("tools", "--output", str(output), "--force")
    assert forced.returncode == 0, forced.stderr


def test_cli_one_click_does_not_report_zero_results_as_success(tmp_path):
    data_path = tmp_path / "text-only.csv"
    pd.DataFrame({"status": ["accepted", "rejected"]}).to_csv(
        data_path, index=False)

    completed = _run_cli(
        "one-click", "--input", str(data_path), "--select", "capability")
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["ok"] is False
    assert payload["data"]["total_count"] == 0
