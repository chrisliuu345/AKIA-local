#!/usr/bin/env python3
"""Windows 安装包冒烟：编译 Inno Setup 安装包并核对随包文件。

只应由 tag 工作流调用（``.github/workflows/ci.yml`` 的 ``package-windows``）。
检查安装结果而不是构建目录：``.iss`` 的 ``[Files]`` 若漏掉程序目录，
仅查看 ``build/AKIA.dist`` 仍会通过。

确认三项：
- 程序入口 ``AKIA.exe``
- 项目许可证 ``_internal/LICENSE``（与仓库 ``LICENSE`` 字节一致）
- 第三方归属 ``_internal/THIRD_PARTY_NOTICES.md``

PyInstaller 6 的 onedir 把 ``--add-data`` 放进 ``_internal/``，安装脚本原样复制该目录。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ENTRY_RELATIVE = Path("AKIA.exe")
LICENSE_RELATIVE = Path("_internal") / "LICENSE"
NOTICE_RELATIVE = Path("_internal") / "THIRD_PARTY_NOTICES.md"
# 与 tools/collect_licenses.py 写出的归属页同一标识，避免空文件或同名占位通过。
NOTICE_MARKERS = (
    "# Third-Party Notices",
    "| Package | Version | License | Source |",
)
MIN_ENTRY_BYTES = 1024
INSTALL_TIMEOUT_SECONDS = 900
DEFAULT_INSTALL_ROOT = Path(r"C:\akia-installer-smoke")
# 冒烟会先删掉安装目录。这些前缀是系统目录，不能当 /DIR。
_UNSAFE_INSTALL_PREFIXES = (
    "c:\\windows",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\users",
    "c:\\programdata",
)


def _license_bytes(data: bytes) -> bytes:
    # Windows 检出可能把 LF 收成 CRLF。比对正文，不把换行差异当成漏打许可证。
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def payload_problems(install_root: Path, project_license: Path) -> list[str]:
    """返回安装结果里缺失或不匹配的项；空列表表示三项都在。"""
    root = Path(install_root)
    problems: list[str] = []

    entry = root / ENTRY_RELATIVE
    if not entry.is_file():
        problems.append(f"缺少程序入口 {ENTRY_RELATIVE.as_posix()}")
    else:
        with entry.open("rb") as handle:
            magic = handle.read(2)
        if magic != b"MZ" or entry.stat().st_size < MIN_ENTRY_BYTES:
            problems.append(f"程序入口 {ENTRY_RELATIVE.as_posix()} 不是有效的 Windows 可执行文件")

    license_path = root / LICENSE_RELATIVE
    expected = Path(project_license)
    if not license_path.is_file():
        problems.append(f"缺少项目许可证 {LICENSE_RELATIVE.as_posix()}")
    elif not expected.is_file():
        problems.append(f"仓库许可证不存在: {expected}")
    elif _license_bytes(license_path.read_bytes()) != _license_bytes(expected.read_bytes()):
        problems.append("安装结果中的 LICENSE 与项目 LICENSE 不一致")

    notice = root / NOTICE_RELATIVE
    if not notice.is_file():
        problems.append(f"缺少第三方归属 {NOTICE_RELATIVE.as_posix()}")
    else:
        text = notice.read_text(encoding="utf-8", errors="replace")
        missing = [marker for marker in NOTICE_MARKERS if marker not in text]
        if missing:
            problems.append("第三方归属内容不完整: " + ", ".join(missing))
    return problems


def installer_arguments(setup: Path, install_root: Path, log_path: Path) -> list[str]:
    """静默安装参数。

    ``/VERYSILENT`` 仍会弹出 “Do you wish to continue?”，除非同时带 ``/SP-``。
    漏掉 ``/SP-`` 时标签任务会一直停在该提示上。
    ``/MERGETASKS`` 只取消桌面和开始菜单快捷方式，避免冒烟改动运行器桌面。
    """
    directory = Path(install_root)
    if sys.platform == "win32" and not directory.is_absolute():
        raise ValueError(f"/DIR 必须是绝对路径: {directory}")
    return [
        str(setup),
        "/VERYSILENT",
        "/SP-",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/NOCANCEL",
        f"/DIR={directory}",
        f"/LOG={log_path}",
        "/MERGETASKS=!desktopicon,!startmenu",
    ]


def find_iscc() -> Path | None:
    candidates: list[Path] = []
    env = os.environ.get("ISCC")
    if env:
        candidates.append(Path(env))
    for name in ("ISCC", "ISCC.exe", "iscc"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    candidates.extend([
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ])
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.is_file():
            return path
    return None


def find_setup_executable(dist_dir: Path) -> Path:
    found = sorted(
        path for path in Path(dist_dir).glob("AKIA-Setup-*.exe") if path.is_file())
    if len(found) != 1:
        names = ", ".join(path.name for path in found) or "(无)"
        raise RuntimeError(f"期望 dist 中恰好一个 AKIA-Setup-*.exe，实际: {names}")
    return found[0]


def _unsafe_install_root(path: Path) -> bool:
    text = str(path).replace("/", "\\").rstrip("\\").lower()
    if text.endswith(":") and len(text) <= 3:
        return True
    return any(
        text == prefix or text.startswith(prefix + "\\")
        for prefix in _UNSAFE_INSTALL_PREFIXES
    )


def prepare_install_root() -> Path:
    raw = Path(os.environ.get("AKIA_INSTALLER_SMOKE_DIR", str(DEFAULT_INSTALL_ROOT)))
    if _unsafe_install_root(raw):
        raise RuntimeError(f"拒绝在系统目录执行安装冒烟: {raw}")
    resolved = raw.resolve()
    if _unsafe_install_root(resolved):
        raise RuntimeError(f"拒绝在系统目录执行安装冒烟: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    return resolved


def read_setup_log(path: Path) -> str:
    if not path.is_file():
        return ""
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    return data.decode("utf-8", errors="replace")


def _dump_log(path: Path) -> None:
    text = read_setup_log(path).strip()
    if not text:
        print("[warn] 没有安装日志")
        return
    lines = text.splitlines()
    print("[log] 安装日志末尾:")
    for line in lines[-80:]:
        print(f"  {line}")


def compile_installer(iscc: Path, iss: Path) -> int:
    print(f"[compile] {iscc} {iss}")
    completed = subprocess.run([str(iscc), str(iss)], cwd=ROOT, check=False)
    return completed.returncode


def install_silently(setup: Path, install_root: Path, log_path: Path) -> int:
    if log_path.exists():
        log_path.unlink()
    command = installer_arguments(setup, install_root, log_path)
    print("[install] " + " ".join(command))
    try:
        completed = subprocess.run(
            command, check=False, timeout=INSTALL_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        print(f"[error] 安装程序超过 {INSTALL_TIMEOUT_SECONDS} 秒未结束")
        _dump_log(log_path)
        return 1
    if completed.returncode != 0:
        print(f"[error] 安装程序退出码 {completed.returncode}")
        _dump_log(log_path)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="编译并冒烟 Windows 安装包")
    parser.add_argument("--iss", type=Path, default=ROOT / "packaging" / "AKIA-installer.iss")
    parser.add_argument("--dist", type=Path, default=ROOT / "dist")
    parser.add_argument("--license", type=Path, default=ROOT / "LICENSE")
    args = parser.parse_args(argv)

    if sys.platform != "win32":
        print("[error] Windows 安装包冒烟只能在 Windows 上运行", file=sys.stderr)
        return 2

    iss = args.iss if args.iss.is_absolute() else ROOT / args.iss
    if not iss.is_file():
        print(f"[error] 找不到安装脚本: {iss}", file=sys.stderr)
        return 2
    iscc = find_iscc()
    if iscc is None:
        print("[error] 找不到 ISCC.exe。请先安装 Inno Setup 6，或设置 ISCC。",
              file=sys.stderr)
        return 2
    if compile_installer(iscc, iss) != 0:
        print("[error] Inno Setup 编译失败", file=sys.stderr)
        return 1

    dist_dir = args.dist if args.dist.is_absolute() else ROOT / args.dist
    try:
        setup = find_setup_executable(dist_dir)
        install_root = prepare_install_root()
    except (OSError, RuntimeError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    print(f"[setup] {setup} ({setup.stat().st_size} bytes)")
    log_path = install_root.with_name(install_root.name + ".log")
    try:
        if install_silently(setup, install_root, log_path) != 0:
            return 1
        problems = payload_problems(install_root, args.license)
        for relative in (ENTRY_RELATIVE, LICENSE_RELATIVE, NOTICE_RELATIVE):
            path = install_root / relative
            if path.is_file():
                print(f"[ok] {relative.as_posix()} ({path.stat().st_size} bytes)")
        if problems:
            print("[fail] 安装包未包含要求的文件:")
            for item in problems:
                print(f"  - {item}")
            _dump_log(log_path)
            return 1
    finally:
        shutil.rmtree(install_root, ignore_errors=True)
        log_path.unlink(missing_ok=True)

    print(f"[ok] {setup.name}: 程序入口、项目许可证、第三方归属均已打入安装包")
    return 0


if __name__ == "__main__":
    sys.exit(main())
