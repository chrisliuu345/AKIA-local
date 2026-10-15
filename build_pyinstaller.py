"""
build_pyinstaller.py — AKIA PyInstaller 构建脚本（跨平台, onedir 默认）

用法:
    python build_pyinstaller.py                # onedir 独立目录模式(默认)
    python build_pyinstaller.py --onefile      # 单文件模式
    python build_pyinstaller.py --name akia # 自定义产物名(Linux 用 akia)

产物布局:
    onedir  → build/<name>.dist/<name>[.exe] + _internal/   (供 .iss / AppImage 使用)
    onefile → dist/<name>[.exe]
"""

import sys
import os
import re
import shutil
import subprocess
import argparse
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
ENTRY_POINT = PROJECT_DIR / "main.py"
ICON_PATH_WIN = PROJECT_DIR / "assets" / "logo.ico"
ICON_PATH_LINUX = PROJECT_DIR / "assets" / "logo.png"

BUILD_DIR = PROJECT_DIR / "build"
DIST_DIR = PROJECT_DIR / "dist"
WORK_DIR = BUILD_DIR / "pyi_work"

# APP_VERSION 单一事实源：config/settings.py
sys.path.insert(0, str(PROJECT_DIR))
from config.settings import APP_VERSION  # noqa: E402

GENERATED_VERSION_INFO = BUILD_DIR / "version_info.generated.txt"

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
    # 注意: --add-data 的目标一律按"目录"处理，写成同名文件名会生成
    # _internal/logo.png/logo.png（冻结版按 __file__ 解析路径时读到目录，
    # logo 与默认配置都会静默丢失）。目标写 "." 才会落到 _internal/ 根下。
    ("logo.png", "."),
    # 仅打包公共默认配置；本机 user_config.json（可能含设备列表/告警密码）
    # 严禁进入安装包，运行时由 config.settings 叠加用户文件
    ("user_config.default.json", "."),
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
]

#: 动态导入包的子模块收集（不写会造成打包产物缺失模块）：
#: PyInstaller 只能静态跟踪字面量 import，而以下包经 importlib 动态加载——
#: ui/_tab_registry.py 的 Tab 懒加载（import_module(module_path)）与
#: connectors/registry.py 的插件发现（f"connectors.plugins.{stem}"）。
#: 2026-10-15 审查实测：v4.2.0–v4.4.0 全部 AppImage 与 Windows onedir 构建
#: 均缺失这两个包，打包版所有 Tab / 连接器插件不可用（源码运行无感知）。
COLLECT_SUBMODULES = [
    "ui.tabs",
    "connectors.plugins",
]

EXCLUDES = [
    "tkinter",
    # 注意: 不可排除 unittest —— matplotlib → pyparsing(≥3.3) 的
    # __init__ 会导入 pyparsing.testing，后者依赖 unittest；排除后
    # 打包产物启动即 ModuleNotFoundError（v3.8.0 打包冒烟发现）
    "pytest",
    "IPython",
    "jupyter",
    "notebook",
    "PySide6.QtQuick",
    "PySide6.QtQml",
    "PySide6.Qt3D",
    # 外部插件依赖（如独立项目 AKIA-Vision-expansion 的 opencv/mediapipe，
    # 体积约 200MB）：主应用不内置视觉能力，默认不打包，插件按需在运行环境安装。
    "cv2",
    "mediapipe",
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


def write_version_file(version: str) -> Path:
    """从 APP_VERSION 生成 Windows 版本资源文件（避免与静态文件漂移）"""
    numbers = [int(n) for n in re.findall(r"\d+", version)[:4]]
    numbers += [0] * (4 - len(numbers))
    tuple_text = ", ".join(str(n) for n in numbers)
    GENERATED_VERSION_INFO.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_VERSION_INFO.write_text(
        f"""# UTF-8 (auto-generated from config.settings.APP_VERSION={version})
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({tuple_text}),
    prodvers=({tuple_text}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'080404b0',
        [
          StringStruct(u'CompanyName', u'AKIM'),
          StringStruct(u'FileDescription', u'AKIA · AKIM IE/Quality analyzer-local'),
          StringStruct(u'FileVersion', u'{version}'),
          StringStruct(u'InternalName', u'AKIA'),
          StringStruct(u'LegalCopyright', u'Copyright \\u00a9 2026 AKIM'),
          StringStruct(u'OriginalFilename', u'AKIA.exe'),
          StringStruct(u'ProductName', u'AKIA'),
          StringStruct(u'ProductVersion', u'{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return GENERATED_VERSION_INFO


def build(name: str, onefile: bool):
    print("\n" + "=" * 60)
    print(f"  PyInstaller 构建 — 模式: {'onefile' if onefile else 'onedir'}")
    print(f"  平台: {sys.platform}  名称: {name}  版本: {APP_VERSION}")
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
        version_file = write_version_file(APP_VERSION)
        cmd.append("--version-file")
        cmd.append(str(version_file))
    else:
        if ICON_PATH_LINUX.exists():
            cmd.append("--icon")
            cmd.append(str(ICON_PATH_LINUX))

    for src_rel, dest_rel in DATA_DIRS + DATA_FILES:
        cmd.append("--add-data")
        cmd.append(f"{PROJECT_DIR / src_rel!s}{os.pathsep}{dest_rel}")

    for imp in HIDDEN_IMPORTS:
        cmd.append("--hidden-import")
        cmd.append(imp)

    for pkg in COLLECT_SUBMODULES:
        cmd.append("--collect-submodules")
        cmd.append(pkg)

    for excl in EXCLUDES:
        cmd.append("--exclude-module")
        cmd.append(excl)

    cmd.append(str(ENTRY_POINT))

    print("[cmd] 构建命令:")
    print("  " + " \\\n  ".join(cmd) + "\n")
    print("[build] 开始构建，请耐心等待...\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_DIR), check=False)
    if result.returncode != 0:
        print(f"\n[error] 构建失败! 返回码: {result.returncode}")
        sys.exit(result.returncode)

    if onefile:
        candidates = list(DIST_DIR.glob(f"{name}*")) or list(BUILD_DIR.glob(f"{name}*"))
        if candidates:
            verify_bundle(candidates[0])
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
    verify_bundle(final_dir / (f"{name}.exe" if sys.platform == "win32" else name))
    _report([final_dir])


def verify_bundle(executable: Path) -> None:
    """构建收尾自检：动态导入模块（Tab / 连接器插件）必须已进入打包产物。

    缺失即中止构建——防止"源码全绿、打包产物缺模块"再次发生。
    """
    if not executable.exists():
        print(f"\n[warn] 未找到打包产物可执行文件，跳过产物校验: {executable}")
        return
    cmd = [sys.executable, str(PROJECT_DIR / "tools" / "verify_bundle.py"),
           "--dist", str(executable)]
    result = subprocess.run(cmd, cwd=str(PROJECT_DIR), check=False)
    if result.returncode != 0:
        print(f"\n[error] 打包产物完整性校验失败（返回码 {result.returncode}）："
              "动态导入模块缺失，产物不可发布！")
        sys.exit(result.returncode)


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
    print()


def main():
    parser = argparse.ArgumentParser(
        description="AKIA PyInstaller 构建脚本（跨平台, onedir 默认）",
    )
    parser.add_argument("--onefile", action="store_true", help="构建单文件可执行程序")
    parser.add_argument("--name", default=None,
                        help="产物名称 (默认: Windows AKIA / 其他 akia)")
    parser.add_argument("--clean-only", action="store_true", help="仅清理旧构建目录")

    args = parser.parse_args()
    name = args.name or ("AKIA" if sys.platform == "win32" else "akia")

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
