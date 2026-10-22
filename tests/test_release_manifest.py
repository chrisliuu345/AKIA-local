"""Release provenance manifest generation and verification tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.release_manifest import build_manifest, verify_manifest

ROOT = Path(__file__).resolve().parent.parent


def test_manifest_binds_version_commit_locks_and_artifact(tmp_path):
    artifact = tmp_path / "AKIA-demo.AppImage"
    artifact.write_bytes(b"release-bytes")
    manifest = build_manifest([artifact])
    assert manifest["app_version"]
    assert manifest["git"]["commit"]
    assert manifest["expected_tag"].startswith("v")
    assert manifest["dependency_locks"]["requirements.lock"]["sha256"]
    assert manifest["dependency_locks"]["requirements-ci.lock"]["sha256"]
    assert manifest["artifacts"][0]["sha256"] == hashlib.sha256(
        b"release-bytes").hexdigest()

    path = tmp_path / "release-manifest.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    assert verify_manifest(path) == []


def test_manifest_detects_tampered_artifact(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"before")
    manifest = build_manifest([artifact])
    path = tmp_path / "release-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    artifact.write_bytes(b"after")
    problems = verify_manifest(path)
    assert any("哈希不匹配" in problem for problem in problems)


def test_manifest_rejects_wrong_version(tmp_path):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"x")
    manifest = build_manifest([artifact])
    manifest["app_version"] = "0.0.0"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    problems = verify_manifest(path)
    assert any("APP_VERSION" in problem for problem in problems)
