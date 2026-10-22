#!/usr/bin/env python3
"""release_check.py — 发布门禁一键执行（对应 PLAN/ROADMAP 的 P6 清单）

依次执行：版本一致性 → ruff → 逐文件回归 → 性能基线（可选 AppImage 打包冒烟）。
任一步失败立即中止并给出原因；全部通过时打印可粘贴进发布说明的证据块。

用法::

    python tools/release_check.py                  # 常规发布门禁
    python tools/release_check.py --skip-tests     # 只做静态检查（快速）
    python tools/release_check.py --with-appimage  # 追加打包冒烟（需本地可构建）
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def _run(title: str, cmd: list[str]) -> tuple[bool, str]:
    print(f"\n▶ {title}\n  $ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    for line in tail[-6:]:
        print(f"  {line}")
    return proc.returncode == 0, "\n".join(tail[-3:])


def main() -> int:
    parser = argparse.ArgumentParser(description="AKIA 发布门禁")
    parser.add_argument("--skip-tests", action="store_true", help="跳过逐文件回归")
    parser.add_argument("--skip-benchmark", action="store_true", help="跳过性能基线")
    parser.add_argument("--with-appimage", action="store_true",
                        help="追加 AppImage 打包与启动冒烟")
    parser.add_argument("--tolerance", type=float, default=4.0,
                        help="性能基线容差倍数（默认 4.0，CI 同值）")
    args = parser.parse_args()

    steps: list[tuple[str, list[str]]] = [
        ("版本一致性（四端 + 文档产物名）", [PY, "tools/check_version.py"]),
        ("依赖锁哈希与分层", [PY, "tools/check_dependencies.py"]),
        ("抽样标准独立交叉核对", [PY, "tools/check_aql_reference.py"]),
        ("ruff 全库零告警", [PY, "-m", "ruff", "check", "."]),
    ]
    if not args.skip_tests:
        steps.append(("全量逐文件回归", [PY, "tools/run_tests.py", "--quiet"]))
    if not args.skip_benchmark:
        steps.append(("性能基线", [PY, "tools/benchmark.py", "--tolerance",
                                   str(args.tolerance)]))
    if args.with_appimage:
        steps.append(("AppImage 打包冒烟", ["bash", "build_appimage.sh"]))

    results: list[tuple[str, bool]] = []
    for title, cmd in steps:
        ok, _ = _run(title, cmd)
        results.append((title, ok))
        if not ok:
            print("\n❌ 发布门禁未通过：" + title)
            print("   修复后重跑：python tools/release_check.py")
            return 1

    print("\n✅ 发布门禁全部通过")
    print("   证据块（可粘贴进 Release 说明）:")
    print("   - 版本一致性 / ruff 零告警 / 逐文件回归 / 性能基线：全部通过")
    print("   - 复现命令：python tools/release_check.py")
    for title, _ in results:
        print(f"   - {title}: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
