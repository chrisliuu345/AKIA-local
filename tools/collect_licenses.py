#!/usr/bin/env python3
"""Collect third-party license texts from installed distribution metadata."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from packaging.markers import default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

MAX_LICENSE_FILE_BYTES = 2 * 1024 ** 2
MAX_LICENSE_TOTAL_BYTES = 50 * 1024 ** 2
OVERRIDE_ROOT = Path(__file__).resolve().parent.parent / "third_party_overrides"
OVERRIDE_GROUPS = {
    "pyside6": "qt_pyside",
    "pyside6-addons": "qt_pyside",
    "pyside6-essentials": "qt_pyside",
    "pyside6-pdf": "qt_pyside",
    "pyside6-webengine": "qt_pyside",
    "shiboken6": "qt_pyside",
    "pyserial": "pyserial",
}
_LICENSE_NAME_RE = re.compile(
    r"(^|/)(license|licence|copying|copyright|notice|authors?)([._-].*)?$",
    re.IGNORECASE,
)


@dataclass
class PackageLicense:
    name: str
    version: str
    license: str
    homepage: str
    files: list[str] = field(default_factory=list)
    missing: bool = False


def _safe_dist_name(name: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", canonicalize_name(name)) or "package"


def _requirement_file_names(paths: list[str]) -> set[str]:
    names: set[str] = set()
    for raw in paths:
        path = Path(raw)
        for line in path.read_text(encoding="utf-8").splitlines():
            text = line.split(" #", 1)[0].strip()
            if not text or text.startswith(("#", "-r", "--")):
                continue
            try:
                requirement = Requirement(text)
            except InvalidRequirement:
                continue
            names.add(canonicalize_name(requirement.name))
    return names


def _installed_map() -> dict[str, importlib.metadata.Distribution]:
    return {
        canonicalize_name(dist.metadata.get("Name") or ""): dist
        for dist in importlib.metadata.distributions()
        if dist.metadata.get("Name")
    }


def _dependency_closure(direct: set[str],
                        installed: dict[str, importlib.metadata.Distribution],
                        *, allow_missing: bool) -> tuple[list[str], list[str]]:
    queue = sorted(direct)
    seen: set[str] = set()
    missing: list[str] = []
    environment = default_environment()
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        dist = installed.get(name)
        if dist is None:
            missing.append(name)
            continue
        for raw in dist.requires or []:
            try:
                requirement = Requirement(raw)
            except InvalidRequirement:
                continue
            if requirement.marker and not requirement.marker.evaluate(environment):
                continue
            dependency = canonicalize_name(requirement.name)
            if dependency not in seen:
                queue.append(dependency)
    if missing and not allow_missing:
        raise RuntimeError(
            "以下依赖未安装，无法收集许可证: " + ", ".join(sorted(missing)))
    return sorted(seen - set(missing)), sorted(missing)


def _license_expression(metadata) -> str:
    expression = str(metadata.get("License-Expression") or "").strip()
    if expression:
        return expression
    legacy = str(metadata.get("License") or "").strip()
    if legacy and len(legacy) <= 160 and "\n" not in legacy:
        return legacy
    classifiers = [
        value.split(" :: ")[-1]
        for value in metadata.get_all("Classifier") or []
        if value.startswith("License ::")
    ]
    return ", ".join(classifiers) if classifiers else "See bundled license text"


def _homepage(metadata) -> str:
    for key in ("Home-page", "Project-URL"):
        values = metadata.get_all(key) or []
        for value in values:
            text = str(value or "").strip()
            if text.startswith(("http://", "https://")):
                return text
            if key == "Project-URL" and ", " in text:
                candidate = text.split(", ", 1)[1].strip()
                if candidate.startswith(("http://", "https://")):
                    return candidate
    return ""


def _license_files(dist: importlib.metadata.Distribution) -> list:
    candidates = []
    for raw in dist.metadata.get_all("License-File") or []:
        candidates.append(raw)
    for item in dist.files or []:
        text = str(item)
        if _LICENSE_NAME_RE.search(text):
            candidates.append(item)
    unique = []
    seen = set()
    for item in candidates:
        key = str(item)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _copy_license_files(dist: importlib.metadata.Distribution, package_dir: Path,
                        total_budget: list[int]) -> list[str]:
    copied: list[str] = []
    used_names: set[str] = set()
    for item in _license_files(dist):
        relative = Path(str(item))
        if relative.is_absolute() or ".." in relative.parts:
            continue
        source = Path(dist.locate_file(item))
        if not source.is_file():
            continue
        size = source.stat().st_size
        if size > MAX_LICENSE_FILE_BYTES or total_budget[0] + size > MAX_LICENSE_TOTAL_BYTES:
            continue
        filename = relative.name or "LICENSE.txt"
        if filename.casefold() in used_names:
            filename = f"{len(copied) + 1}-{filename}"
        used_names.add(filename.casefold())
        target = package_dir / filename
        shutil.copyfile(source, target)
        total_budget[0] += size
        copied.append(target.name)
    return copied


def _copy_override_files(package_name: str, package_dir: Path,
                         total_budget: list[int]) -> list[str]:
    group = OVERRIDE_GROUPS.get(canonicalize_name(package_name))
    if not group:
        return []
    source_dir = OVERRIDE_ROOT / group
    if not source_dir.is_dir():
        return []
    copied = []
    for source in sorted(source_dir.iterdir()):
        if not source.is_file():
            continue
        size = source.stat().st_size
        if size > MAX_LICENSE_FILE_BYTES or total_budget[0] + size > MAX_LICENSE_TOTAL_BYTES:
            continue
        target = package_dir / source.name
        shutil.copyfile(source, target)
        total_budget[0] += size
        copied.append(target.name)
    return copied


def collect_licenses(requirements: list[str], output: str | Path,
                     notice_path: str | Path, *,
                     allow_missing: bool = False) -> dict:
    direct = _requirement_file_names(requirements)
    if not direct:
        raise ValueError("未从 requirements 文件解析到任何依赖")
    installed = _installed_map()
    names, missing = _dependency_closure(
        direct, installed, allow_missing=allow_missing)
    output_dir = Path(output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    budget = [0]
    packages: list[PackageLicense] = []
    for name in names:
        dist = installed[name]
        package_dir = output_dir / _safe_dist_name(name)
        package_dir.mkdir(parents=True, exist_ok=True)
        for stale in package_dir.iterdir():
            if stale.is_file():
                stale.unlink()
        copied = _copy_license_files(dist, package_dir, budget)
        if not copied:
            copied = _copy_override_files(name, package_dir, budget)
        if not copied:
            placeholder = package_dir / "LICENSE.txt"
            placeholder.write_text(
                f"{name} {dist.version}\n"
                f"License: {_license_expression(dist.metadata)}\n"
                "No license file was included in the installed distribution metadata.\n",
                encoding="utf-8")
            copied = [placeholder.name]
        packages.append(PackageLicense(
            name=name,
            version=str(dist.version),
            license=_license_expression(dist.metadata),
            homepage=_homepage(dist.metadata),
            files=copied,
        ))

    package_payload = []
    for package in packages:
        files = []
        for filename in package.files:
            path = output_dir / _safe_dist_name(package.name) / filename
            files.append({
                "name": filename,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            })
        package_payload.append({
            "name": package.name,
            "version": package.version,
            "license": package.license,
            "homepage": package.homepage,
            "files": files,
        })
    manifest = {
        "schema_version": "1.0",
        "requirements": [Path(path).name for path in requirements],
        "missing": missing,
        "packages": package_payload,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    notice = Path(notice_path).expanduser().resolve()
    notice.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Third-Party Notices",
        "",
        ("AKIA includes third-party Python packages. Their license texts are bundled "
         "under `licenses/`; package metadata and file hashes are recorded in "
         "`licenses/manifest.json`."),
        "",
        "| Package | Version | License | Source |",
        "|---------|---------|---------|--------|",
    ]
    for package in packages:
        source = package.homepage or ""
        lines.append(
            f"| {package.name} | {package.version} | {package.license} | {source} |")
    if missing:
        lines.extend([
            "",
            "Optional or unavailable packages not included: " + ", ".join(missing),
        ])
    lines.append("")
    notice.write_text("\n".join(lines), encoding="utf-8")
    return {
        "ok": not missing or allow_missing,
        "output": str(output_dir),
        "notice": str(notice),
        "package_count": len(packages),
        "missing": missing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="从已安装依赖生成第三方许可证与归属清单")
    parser.add_argument("--requirements", action="append", required=True,
                        help="requirements 文件；可重复")
    parser.add_argument("--output", required=True, help="许可证文件输出目录")
    parser.add_argument("--notice", required=True, help="THIRD_PARTY_NOTICES.md 路径")
    parser.add_argument("--allow-missing", action="store_true",
                        help="允许可选依赖未安装")
    parser.add_argument("--json", action="store_true", help="输出 JSON 摘要")
    args = parser.parse_args(argv)
    try:
        result = collect_licenses(
            args.requirements, args.output, args.notice,
            allow_missing=args.allow_missing)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"许可证收集失败: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"已收集 {result['package_count']} 个依赖的许可证 → {result['output']}")
        print(f"第三方声明: {result['notice']}")
        if result["missing"]:
            print("未安装的可选依赖: " + ", ".join(result["missing"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
