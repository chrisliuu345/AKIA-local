#!/usr/bin/env python3
"""Check AKIA plugin manifests and capability methods without executing plugins."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def _print_report(report, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return
    state = "ok" if report.ok else "fail"
    print(f"[{state}] {report.plugin_dir}")
    for issue in report.issues:
        print(f"  {issue.level.upper():7} {issue.code}: {issue.message}")


def main(argv: list[str] | None = None) -> int:
    from config.settings import APP_VERSION
    from core.plugin_check import check_plugin_dir, discover_plugin_dirs

    parser = argparse.ArgumentParser(
        description="静态检查 AKIA 插件契约（不导入插件代码）")
    parser.add_argument("paths", nargs="+", help="插件目录或其父目录")
    parser.add_argument("--app-version", default=APP_VERSION,
                        help=f"兼容性检查目标主程序版本（默认 {APP_VERSION}）")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    reports = []
    for raw in args.paths:
        dirs = discover_plugin_dirs(raw)
        if not dirs:
            parser.error(f"未找到含 plugin.json 的插件目录: {raw}")
        reports.extend(check_plugin_dir(path, app_version=args.app_version)
                       for path in dirs)

    if args.json:
        print(json.dumps([report.as_dict() for report in reports],
                         ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for report in reports:
            _print_report(report, as_json=False)
        errors = sum(len(report.errors) for report in reports)
        warnings = sum(len(report.warnings) for report in reports)
        print(f"\n插件 {len(reports)} 个 · 错误 {errors} · 警告 {warnings}")
    return 1 if any(not report.ok for report in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
