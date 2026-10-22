"""Shared ZIP validation and bounded reads for user-supplied archives."""

from __future__ import annotations

import stat
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import BinaryIO


class ArchiveSecurityError(ValueError):
    """An archive exceeds a safety limit or contains an unsafe member."""


@dataclass(frozen=True)
class ArchiveLimits:
    max_archive_bytes: int = 2 * 1024 ** 3
    max_entries: int = 10_000
    max_entry_uncompressed: int = 256 * 1024 ** 2
    max_total_uncompressed: int = 512 * 1024 ** 2
    max_compression_ratio: float = 1000.0


DEFAULT_ARCHIVE_LIMITS = ArchiveLimits()


@dataclass
class ArchiveInspection:
    members: dict[str, zipfile.ZipInfo] = field(default_factory=dict)
    declared_total: int = 0
    read_total: int = 0

    def names(self) -> list[str]:
        return list(self.members)


def _safe_member_name(name: str) -> str:
    normalized = str(name or "").replace("\\", "/")
    if not normalized or normalized.startswith("/") or "\x00" in normalized:
        raise ArchiveSecurityError(f"归档包含非法路径: {name!r}")
    if any(ord(char) < 32 for char in normalized):
        raise ArchiveSecurityError(f"归档路径含控制字符: {name!r}")
    parts = PurePosixPath(normalized).parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ArchiveSecurityError(f"归档路径越界: {name!r}")
    if any(":" in part for part in parts):
        raise ArchiveSecurityError(f"归档路径含盘符或保留字符: {name!r}")
    return normalized[:-1] if normalized.endswith("/") else normalized


def _inspect(archive: zipfile.ZipFile, limits: ArchiveLimits) -> ArchiveInspection:
    infos = archive.infolist()
    if len(infos) > limits.max_entries:
        raise ArchiveSecurityError(
            f"归档条目过多: {len(infos)}（上限 {limits.max_entries}）")
    inspection = ArchiveInspection()
    seen: set[str] = set()
    total = 0
    for info in infos:
        name = _safe_member_name(info.filename)
        key = name.casefold()
        if key in seen:
            raise ArchiveSecurityError(f"归档包含重复路径: {name}")
        seen.add(key)
        if info.flag_bits & 0x1:
            raise ArchiveSecurityError(f"归档包含加密条目: {name}")
        mode = (info.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise ArchiveSecurityError(f"归档包含符号链接: {name}")
        if info.is_dir():
            continue
        if info.file_size < 0 or info.file_size > limits.max_entry_uncompressed:
            raise ArchiveSecurityError(
                f"归档条目过大: {name} ({info.file_size} bytes，"
                f"上限 {limits.max_entry_uncompressed})")
        if (info.file_size > 1024 * 1024 and info.compress_size > 0
                and info.file_size / info.compress_size
                > limits.max_compression_ratio):
            raise ArchiveSecurityError(f"归档条目压缩比异常: {name}")
        total += info.file_size
        if total > limits.max_total_uncompressed:
            raise ArchiveSecurityError(
                f"归档解压总量超限: {total} bytes（上限 "
                f"{limits.max_total_uncompressed}）")
        inspection.members[name] = info
    inspection.declared_total = total
    return inspection


@contextmanager
def open_safe_zip(path: str | Path,
                  limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS
                  ) -> Iterator[tuple[zipfile.ZipFile, ArchiveInspection]]:
    """Open a ZIP only after validating its size and central directory."""
    source = Path(path)
    try:
        archive_size = source.stat().st_size
    except OSError as exc:
        raise ArchiveSecurityError(f"无法读取归档: {exc}") from exc
    if archive_size > limits.max_archive_bytes:
        raise ArchiveSecurityError(
            f"归档文件过大: {archive_size} bytes（上限 "
            f"{limits.max_archive_bytes}）")
    try:
        with zipfile.ZipFile(source, "r") as archive:
            yield archive, _inspect(archive, limits)
    except zipfile.BadZipFile as exc:
        raise ArchiveSecurityError(f"归档格式无效: {exc}") from exc


def read_member(archive: zipfile.ZipFile, inspection: ArchiveInspection,
                name: str,
                limits: ArchiveLimits = DEFAULT_ARCHIVE_LIMITS,
                *, max_bytes: int | None = None) -> bytes:
    """Read one inspected member while bounding the bytes actually produced."""
    info = inspection.members.get(name)
    if info is None:
        raise ArchiveSecurityError(f"归档缺少条目: {name}")
    allowed = min(info.file_size, limits.max_entry_uncompressed)
    if max_bytes is not None:
        allowed = min(allowed, int(max_bytes))
    if inspection.read_total + info.file_size > limits.max_total_uncompressed:
        raise ArchiveSecurityError(
            f"归档实际解压总量将超限（上限 "
            f"{limits.max_total_uncompressed}）")
    chunks: list[bytes] = []
    produced = 0
    try:
        with archive.open(info, "r") as handle:
            produced = _read_bounded(handle, allowed, chunks, name)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ArchiveSecurityError(f"归档条目读取失败: {name}: {exc}") from exc
    if produced != info.file_size:
        raise ArchiveSecurityError(
            f"归档条目大小不一致: {name}（声明 {info.file_size}，实际 {produced}）")
    inspection.read_total += produced
    return b"".join(chunks)


def _read_bounded(handle: BinaryIO, allowed: int, chunks: list[bytes],
                  name: str) -> int:
    produced = 0
    while True:
        chunk = handle.read(min(1024 * 1024, allowed - produced + 1))
        if not chunk:
            return produced
        produced += len(chunk)
        if produced > allowed:
            raise ArchiveSecurityError(
                f"归档条目实际解压超过上限: {name}")
        chunks.append(chunk)
