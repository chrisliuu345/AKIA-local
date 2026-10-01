#!/usr/bin/env python3
"""check_version.py — 版本一致性校验（APP_VERSION 为单一事实源）

用法: python tools/check_version.py

校验范围: config/settings.py 的 APP_VERSION（事实源）、version_info.txt、
build_pyinstaller.py（禁止硬编码）、README/README.en/INSTALL_LINUX 的
产物文件名与版本声明、ROADMAP 头部当前版本。不一致时返回非零退出码。
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_APP_VERSION_RE = re.compile(r'^APP_VERSION\s*=\s*"([^"]+)"', re.MULTILINE)
_ARTIFACT_RES = (
    re.compile(r"AKIA-(\d+\.\d+\.\d+)-x86_64\.AppImage"),
)
_DECL_RES = (
    r"\*\*当前版本\*\*:\s*v(\d+\.\d+\.\d+)",
    r"当前: v(\d+\.\d+\.\d+)",
    r"Current: v(\d+\.\d+\.\d+)",
)


def read_app_version() -> str:
    text = (ROOT / "config" / "settings.py").read_text(encoding="utf-8")
    match = _APP_VERSION_RE.search(text)
    if not match:
        raise SystemExit("无法从 config/settings.py 解析 APP_VERSION")
    return match.group(1)


def check_version_info(version: str, problems: list) -> None:
    path = ROOT / "version_info.txt"
    if not path.exists():
        problems.append("version_info.txt: 文件不存在")
        return
    text = path.read_text(encoding="utf-8")
    numbers = [int(n) for n in re.findall(r"\d+", version)]
    numbers += [0] * (4 - len(numbers))
    expected = f"({numbers[0]}, {numbers[1]}, {numbers[2]}, {numbers[3]})"
    for field in ("filevers", "prodvers"):
        found = re.search(rf"{field}=\([^)]*\)", text)
        if not found or found.group(0).split("=", 1)[1] != expected:
            problems.append(
                f"version_info.txt: {field} 与 APP_VERSION 不一致 (期望 {expected})")
    for field in ("FileVersion", "ProductVersion"):
        if f"u'{field}', u'{version}'" not in text:
            problems.append(f"version_info.txt: {field} 未同步为 {version}")


def check_build_script(problems: list) -> None:
    text = (ROOT / "build_pyinstaller.py").read_text(encoding="utf-8")
    if re.search(r'^APP_VERSION\s*=\s*"', text, re.MULTILINE):
        problems.append("build_pyinstaller.py: 不应硬编码 APP_VERSION（应从 config.settings 导入）")
    if "from config.settings import APP_VERSION" not in text:
        problems.append("build_pyinstaller.py: 未从 config.settings 导入 APP_VERSION")


def check_installer(version: str, problems: list) -> None:
    """Inno Setup 安装器版本（Windows 打包，手动构建也需要同步）"""
    path = ROOT / "packaging" / "AKIA-installer.iss"
    if not path.exists():
        problems.append("packaging/AKIA-installer.iss: 文件不存在")
        return
    found = re.search(r'#define\s+MyAppVersion\s+"([^"]+)"',
                      path.read_text(encoding="utf-8"))
    if not found or found.group(1) != version:
        current = found.group(1) if found else "未声明"
        problems.append(
            f"packaging/AKIA-installer.iss: MyAppVersion {current} != {version}")


def check_version_claims(rel_path: str, version: str, problems: list) -> None:
    path = ROOT / rel_path
    if not path.exists():
        problems.append(f"{rel_path}: 文件不存在")
        return
    text = path.read_text(encoding="utf-8")
    for pattern in _ARTIFACT_RES:
        for found in pattern.findall(text):
            if found != version:
                problems.append(f"{rel_path}: 示例文件名版本 {found} != {version}")
    for pattern in _DECL_RES:
        for found in re.findall(pattern, text):
            if found != version:
                problems.append(f"{rel_path}: 版本声明 {found} != {version}")


def main() -> int:
    version = read_app_version()
    problems: list = []

    check_version_info(version, problems)
    check_build_script(problems)
    check_installer(version, problems)
    for rel in ("README.md", "README.en.md", "INSTALL_LINUX.md",
                "ROADMAP.md", "ROADMAP.en.md"):
        check_version_claims(rel, version, problems)

    print(f"APP_VERSION = {version}")
    if problems:
        print("\n发现版本不一致:")
        for item in problems:
            print(f"  - {item}")
        return 1
    print("版本一致性检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
