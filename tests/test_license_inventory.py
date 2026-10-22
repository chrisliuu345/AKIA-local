"""Third-party license collection and packaging integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.collect_licenses import collect_licenses

ROOT = Path(__file__).resolve().parent.parent


def test_collects_installed_dependency_tree_with_hashes(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("pandas>=2\n", encoding="utf-8")
    result = collect_licenses(
        [str(requirements)],
        tmp_path / "licenses",
        tmp_path / "THIRD_PARTY_NOTICES.md",
    )
    assert result["ok"] is True
    assert result["package_count"] >= 2
    manifest = json.loads(
        (tmp_path / "licenses" / "manifest.json").read_text(encoding="utf-8"))
    packages = {item["name"]: item for item in manifest["packages"]}
    assert "pandas" in packages
    assert "numpy" in packages
    for package in manifest["packages"]:
        assert package["files"]
        assert package["files"][0]["sha256"]
        assert package["files"][0]["size"] >= 0
    notice = (tmp_path / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "| pandas |" in notice
    assert "licenses/manifest.json" in notice


def test_missing_dependency_is_explicit(tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("definitely-not-installed-akia-package>=1\n",
                            encoding="utf-8")
    with pytest.raises(RuntimeError, match="未安装"):
        collect_licenses(
            [str(requirements)],
            tmp_path / "licenses",
            tmp_path / "notices.md",
        )
    allowed = collect_licenses(
        [str(requirements)],
        tmp_path / "licenses-optional",
        tmp_path / "notices-optional.md",
        allow_missing=True,
    )
    assert allowed["ok"] is True
    assert "definitely-not-installed-akia-package" in allowed["missing"]


def test_build_script_bundles_generated_licenses():
    script = (ROOT / "build_pyinstaller.py").read_text(encoding="utf-8")
    assert "collect_licenses.py" in script
    assert '(licenses_dir, "licenses")' in script
    assert "(notice_file, \".\")" in script


def test_current_build_dependencies_have_real_license_texts(tmp_path):
    result = collect_licenses(
        [
            str(ROOT / "requirements.txt"),
            str(ROOT / "requirements-server.txt"),
            str(ROOT / "requirements-connectors.txt"),
        ],
        tmp_path / "licenses",
        tmp_path / "THIRD_PARTY_NOTICES.md",
        allow_missing=True,
    )
    assert result["ok"] is True
    manifest = json.loads(
        (tmp_path / "licenses" / "manifest.json").read_text(encoding="utf-8"))
    placeholder_only = []
    for package in manifest["packages"]:
        texts = [
            (tmp_path / "licenses" / package["name"] / item["name"]).read_text(
                encoding="utf-8", errors="ignore")
            for item in package["files"]
        ]
        if all("No license file was included" in text for text in texts):
            placeholder_only.append(package["name"])
    assert placeholder_only == []
    qt_files = {
        path.name for path in (tmp_path / "licenses" / "pyside6").iterdir()
        if path.is_file()
    }
    assert {"LGPL-3.0.txt", "GPL-3.0.txt", "NOTICE.txt"} <= qt_files
