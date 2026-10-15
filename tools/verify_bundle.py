#!/usr/bin/env python3
"""打包产物完整性校验（v4.4.0 审查修复）— 动态导入模块必须随包分发。

背景：``ui/_tab_registry.py``（Tab 懒加载）与 ``connectors/registry.py``
（连接器插件发现）使用 importlib 动态导入，PyInstaller 无法静态跟踪。
2026-10-15 审查实测：v4.2.0–v4.4.0 全部 AppImage 与 Windows onedir 构建
均缺失 ``ui.tabs.*`` 与 ``connectors.plugins.*``——打包版所有 Tab 与连接器
插件不可用（源码运行与 CI 全绿均无感知）。本工具在构建收尾阶段核验归档
内容，缺失即失败（build_pyinstaller.py 已接线）。

用法:
    python tools/verify_bundle.py --dist build/akia.dist/akia       # Linux onedir
    python tools/verify_bundle.py --dist build/AKIA.dist/AKIA.exe   # Windows onedir
    python tools/verify_bundle.py --dist dist/akia                  # onefile

退出码: 0 = 全部模块在包内；1 = 有缺失（列出清单）；2 = 用法/环境错误。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def required_modules() -> set[str]:
    """必须随包分发的动态导入模块（单一事实源 = 业务注册表本身）。"""
    from ui._tab_registry import TAB_REGISTRY
    from connectors.registry import _candidate_stems

    required = {"ui.tabs", "connectors.plugins"}
    required |= {str(entry[3]) for entry in TAB_REGISTRY}
    required |= {f"connectors.plugins.{stem}" for stem in _candidate_stems()}
    return required


def frozen_modules(executable: Path) -> set[str]:
    """读取冻结产物内的模块名集合（CArchive + 内嵌 PYZ 归档）。"""
    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

    if executable.suffix.lower() == ".pyz":
        return set(ZlibArchiveReader(str(executable)).toc)

    reader = CArchiveReader(str(executable))
    names: set[str] = set()
    for name, entry in reader.toc.items():
        typecode = entry[4] if isinstance(entry, tuple) and len(entry) >= 5 else ""
        if typecode == "z":                       # 内嵌 PYZ（纯 Python 模块）
            names |= set(reader.open_embedded_archive(name).toc)
        elif typecode in ("m", "M", "s", "S"):    # 顶层脚本 / 扩展模块
            names.add(name)
    return names


def default_target() -> Path | None:
    candidates = [
        ROOT / "build" / "akia.dist" / "akia",
        ROOT / "build" / "AKIA.dist" / "AKIA.exe",
        ROOT / "dist" / "akia",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验打包产物包含全部动态导入模块")
    parser.add_argument("--dist", default=None,
                        help="打包产物可执行文件路径（onedir/onefile 均可）")
    args = parser.parse_args(argv)

    target = Path(args.dist) if args.dist else default_target()
    if target is None or not target.is_file():
        print(f"[error] 未找到打包产物: {target or '(自动探测失败)'}")
        return 2

    try:
        required = required_modules()
        present = frozen_modules(target)
    except ImportError as exc:
        print(f"[error] 校验环境不完整（需要 PyInstaller）: {exc}")
        return 2

    missing = sorted(required - present)
    if missing:
        print(f"[fail] {target.name} 缺失 {len(missing)} 个动态导入模块:")
        for name in missing:
            print(f"  - {name}")
        print("提示: 检查 build_pyinstaller.py 的 COLLECT_SUBMODULES "
              "（ui.tabs / connectors.plugins）。")
        return 1

    print(f"[ok] {target.name}: {len(required)} 个动态导入模块全部在包内"
          f"（共 {len(present)} 个冻结模块）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
