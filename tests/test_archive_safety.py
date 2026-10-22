"""Shared archive limits and integration tests."""

from __future__ import annotations

import stat
import zipfile

import pytest

from core.archive_safety import (
    ArchiveLimits,
    ArchiveSecurityError,
    open_safe_zip,
    read_member,
)
from core.evidence_pack import read_evidence_pack, verify_evidence_pack
from core.project_manager import ProjectManager
from core.share_pack import scan_share_pack


def _zip(path, entries):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return path


def test_safe_archive_roundtrip(tmp_path):
    path = _zip(tmp_path / "safe.zip", [
        ("manifest.json", b'{"version":"2.0"}'),
        ("data/Sheet1.csv", b"x\n1\n2\n"),
    ])
    with open_safe_zip(path) as (archive, inspection):
        assert set(inspection.names()) == {"manifest.json", "data/Sheet1.csv"}
        assert inspection.declared_total == 23
        manifest = read_member(
            archive, inspection, "manifest.json", max_bytes=1024)
        assert manifest.startswith(b'{"version"')
        assert inspection.read_total == len(manifest)


@pytest.mark.parametrize("name", [
    "../escape.txt",
    "/absolute.txt",
    "C:/windows.txt",
    "folder/../../escape.txt",
])
def test_path_traversal_rejected(tmp_path, name):
    path = _zip(tmp_path / "bad-path.zip", [(name, b"x")])
    with pytest.raises(ArchiveSecurityError, match="非法|越界|盘符"):
        with open_safe_zip(path):
            pass


def test_duplicate_case_insensitive_path_rejected(tmp_path):
    path = _zip(tmp_path / "duplicate.zip", [
        ("Report.json", b"{}"),
        ("report.json", b"{}"),
    ])
    with pytest.raises(ArchiveSecurityError, match="重复"):
        with open_safe_zip(path):
            pass


def test_entry_count_and_size_limits(tmp_path):
    path = _zip(tmp_path / "limits.zip", [
        ("a.txt", b"a" * 1024),
        ("b.txt", b"b" * 1024),
    ])
    with pytest.raises(ArchiveSecurityError, match="条目过多"):
        with open_safe_zip(path, ArchiveLimits(max_entries=1)):
            pass
    with pytest.raises(ArchiveSecurityError, match="条目过大"):
        with open_safe_zip(path, ArchiveLimits(max_entry_uncompressed=100)):
            pass
    with pytest.raises(ArchiveSecurityError, match="解压总量"):
        with open_safe_zip(path, ArchiveLimits(max_total_uncompressed=1500)):
            pass


def test_compression_ratio_and_symlink_rejected(tmp_path):
    bomb = _zip(tmp_path / "ratio.zip", [("zeros.bin", b"\0" * (2 * 1024 * 1024))])
    with pytest.raises(ArchiveSecurityError, match="压缩比"):
        with open_safe_zip(bomb, ArchiveLimits(max_compression_ratio=5)):
            pass

    linked = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("link")
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(linked, "w") as archive:
        archive.writestr(info, "target")
    with pytest.raises(ArchiveSecurityError, match="符号链接"):
        with open_safe_zip(linked):
            pass


def test_read_member_respects_format_limit(tmp_path):
    path = _zip(tmp_path / "manifest.zip", [
        ("manifest.json", b"x" * 1024),
    ])
    with open_safe_zip(path) as (archive, inspection):
        with pytest.raises(ArchiveSecurityError, match="实际解压"):
            read_member(archive, inspection, "manifest.json", max_bytes=100)


def test_consumers_report_unsafe_archives(tmp_path):
    path = _zip(tmp_path / "malicious.qap", [
        ("../manifest.json", b'{"version":"2.0"}'),
    ])
    with pytest.raises(ArchiveSecurityError):
        ProjectManager.get_project_info(str(path))
    with pytest.raises(ArchiveSecurityError):
        ProjectManager.load_project(str(path))
    with pytest.raises(ArchiveSecurityError):
        read_evidence_pack(str(path))
    verify = verify_evidence_pack(str(path))
    assert verify["ok"] is False
    assert any("归档" in problem for problem in verify["problems"])
    scan = scan_share_pack(str(path), raw_data={})
    assert scan["ok"] is False
    assert scan["findings"][0]["kind"] == "read-error"
