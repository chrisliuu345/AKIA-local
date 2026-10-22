"""Dependency-free MCP stdio service for a fixed, read-only AKIA dataset."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TextIO

from akia_sdk.client import SDK_API_VERSION, AKIAClient, SDKError, to_jsonable
from config.settings import APP_VERSION

SERVER_NAME = "AKIA Local Analysis"
MCP_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
MCP_LATEST_PROTOCOL = MCP_PROTOCOL_VERSIONS[0]
MAX_REQUEST_BYTES = 2 * 1024 * 1024
MCP_BLOCKED_TOOLS = frozenset({"ml_predict"})
SERVER_INSTRUCTIONS = (
    "AKIA exposes local, read-only industrial engineering and quality analysis. "
    "The dataset is fixed when the server starts. Call akia_list_tools to discover "
    "analysis tools, then akia_run_tool with a tool name and JSON parameters. "
    "No plugins are loaded and no file paths are accepted at call time."
)


def _is_path_parameter(name: str) -> bool:
    normalized = str(name or "").casefold()
    return normalized in {"path", "file", "model_path", "save_path"} \
        or normalized.endswith("_path")


def _contains_path_parameter(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_is_path_parameter(key) or _contains_path_parameter(item)
                   for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_path_parameter(item) for item in value)
    return False


def _mcp_safe_specs(client: AKIAClient) -> list[dict[str, Any]]:
    safe = []
    for spec in client.tool_specs():
        if spec["name"] in MCP_BLOCKED_TOOLS:
            continue
        if any(_is_path_parameter(name) for name in spec["parameters"]):
            continue
        safe.append(spec)
    return safe


def _envelope(kind: str, payload: dict[str, Any], *, ok: bool = True) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "sdk_api_version": SDK_API_VERSION,
        "app_version": APP_VERSION,
        "kind": kind,
        "ok": ok,
        **to_jsonable(payload),
    }


@dataclass(frozen=True)
class MCPTool:
    name: str
    title: str
    description: str
    schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], dict[str, Any]]

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.schema,
        }


class MCPService:
    """Minimal MCP tool server with no call-time filesystem access."""

    def __init__(self, client: AKIAClient):
        self.client = client
        self.safe_specs = _mcp_safe_specs(client)
        self.safe_tool_names = {spec["name"] for spec in self.safe_specs}
        self.tools: dict[str, MCPTool] = {}
        self._register_tools()

    def _register(self, name: str, title: str, description: str,
                  properties: dict[str, Any],
                  handler: Callable[[dict[str, Any]], dict[str, Any]],
                  required: list[str] | None = None) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            schema["required"] = required
        self.tools[name] = MCPTool(name, title, description, schema, handler)

    def _register_tools(self) -> None:
        self._register(
            "akia_list_tools",
            "List AKIA analysis tools",
            "List the read-only analysis tools and their parameters.",
            {"category": {"type": ["string", "null"]}},
            self._list_tools,
        )
        self._register(
            "akia_describe_data",
            "Describe loaded AKIA data",
            "Return a data profile and recommendations without raw rows.",
            {},
            self._describe_data,
        )
        self._register(
            "akia_run_tool",
            "Run an AKIA analysis tool",
            "Run one tool from akia_list_tools with a JSON parameter object.",
            {
                "tool": {"type": "string"},
                "params": {"type": ["object", "null"]},
            },
            self._run_tool,
            required=["tool"],
        )
        self._register(
            "akia_one_click",
            "Run the AKIA one-click analysis",
            "Profile the fixed dataset and run recommended or selected analyses.",
            {"selected": {"type": ["array", "null"],
                          "items": {"type": "string"}}},
            self._one_click,
        )
        self._register(
            "akia_server_info",
            "Describe the AKIA MCP server",
            "Return version, data source type, tool count, and safety settings.",
            {},
            self._server_info,
        )

    def _list_tools(self, arguments: dict[str, Any]) -> dict[str, Any]:
        category = arguments.get("category")
        tools = [
            spec for spec in self.safe_specs
            if not category or spec["category"] == str(category)
        ]
        return _envelope("tool_catalog", {"count": len(tools), "tools": tools})

    def _describe_data(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        return _envelope("profile", {"data": self.client.profile()})

    def _run_tool(self, arguments: dict[str, Any]) -> dict[str, Any]:
        name = str(arguments.get("tool") or "")
        raw_params = arguments.get("params")
        params = {} if raw_params is None else raw_params
        if name not in self.safe_tool_names:
            raise SDKError(f"工具 {name or '(未指定)'} 不允许通过 MCP 调用")
        if not isinstance(params, dict):
            raise SDKError("params 必须是对象")
        if _contains_path_parameter(params):
            raise SDKError("MCP 调用不接受文件或目录路径参数")
        result = self.client.run(
            name,
            params,
        )
        return result.as_dict()

    def _one_click(self, arguments: dict[str, Any]) -> dict[str, Any]:
        selected = arguments.get("selected")
        if selected is not None and not isinstance(selected, list):
            raise SDKError("selected 必须是字符串数组")
        data = self.client.one_click(
            [str(item) for item in selected] if selected else None)
        total = int(data.get("total_count", 0))
        success = int(data.get("success_count", 0))
        ok = total > 0 and total == success
        return _envelope("one_click", {"data": data}, ok=ok)

    def _server_info(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        source_kind = "project" if self.client.source.lower().endswith(".qap") else "data_file"
        return _envelope("server_info", {
            "name": SERVER_NAME,
            "app_version": APP_VERSION,
            "sdk_api_version": SDK_API_VERSION,
            "tool_count": len(self.safe_tool_names),
            "mcp_tool_count": len(self.tools),
            "source_kind": source_kind if self.client.source else "in_memory",
            "read_only": True,
            "plugins_enabled": False,
            "call_time_paths": False,
        })

    def handle(self, message: Any) -> dict[str, Any] | None:
        """Handle one decoded JSON-RPC message."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return _rpc_error(None, -32600, "Invalid Request")
        request_id = message.get("id")
        if "id" in message and not _valid_request_id(request_id):
            return _rpc_error(None, -32600, "Invalid Request")
        method = str(message.get("method") or "")
        is_notification = "id" not in message
        if is_notification:
            return None
        if not method:
            return _rpc_error(request_id, -32600, "Invalid Request")
        raw_params = message.get("params")
        params = {} if raw_params is None else raw_params
        if not isinstance(params, dict):
            return _rpc_error(request_id, -32602, "params 必须是对象")
        if method == "initialize":
            requested = str(params.get("protocolVersion") or "")
            version = (requested if requested in MCP_PROTOCOL_VERSIONS
                       else MCP_LATEST_PROTOCOL)
            return _rpc_result(request_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": APP_VERSION},
                "instructions": SERVER_INSTRUCTIONS,
            })
        if method == "ping":
            return _rpc_result(request_id, {})
        if method == "tools/list":
            return _rpc_result(request_id, {
                "tools": [tool.definition() for tool in self.tools.values()],
            })
        if method == "tools/call":
            return self._call(request_id, params)
        return _rpc_error(request_id, -32601, f"Method not found: {method}")

    def _call(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = str(params.get("name") or "")
        raw_arguments = params.get("arguments")
        arguments = {} if raw_arguments is None else raw_arguments
        if not isinstance(arguments, dict):
            return _rpc_error(request_id, -32602, "arguments 必须是对象")
        tool = self.tools.get(name)
        if tool is None:
            return _tool_error(request_id, f"Unknown tool: {name}")
        unknown = sorted(set(arguments) - set(tool.schema["properties"]))
        if unknown:
            return _rpc_error(
                request_id, -32602,
                f"Unknown arguments for {name}: {', '.join(unknown)}")
        missing = [key for key in tool.schema.get("required", [])
                   if key not in arguments]
        if missing:
            return _rpc_error(
                request_id, -32602,
                f"Missing required arguments for {name}: {', '.join(missing)}")
        try:
            payload = tool.handler(arguments)
        except (SDKError, ValueError, TypeError, OSError) as exc:
            return _tool_error(request_id, str(exc))
        except Exception as exc:  # noqa: BLE001 - MCP boundary isolates tool failures
            return _tool_error(request_id, f"{type(exc).__name__}: {exc}")
        return _rpc_result(request_id, {
            "content": [{"type": "text",
                         "text": json.dumps(payload, ensure_ascii=False,
                                            sort_keys=True, allow_nan=False)}],
            "isError": not bool(payload.get("ok", True)),
        })


def _rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": code, "message": message}}


def _tool_error(request_id: Any, message: str) -> dict[str, Any]:
    return _rpc_result(request_id, {
        "content": [{"type": "text", "text": message}],
        "isError": True,
    })


def _valid_request_id(value: Any) -> bool:
    if value is None or isinstance(value, str):
        return True
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"不支持非标准 JSON 常量: {value}")


def _parse_finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"JSON 数值必须有限: {value}")
    return number


def _parse_request(line: str) -> Any:
    if len(line.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise ValueError(f"请求超过 {MAX_REQUEST_BYTES} 字节")
    return json.loads(
        line,
        parse_constant=_reject_json_constant,
        parse_float=_parse_finite_float,
    )


def serve_stdio(service: MCPService, stdin: TextIO | None = None,
                stdout: TextIO | None = None) -> int:
    """Serve newline-delimited JSON-RPC until stdin closes."""
    source = stdin or sys.stdin
    target = stdout or sys.stdout
    for line in source:
        if not line.strip():
            continue
        try:
            message = _parse_request(line)
        except (json.JSONDecodeError, ValueError, RecursionError) as exc:
            response = _rpc_error(None, -32700, f"Parse error: {exc}")
        else:
            response = service.handle(message)
        if response is not None:
            try:
                output = json.dumps(response, ensure_ascii=False,
                                    sort_keys=True, allow_nan=False)
            except (TypeError, ValueError, RecursionError):
                output = json.dumps(
                    _rpc_error(None, -32603, "Internal error"),
                    ensure_ascii=False, sort_keys=True, allow_nan=False)
            target.write(output + "\n")
            target.flush()
    return 0


def create_server(client: AKIAClient) -> MCPService:
    """Compatibility name for callers that treat the service as a server."""
    return MCPService(client)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m akia_sdk.mcp",
        description="AKIA MCP stdio service",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="CSV or Excel data file")
    source.add_argument("--project", help="AKIA .qap project file")
    parser.add_argument("--sheet", action="append",
                        help="Load only the specified worksheet; repeatable")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        sheets = list(args.sheet or [])
        if args.project:
            client = AKIAClient.from_project(args.project, sheets=sheets)
        else:
            client = AKIAClient.from_file(args.input, sheets=sheets)
        service = create_server(client)
    except (SDKError, OSError) as exc:
        sys.stderr.write(f"AKIA MCP 启动失败: {exc}\n")
        return 2
    try:
        return serve_stdio(service)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
