#!/usr/bin/env python3
"""Generate or verify a release provenance manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.settings import APP_VERSION  # noqa: E402

SCHEMA_VERSION = "1.0"


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} 失败")
    return proc.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(path: str | Path) -> dict:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"释放产物不存在: {source}")
    try:
        display = source.relative_to(ROOT).as_posix()
    except ValueError:
        display = str(source)
    return {
        "path": display,
        "name": source.name,
        "size": source.stat().st_size,
        "sha256": _sha256(source),
    }


def build_manifest(artifacts: list[str | Path]) -> dict:
    commit = _git("rev-parse", "HEAD")
    tags = set(_git("tag", "--points-at", "HEAD").splitlines())
    expected_tag = f"v{APP_VERSION}"
    lock_files = {}
    for name in ("requirements.lock", "requirements-ci.lock"):
        path = ROOT / name
        if path.is_file():
            lock_files[name] = {
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
    license_manifest = ROOT / "build" / "third_party_licenses" / "manifest.json"
    license_notice = ROOT / "build" / "THIRD_PARTY_NOTICES.md"
    licenses = {}
    for path in (license_manifest, license_notice):
        if path.is_file():
            licenses[path.relative_to(ROOT).as_posix()] = {
                "sha256": _sha256(path),
                "size": path.stat().st_size,
            }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "app_version": APP_VERSION,
        "expected_tag": expected_tag,
        "git": {
            "commit": commit,
            "tags": sorted(tags),
            "dirty": bool(_git("status", "--porcelain")),
        },
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependency_locks": lock_files,
        "licenses": licenses,
        "artifacts": [_artifact(path) for path in artifacts],
    }


def verify_manifest(path: str | Path, *, require_tag: bool = False,
                    require_clean: bool = False) -> list[str]:
    manifest_path = Path(path).expanduser().resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"无法读取发布清单: {exc}"]
    problems: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"不支持的清单 schema: {manifest.get('schema_version')}")
    if manifest.get("app_version") != APP_VERSION:
        problems.append(
            f"清单版本 {manifest.get('app_version')} != APP_VERSION {APP_VERSION}")
    git_info = manifest.get("git") or {}
    current_commit = _git("rev-parse", "HEAD")
    if git_info.get("commit") != current_commit:
        problems.append("清单提交与当前 HEAD 不一致")
    expected_tag = f"v{APP_VERSION}"
    current_tags = set(_git("tag", "--points-at", "HEAD").splitlines())
    if require_tag and expected_tag not in current_tags:
        problems.append(f"当前提交缺少发布标签 {expected_tag}")
    if manifest.get("expected_tag") != expected_tag:
        problems.append("清单 expected_tag 与当前版本不一致")
    if require_clean and bool(git_info.get("dirty")):
        problems.append("发布清单生成时工作区不干净")
    for rel, expected in (manifest.get("dependency_locks") or {}).items():
        target = ROOT / rel
        if not target.is_file():
            problems.append(f"缺少依赖锁: {rel}")
        elif _sha256(target) != expected.get("sha256"):
            problems.append(f"依赖锁哈希不匹配: {rel}")
    for rel, expected in (manifest.get("licenses") or {}).items():
        target = ROOT / rel
        if not target.is_file():
            problems.append(f"缺少许可证清单: {rel}")
        elif _sha256(target) != expected.get("sha256"):
            problems.append(f"许可证清单哈希不匹配: {rel}")
    for item in manifest.get("artifacts") or []:
        raw = str(item.get("path") or "")
        target = Path(raw) if Path(raw).is_absolute() else ROOT / raw
        if not target.is_file():
            problems.append(f"缺少产物: {raw}")
            continue
        if _sha256(target) != item.get("sha256"):
            problems.append(f"产物哈希不匹配: {raw}")
        if target.stat().st_size != item.get("size"):
            problems.append(f"产物大小不匹配: {raw}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成或校验发布溯源清单")
    parser.add_argument("--artifact", action="append", default=[],
                        help="发布产物；可重复")
    parser.add_argument("--output", default="build/release-manifest.json")
    parser.add_argument("--require-tag", action="store_true",
                        help="要求当前 HEAD 带有 v<APP_VERSION> 标签")
    parser.add_argument("--require-clean", action="store_true",
                        help="要求工作区干净")
    parser.add_argument("--verify", metavar="MANIFEST",
                        help="校验已有清单而不是生成")
    args = parser.parse_args(argv)
    try:
        if args.verify:
            problems = verify_manifest(
                args.verify,
                require_tag=args.require_tag,
                require_clean=args.require_clean,
            )
            if problems:
                for problem in problems:
                    print(f"[fail] {problem}", file=sys.stderr)
                return 1
            print(f"[ok] 发布清单验证通过: {args.verify}")
            return 0
        if args.require_tag:
            tags = set(_git("tag", "--points-at", "HEAD").splitlines())
            if f"v{APP_VERSION}" not in tags:
                raise RuntimeError(f"当前提交缺少发布标签 v{APP_VERSION}")
        manifest = build_manifest(args.artifact)
        if args.require_clean and manifest["git"]["dirty"]:
            raise RuntimeError("工作区不干净，拒绝生成正式发布清单")
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"发布清单失败: {exc}", file=sys.stderr)
        return 1
    print(f"[ok] 发布清单: {output}")
    for item in manifest["artifacts"]:
        print(f"     {item['name']}  sha256={item['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
