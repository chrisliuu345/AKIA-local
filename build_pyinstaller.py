"""
build_pyinstaller.py — QA-Tool PyInstaller 构建脚本（跨平台, onedir 默认）

用法:
    python build_pyinstaller.py                # onedir 独立目录模式(默认)
    python build_pyinstaller.py --onefile      # 单文件模式
    python build_pyinstaller.py --name qa-tool # 自定义产物名(Linux 用 qa-tool)

产物布局:
    onedir  → build/<name>.dist/<name>[.exe] + _internal/   (供 .iss / AppImage / deb 使用)
    onefile → dist/<name>[.exe]
"""

import sys
import os
import shutil
import subprocess
import argparse
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
ENTRY_POINT = PROJECT_DIR / "main.py"
ICON_PATH_WIN = PROJECT_DIR / "assets" / "logo.ico"
ICON_PATH_LINUX = PROJECT_DIR / "assets" / "logo.png"
VERSION_INFO = PROJECT_DIR / "version_info.txt"

APP_VERSION = "3.6.0"

BUILD_DIR = PROJECT_DIR / "build"
DIST_DIR = PROJECT_DIR / "dist"
WORK_DIR = BUILD_DIR / "pyi_work"

# 目录类数据: (源相对路径, 目标相对路径) — 落于 _internal/ 下, 与
# config/settings.py 基于 __file__ 的路径解析一致
DATA_DIRS = [
    ("config/knowledge", "config/knowledge"),
    ("config/templates", "config/templates"),
    ("config/help", "config/help"),
    ("locales", "locales"),
    ("plugins", "plugins"),
]

DATA_FILES = [
    ("logo.png", "logo.png"),
    ("user_config.json", "user_config.json"),
]

HIDDEN_IMPORTS = [
    "matplotlib.backends.backend_qtagg",
    "seaborn",
    "scipy.stats._morestats",
    "scipy.special._ufuncs_cxx",
    "openpyxl.cell._writer",
    "reportlab.pdfbase.ttfonts",
    "reportlab.pdfbase.cidfonts",
    "PIL",
    "PIL.Image",
    "core.anti_debug",
    "core.integrity",
]

EXCLUDES = [
    "tkinter",
    "unittest",
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.Qt3D",
]


def clean_old_dirs(name: str):
    for d in (BUILD_DIR / f"{name}.dist", BUILD_DIR / f"{name}.build", WORK_DIR):
        if d.exists():
            print(f"[clean] 删除目录: {d}")
            shutil.rmtree(d, ignore_errors=True)
    if DIST_DIR.exists():
        for f in DIST_DIR.glob(f"{name}*"):
            if f.is_file():
                print(f"[clean] 删除文件: {f}")
                f.unlink(missing_ok=True)


def build(name: str, onefile: bool):
    print("\n" + "=" * 60)
    print(f"  PyInstaller 构建 — 模式: {'onefile' if onefile else 'onedir'}")
    print(f"  平台: {sys.platform}  名称: {name}")
    print("=" * 60 + "\n")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", name,
        "--distpath", str(BUILD_DIR),
        "--workpath", str(WORK_DIR),
        "--specpath", str(BUILD_DIR),
    ]

    if onefile:
        cmd.append("--onefile")

    if sys.platform == "win32":
        cmd.append("--noconsole")
        if ICON_PATH_WIN.exists():
            cmd.append("--icon")
            cmd.append(str(ICON_PATH_WIN))
        if VERSION_INFO.exists():
            cmd.append("--version-file")
            cmd.append(str(VERSION_INFO))
    else:
        if ICON_PATH_LINUX.exists():
            cmd.append("--icon")
            cmd.append(str(ICON_PATH_LINUX))

    for src_rel, dest_rel in DATA_DIRS + DATA_FILES:
        cmd.append("--add-data")
        cmd.append(f"{str(PROJECT_DIR / src_rel)}{os.pathsep}{dest_rel}")

    for imp in HIDDEN_IMPORTS:
        cmd.append("--hidden-import")
        cmd.append(imp)

    for excl in EXCLUDES:
        cmd.append("--exclude-module")
        cmd.append(excl)

    cmd.append(str(ENTRY_POINT))

    print("[cmd] 构建命令:")
    print("  " + " \\\n  ".join(cmd) + "\n")
    print("[build] 开始构建，请耐心等待...\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_DIR))
    if result.returncode != 0:
        print(f"\n[error] 构建失败! 返回码: {result.returncode}")
        sys.exit(result.returncode)

    if onefile:
        candidates = list(DIST_DIR.glob(f"{name}*")) or list(BUILD_DIR.glob(f"{name}*"))
        _report(candidates)
        return

    # onedir: PyInstaller 输出为 build/<name>/ → 上移为 build/<name>.dist/
    src_dir = BUILD_DIR / name
    if not src_dir.is_dir():
        print(f"[error] 未找到构建输出目录: {src_dir}")
        sys.exit(1)
    final_dir = BUILD_DIR / f"{name}.dist"
    if final_dir.exists():
        shutil.rmtree(final_dir, ignore_errors=True)
    shutil.move(str(src_dir), str(final_dir))
    print(f"[done] onedir 产物整理为: {final_dir}")
    _report([final_dir])


def _report(paths):
    print("\n" + "=" * 60)
    print("  构建成功!")
    print("=" * 60)
    for path in paths:
        if path.is_dir():
            total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            print(f"\n  输出目录: {path}")
            print(f"  目录大小: {total / (1024 * 1024):.1f} MB")
        elif path.is_file():
            print(f"\n  输出文件: {path}")
            print(f"  文件大小: {path.stat().st_size / (1024 * 1024):.1f} MB")
    print("")


def main():
    parser = argparse.ArgumentParser(
        description="QA-Tool PyInstaller 构建脚本（跨平台, onedir 默认）",
    )
    parser.add_argument("--onefile", action="store_true", help="构建单文件可执行程序")
    parser.add_argument("--name", default=None,
                        help="产物名称 (默认: Windows QA-Tool / 其他 qa-tool)")
    parser.add_argument("--clean-only", action="store_true", help="仅清理旧构建目录")

    args = parser.parse_args()
    name = args.name or ("QA-Tool" if sys.platform == "win32" else "qa-tool")

    if not ENTRY_POINT.exists():
        print(f"[error] 入口文件不存在: {ENTRY_POINT}")
        sys.exit(1)

    print("[clean] 清理旧构建目录...")
    clean_old_dirs(name)
    if args.clean_only:
        print("[done] 清理完成")
        return

    build(name, onefile=args.onefile)


if __name__ == "__main__":
    main()
