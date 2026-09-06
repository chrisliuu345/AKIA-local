"""
build_nuitka.py — QA-Tool Nuitka 构建脚本（跨平台）

用法:
    python build_nuitka.py --onefile      # 单文件模式
    python build_nuitka.py --standalone   # 独立目录模式
    python build_nuitka.py --onefile --standalone  # 两者都构建
"""

import sys
import shutil
import subprocess
import argparse
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
ENTRY_POINT = PROJECT_DIR / "main.py"
ICON_PATH_WIN = PROJECT_DIR / "assets" / "logo.ico"
ICON_PATH_LINUX = PROJECT_DIR / "assets" / "logo.png"
VERSION_INFO = PROJECT_DIR / "version_info.txt"

APP_NAME = "QA-Tool"
APP_VERSION = "3.6.0"

BUILD_DIR = PROJECT_DIR / "build"
DIST_DIR = PROJECT_DIR / "dist"
NUITKA_BUILD_DIR = PROJECT_DIR / "build" / "nuitka_build"
NUITKA_DIST_DIR = PROJECT_DIR / "build" / "nuitka_dist"

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
    "test",
    "unittest",
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.Qt3D",
]


def clean_old_dirs():
    """清理旧的构建目录"""
    dirs_to_clean = [
        BUILD_DIR / "QA-Tool.build",
        BUILD_DIR / "QA-Tool.dist",
        NUITKA_BUILD_DIR,
        NUITKA_DIST_DIR,
    ]
    for d in dirs_to_clean:
        if d.exists():
            print("[clean] 删除目录: " + str(d))
            shutil.rmtree(d, ignore_errors=True)

    for spec in PROJECT_DIR.glob("*.spec"):
        print("[clean] 删除文件: " + str(spec))
        spec.unlink(missing_ok=True)

    if DIST_DIR.exists():
        for f in DIST_DIR.glob("QA-Tool*"):
            print("[clean] 删除文件: " + str(f))
            f.unlink(missing_ok=True)


def build_nuitka(mode):
    """
    执行 Nuitka 构建

    Args:
        mode: "onefile", "standalone", 或 "both"
    """
    if mode == "both":
        build_nuitka("standalone")
        build_nuitka("onefile")
        return

    print("\n" + "=" * 60)
    print("  Nuitka 构建 — 模式: " + mode)
    print("  平台: " + sys.platform)
    print("=" * 60 + "\n")

    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--output-dir=" + str(BUILD_DIR),
        "--output-filename=" + APP_NAME,
    ]

    if mode == "onefile":
        cmd.append("--onefile")

    cmd.append("--enable-plugin=pyside6")

    if sys.platform == "win32":
        cmd.append("--windows-console-mode=disable")
        
        if ICON_PATH_WIN.exists():
            cmd.append("--windows-icon-from-ico=" + str(ICON_PATH_WIN))
        
        cmd.append("--windows-company-name=QA-Tool")
        cmd.append("--windows-product-name=QA-Tool")
        cmd.append("--windows-file-version=" + APP_VERSION)
        cmd.append("--windows-product-version=" + APP_VERSION)
        cmd.append("--windows-file-description=QA-Tool Quality Analysis Tool")
    
    elif sys.platform == "linux":
        if ICON_PATH_LINUX.exists():
            cmd.append("--linux-icon=" + str(ICON_PATH_LINUX))
    
    elif sys.platform == "darwin":
        if ICON_PATH_LINUX.exists():
            cmd.append("--macos-create-app-bundle")
            cmd.append("--macos-app-icon=" + str(ICON_PATH_LINUX))

    for src_rel, dest_rel in DATA_DIRS:
        src_abs = str(PROJECT_DIR / src_rel)
        include_opt = "--include-data-dir=" + src_abs + "=" + dest_rel
        cmd.append(include_opt)

    for src_rel, dest_rel in DATA_FILES:
        src_abs = str(PROJECT_DIR / src_rel)
        include_opt = "--include-data-file=" + src_abs + "=" + dest_rel
        cmd.append(include_opt)

    for imp in HIDDEN_IMPORTS:
        cmd.append("--include-module=" + imp)

    for excl in EXCLUDES:
        cmd.append("--nofollow-import-to=" + excl)

    cmd.append("--assume-yes-for-downloads")
    cmd.append("--remove-output")

    cmd.append(str(ENTRY_POINT))

    print("[cmd] 构建命令:")
    cmd_display = " \\\n  ".join(cmd)
    print("  " + cmd_display + "\n")

    print("[build] 开始构建，请耐心等待...\n")
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_DIR),
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print("\n[error] 构建失败! 返回码: " + str(result.returncode))
        sys.exit(result.returncode)

    report_output(mode)


def report_output(mode):
    """查找构建输出并报告路径与大小"""
    if mode == "onefile":
        candidates = list(DIST_DIR.glob("QA-Tool*"))
        if not candidates:
            candidates = list(BUILD_DIR.glob("QA-Tool*"))
    else:
        candidates = list(BUILD_DIR.glob("QA-Tool*"))

    if not candidates:
        print("\n[warn] 未找到构建输出文件")
        return

    print("\n" + "=" * 60)
    print("  构建成功!")
    print("=" * 60)

    for path in candidates:
        if path.is_file():
            size_bytes = path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            print("\n  输出文件: " + str(path))
            print("  文件大小: " + "{:.1f}".format(size_mb) + " MB")
        elif path.is_dir():
            print("\n  输出目录: " + str(path))
            total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            size_mb = total / (1024 * 1024)
            print("  目录大小: " + "{:.1f}".format(size_mb) + " MB")

    print("")


def main():
    parser = argparse.ArgumentParser(
        description="QA-Tool Nuitka 构建脚本（跨平台）",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="构建单文件可执行程序",
    )
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="构建独立目录的可执行程序",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="仅清理旧构建目录，不执行构建",
    )

    args = parser.parse_args()

    if not ENTRY_POINT.exists():
        print("[error] 入口文件不存在: " + str(ENTRY_POINT))
        sys.exit(1)

    if sys.platform == "win32" and not ICON_PATH_WIN.exists():
        print("[warn] 图标文件不存在: " + str(ICON_PATH_WIN) + "，将不使用自定义图标")
    elif sys.platform == "linux" and not ICON_PATH_LINUX.exists():
        print("[warn] 图标文件不存在: " + str(ICON_PATH_LINUX) + "，将不使用自定义图标")

    print("[clean] 清理旧构建目录...")
    clean_old_dirs()

    if args.clean_only:
        print("[done] 清理完成")
        return

    if args.onefile and args.standalone:
        mode = "both"
    elif args.onefile:
        mode = "onefile"
    elif args.standalone:
        mode = "standalone"
    else:
        print("[error] 请指定构建模式: --onefile 或 --standalone")
        print("  用法: python build_nuitka.py --onefile")
        print("        python build_nuitka.py --standalone")
        print("        python build_nuitka.py --onefile --standalone")
        sys.exit(1)

    build_nuitka(mode)


if __name__ == "__main__":
    main()
