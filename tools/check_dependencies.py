#!/usr/bin/env python3
"""Validate hashed dependency locks and their source separation."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parent.parent
_PIN_RE = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)")
_HASH_RE = re.compile(r"--hash=sha256:[0-9a-f]{64}")

CORE_BANNED = {
    "asyncua", "docxtpl", "fastapi", "ghapi", "jinja2",
    "mediapipe", "nuitka", "opencv-contrib-python", "paho-mqtt",
    "pip-audit", "pyinstaller", "pyinstaller-hooks-contrib",
    "pymodbus", "pyodbc", "pytest", "ruff",
    "sounddevice", "uvicorn", "websockets",
}
CI_REQUIRED = {
    "asyncua", "fastapi", "paho-mqtt", "pymodbus", "pyodbc",
    "pyinstaller", "pytest", "ruff", "uvicorn", "websockets",
}


@dataclass
class LockReport:
    path: Path
    packages: set[str] = field(default_factory=set)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "path": str(self.path),
            "ok": not self.errors,
            "package_count": len(self.packages),
            "errors": self.errors,
        }


def _source_names(path: Path, seen: set[Path] | None = None) -> set[str]:
    source = path.resolve()
    visited = seen if seen is not None else set()
    if source in visited:
        return set()
    visited.add(source)
    names: set[str] = set()
    for line in source.read_text(encoding="utf-8").splitlines():
        text = line.split(" #", 1)[0].strip()
        if not text or text.startswith(("#", "--")):
            continue
        if text.startswith("-r "):
            names |= _source_names(source.parent / text[3:].strip(), visited)
            continue
        try:
            names.add(canonicalize_name(Requirement(text).name))
        except InvalidRequirement:
            continue
    return names


def check_lock(path: str | Path,
               sources: list[str | Path] | tuple[str | Path, ...] = ()
               ) -> LockReport:
    lock_path = Path(path)
    report = LockReport(lock_path)
    lines = lock_path.read_text(encoding="utf-8").splitlines()
    current = ""
    current_hashes = 0

    def _finish() -> None:
        nonlocal current, current_hashes
        if current and current_hashes == 0:
            report.errors.append(f"{current}: 缺少 sha256 哈希")
        current = ""
        current_hashes = 0

    for line in lines:
        match = _PIN_RE.match(line)
        if match:
            _finish()
            current = match.group(1)
            report.packages.add(canonicalize_name(current))
            continue
        if current and _HASH_RE.search(line):
            current_hashes += 1
        if line.strip() and not line.startswith((" ", "#")) and not match:
            _finish()
    _finish()

    for source in sources:
        for name in sorted(_source_names(Path(source)) - report.packages):
            report.errors.append(f"锁定文件缺少直接依赖: {name}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查依赖锁哈希与分层")
    parser.add_argument("--core-lock", default="requirements.lock")
    parser.add_argument("--ci-lock", default="requirements-ci.lock")
    args = parser.parse_args(argv)
    core = check_lock(
        ROOT / args.core_lock,
        [ROOT / "requirements.txt"],
    )
    ci = check_lock(
        ROOT / args.ci_lock,
        [ROOT / "requirements-ci.in"],
    )
    banned = sorted(CORE_BANNED & core.packages)
    if banned:
        core.errors.append("核心锁混入可选或开发依赖: " + ", ".join(banned))
    missing = sorted(CI_REQUIRED - ci.packages)
    if missing:
        ci.errors.append("CI 锁缺少可选/开发依赖: " + ", ".join(missing))

    failed = False
    for report in (core, ci):
        state = "ok" if not report.errors else "fail"
        print(f"[{state}] {report.path.name}: {len(report.packages)} packages")
        for error in report.errors:
            print(f"  - {error}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
