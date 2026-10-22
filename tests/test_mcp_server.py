"""AKIA MCP stdio protocol integration tests."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from akia_sdk.client import AKIAClient
from akia_sdk.mcp import MCPService, serve_stdio

ROOT = Path(__file__).resolve().parent.parent


def _frame() -> pd.DataFrame:
    rng = np.random.default_rng(22)
    values = rng.normal(20.0, 0.1, 40)
    return pd.DataFrame({
        "直径": values,
        "USL": [20.4] * len(values),
        "LSL": [19.6] * len(values),
    })


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["MPLBACKEND"] = "Agg"
    env["PYTHONPATH"] = str(ROOT)
    return env


def _request(process: subprocess.Popen, message: dict) -> dict:
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    line = process.stdout.readline()
    assert line, process.stderr.read() if process.stderr else "no response"
    return json.loads(line)


def test_mcp_service_protocol_contract():
    service = MCPService(AKIAClient.from_dataframes({"Sheet1": _frame()}))
    initialized = service.handle({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    })
    assert initialized["result"]["serverInfo"]["name"] == "AKIA Local Analysis"
    assert "tools" in initialized["result"]["capabilities"]

    listed = service.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert {tool["name"] for tool in listed["result"]["tools"]} >= {
        "akia_list_tools", "akia_describe_data", "akia_run_tool",
        "akia_one_click", "akia_server_info",
    }

    ignored = service.handle({
        "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
    })
    assert ignored is None

    unknown = service.handle({
        "jsonrpc": "2.0", "id": 3, "method": "unknown/method",
    })
    assert unknown["error"]["code"] == -32601

    bad_arguments = service.handle({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "akia_run_tool", "arguments": {"tool": "x", "extra": 1}},
    })
    assert bad_arguments["error"]["code"] == -32602

    bad_params = service.handle({
        "jsonrpc": "2.0", "id": 5, "method": "ping", "params": [],
    })
    assert bad_params["error"]["code"] == -32602

    catalog = service.handle({
        "jsonrpc": "2.0", "id": 6, "method": "tools/call",
        "params": {"name": "akia_list_tools", "arguments": {}},
    })
    catalog_data = json.loads(catalog["result"]["content"][0]["text"])
    assert "ml_predict" not in {tool["name"] for tool in catalog_data["tools"]}

    blocked = service.handle({
        "jsonrpc": "2.0", "id": 7, "method": "tools/call",
        "params": {
            "name": "akia_run_tool",
            "arguments": {
                "tool": "ml_predict",
                "params": {"model_path": "/tmp/untrusted.qamodel"},
            },
        },
    })
    assert blocked["result"]["isError"] is True
    assert "不允许" in blocked["result"]["content"][0]["text"]


def test_mcp_stdio_catalog_and_analysis(tmp_path):
    data_path = tmp_path / "data.csv"
    _frame().to_csv(data_path, index=False)
    process = subprocess.Popen(
        [sys.executable, "-m", "akia_sdk.mcp", "--input", str(data_path)],
        cwd=ROOT,
        env=_env(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        initialized = _request(process, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1"},
            },
        })
        assert initialized["result"]["serverInfo"]["name"] == "AKIA Local Analysis"

        assert process.stdin is not None
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0", "method": "notifications/initialized", "params": {},
        }) + "\n")
        process.stdin.flush()

        catalog = _request(process, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {
                "name": "akia_list_tools",
                "arguments": {"category": "质量分析"},
            },
        })
        assert catalog["result"]["isError"] is False
        catalog_data = json.loads(catalog["result"]["content"][0]["text"])
        assert catalog_data["ok"] is True
        assert catalog_data["count"] >= 1

        result = _request(process, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {
                "name": "akia_run_tool",
                "arguments": {
                    "tool": "run_capability",
                    "params": {"column": "直径"},
                },
            },
        })
        assert result["result"]["isError"] is False
        result_data = json.loads(result["result"]["content"][0]["text"])
        assert result_data["ok"] is True
        assert result_data["data"]["cpk"] is not None

        invalid = _request(process, {
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {
                "name": "akia_run_tool",
                "arguments": {"tool": "missing"},
            },
        })
        assert invalid["result"]["isError"] is True
    finally:
        assert process.stdin is not None
        process.stdin.close()
        process.wait(timeout=10)
    assert process.returncode == 0, process.stderr.read() if process.stderr else ""


def test_serve_stdio_handles_parse_and_line_protocol():
    service = MCPService(AKIAClient.from_dataframes({"Sheet1": _frame()}))
    source = io.StringIO(
        "not-json\n"
        '{"jsonrpc":"2.0","id":NaN,"method":"ping"}\n'
        '{"jsonrpc":"2.0","id":2,"method":"ping"}\n'
    )
    target = io.StringIO()
    assert serve_stdio(service, source, target) == 0
    responses = [json.loads(line) for line in target.getvalue().splitlines()]
    assert responses[0]["error"]["code"] == -32700
    assert responses[1]["error"]["code"] == -32700
    assert responses[2]["result"] == {}


def test_mcp_one_click_does_not_report_zero_results_as_success():
    service = MCPService(AKIAClient.from_dataframes({
        "Sheet1": pd.DataFrame({"status": ["accepted", "rejected"]}),
    }))
    response = service.handle({
        "jsonrpc": "2.0", "id": 8, "method": "tools/call",
        "params": {
            "name": "akia_one_click",
            "arguments": {"selected": ["capability"]},
        },
    })
    payload = json.loads(response["result"]["content"][0]["text"])
    assert response["result"]["isError"] is True
    assert payload["ok"] is False
    assert payload["data"]["total_count"] == 0
