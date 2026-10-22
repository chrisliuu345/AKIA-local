"""Command-line interface for the AKIA headless SDK."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from akia_sdk.client import (
    OUTPUT_SCHEMA_VERSION,
    SDK_API_VERSION,
    AKIAClient,
    OutputError,
    SDKError,
    to_jsonable,
)
from config.settings import APP_VERSION
from core.rule_pack import RulePack


def _json_text(payload: Any, pretty: bool) -> str:
    return json.dumps(
        to_jsonable(payload),
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=True,
        allow_nan=False,
    )


def _write_output(payload: Any, output: str, *, pretty: bool,
                  force: bool = False) -> None:
    text = _json_text(payload, pretty) + "\n"
    if output == "-":
        sys.stdout.write(text)
        return
    target = Path(output).expanduser()
    if target.exists() and not force:
        raise OutputError(f"输出文件已存在: {target}（使用 --force 覆盖）")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = ""
    try:
        with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=target.parent,
                prefix=f".{target.name}.", suffix=".tmp", delete=False) as handle:
            handle.write(text)
            temporary = handle.name
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            with contextlib.suppress(OSError):
                os.unlink(temporary)


def _error_payload(exc: Exception) -> dict[str, Any]:
    code = getattr(exc, "code", "sdk_error")
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "sdk_api_version": SDK_API_VERSION,
        "app_version": APP_VERSION,
        "ok": False,
        "error": {"code": code, "message": str(exc)},
    }


def _parse_params(args) -> dict[str, Any]:
    if args.params_file:
        try:
            text = Path(args.params_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise SDKError(f"读取参数文件失败: {exc}") from exc
    else:
        text = args.params
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise SDKError(f"参数不是合法 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SDKError("--params 必须是 JSON 对象")
    return payload


def _parse_local_json(text: str, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise SDKError(f"{label} 不是合法 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SDKError(f"{label} 必须是 JSON 对象")
    return payload


def _load_client(args) -> AKIAClient:
    sheets = list(args.sheet or [])
    if args.project:
        return AKIAClient.from_project(args.project, sheets=sheets)
    return AKIAClient.from_file(args.input, sheets=sheets)


def _source_group(parser: argparse.ArgumentParser) -> None:
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="CSV 或 Excel 数据文件")
    source.add_argument("--project", help="AKIA .qap 项目文件")
    parser.add_argument("--sheet", action="append",
                        help="仅加载指定工作表；可重复")


def _output_group(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", default="-",
                        help="JSON 输出路径；默认 - 为标准输出")
    parser.add_argument("--force", action="store_true",
                        help="允许覆盖已存在的输出文件")
    parser.add_argument("--pretty", action="store_true", help="缩进输出 JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m akia_sdk",
        description="AKIA 无界面分析与自动化接口",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"akia-sdk {SDK_API_VERSION} (AKIA {APP_VERSION})",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    tools = commands.add_parser("tools", help="列出可用分析工具")
    tools.add_argument("--category", help="仅列出指定类别")
    _output_group(tools)

    run = commands.add_parser("run", help="运行单个分析工具")
    _source_group(run)
    run.add_argument("--tool", required=True, help="工具名，例如 run_capability")
    params = run.add_mutually_exclusive_group()
    params.add_argument("--params", default="{}", help="JSON 参数对象")
    params.add_argument("--params-file", help="从 JSON 文件读取参数")
    _output_group(run)

    profile = commands.add_parser("profile", help="生成数据画像与推荐")
    _source_group(profile)
    _output_group(profile)

    one_click = commands.add_parser("one-click", help="执行一键分析")
    _source_group(one_click)
    one_click.add_argument(
        "--select",
        help="逗号分隔的分析类型（spc,capability,msa,hypothesis,regression,doe,chart）",
    )
    _output_group(one_click)

    rules_validate = commands.add_parser("rules-validate", help="校验规则包")
    rules_validate.add_argument("--pack", required=True, help="规则包 JSON 文件")
    _output_group(rules_validate)

    rules_evaluate = commands.add_parser("rules-evaluate", help="按指标评估规则包")
    rules_evaluate.add_argument("--pack", required=True, help="规则包 JSON 文件")
    metrics = rules_evaluate.add_mutually_exclusive_group(required=True)
    metrics.add_argument("--metrics", help="指标 JSON 对象")
    metrics.add_argument("--metrics-file", help="从 JSON 文件读取指标")
    _output_group(rules_evaluate)
    return parser


def _dispatch(args) -> tuple[dict[str, Any], int]:
    common = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "sdk_api_version": SDK_API_VERSION,
        "app_version": APP_VERSION,
    }
    if args.command == "tools":
        client = AKIAClient({})
        specs = client.tool_specs(args.category)
        return {**common, "ok": True, "kind": "tool_catalog",
                "count": len(specs), "tools": specs}, 0
    if args.command == "rules-validate":
        try:
            pack = RulePack.load(args.pack)
        except (OSError, ValueError, TypeError) as exc:
            raise SDKError(f"规则包校验失败: {exc}") from exc
        return {**common, "ok": True, "kind": "rule_pack",
                "rule_count": len(pack.rules), "pack": pack.to_dict()}, 0
    if args.command == "rules-evaluate":
        try:
            pack = RulePack.load(args.pack)
            if args.metrics_file:
                text = Path(args.metrics_file).read_text(encoding="utf-8")
            else:
                text = args.metrics
            metrics = _parse_local_json(text, "--metrics")
            evaluation = pack.evaluate(metrics)
        except (OSError, ValueError, TypeError) as exc:
            raise SDKError(f"规则包评估失败: {exc}") from exc
        return {**common, **evaluation, "kind": "rule_evaluation"}, (
            0 if evaluation["ok"] else 1)

    client = _load_client(args)
    if args.command == "profile":
        return {**common, "ok": True, "kind": "profile",
                "source": client.source, "data": client.profile()}, 0
    if args.command == "one-click":
        selected = [item.strip() for item in str(args.select or "").split(",")
                    if item.strip()] or None
        data = client.one_click(selected)
        total = int(data.get("total_count", 0))
        success = int(data.get("success_count", 0))
        ok = total > 0 and total == success
        return {**common, "ok": ok, "kind": "one_click",
                "source": client.source, "data": data}, 0 if ok else 1

    result = client.run(args.tool, _parse_params(args))
    payload = {**result.as_dict(), "source": client.source}
    return payload, 0 if result.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload, exit_code = _dispatch(args)
    except (SDKError, OSError) as exc:
        sys.stderr.write(_json_text(_error_payload(exc), args.pretty) + "\n")
        return 2
    try:
        _write_output(payload, args.output, pretty=args.pretty, force=args.force)
    except (SDKError, OSError) as exc:
        sys.stderr.write(_json_text(_error_payload(exc), args.pretty) + "\n")
        return 2
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
