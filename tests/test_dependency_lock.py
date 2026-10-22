"""Hashed dependency lock and CI supply-chain gate tests."""

from __future__ import annotations

from pathlib import Path

from tools.check_dependencies import CORE_BANNED, check_lock

ROOT = Path(__file__).resolve().parent.parent


def test_current_locks_are_hashed_and_separated():
    core = check_lock(
        ROOT / "requirements.lock",
        [ROOT / "requirements.txt"],
    )
    ci = check_lock(
        ROOT / "requirements-ci.lock",
        [ROOT / "requirements-ci.in"],
    )
    assert core.errors == [], core.errors
    assert ci.errors == [], ci.errors
    assert not (CORE_BANNED & core.packages)
    assert {"asyncua", "pymodbus", "paho-mqtt", "pyodbc"} <= ci.packages
    assert "pyinstaller" in ci.packages
    assert {"pytest", "ruff", "pip-audit"} <= ci.packages


def test_unhashed_or_missing_source_dependency_is_rejected(tmp_path):
    lock = tmp_path / "bad.lock"
    lock.write_text("example-package==1.0\n", encoding="utf-8")
    report = check_lock(lock, [])
    assert any("缺少 sha256" in error for error in report.errors)

    source = tmp_path / "requirements.in"
    source.write_text("missing-package>=1\n", encoding="utf-8")
    report = check_lock(lock, [source])
    assert any("missing-package" in error for error in report.errors)


def test_ci_workflow_uses_hashes_and_audit():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8")
    assert "--require-hashes -r requirements-ci.lock" in workflow
    assert "--require-hashes -r requirements.lock" in workflow
    assert "pip-audit" in workflow
    assert "python-version: [\"3.11\", \"3.14\"]" in workflow
