# AKIA MCP Service

## 中文

AKIA 的 MCP 服务通过标准输入输出在本机运行，并把一个在启动时固定的数据文件或 `.qap` 项目暴露给外部 AI 工具。服务只使用 Python 标准库实现 MCP JSON-RPC 工具协议，不需要额外安装 MCP 服务端依赖。

启动方式：

```bash
.venv/bin/python -m akia_sdk.mcp --input data.xlsx
.venv/bin/python -m akia_sdk.mcp --project analysis.qap
```

典型 MCP 客户端配置：

```json
{
  "mcpServers": {
    "akia-local": {
      "command": "/absolute/path/to/AKIA/.venv/bin/python",
      "args": [
        "-m",
        "akia_sdk.mcp",
        "--project",
        "/absolute/path/to/analysis.qap"
      ]
    }
  }
}
```

服务提供以下工具：

| 工具 | 作用 |
|------|------|
| `akia_list_tools` | 列出分析工具、参数与类别 |
| `akia_describe_data` | 返回数据画像和推荐，不返回原始数据行 |
| `akia_run_tool` | 调用 `akia_list_tools` 中的单个工具 |
| `akia_one_click` | 执行画像、推荐分析、分析和本地规则结论 |
| `akia_server_info` | 查看版本、数据源类型、工具数量和安全开关 |

安全边界：

- 数据源在服务启动时固定，调用阶段不接受文件路径。
- 服务只读，不保存项目，不写数据文件。
- 默认不扫描或执行第三方插件。
- 模型文件读写工具不会通过 MCP 暴露，调用阶段也会拒绝路径型参数。
- 每次调用都会校验工具名、参数名以及显式工作表/列引用。
- MCP 服务只提供 stdio 传输；当前不开放局域网 HTTP 监听。

## English

The AKIA MCP server runs locally over standard input/output and exposes one data file or `.qap` project fixed at startup. It implements the MCP JSON-RPC tool protocol with the Python standard library and requires no extra MCP server dependency. Launch `python -m akia_sdk.mcp --input <file>` or `--project <file>`, then configure the MCP client with the absolute Python path and matching arguments.

Available tools are `akia_list_tools`, `akia_describe_data`, `akia_run_tool`, `akia_one_click`, and `akia_server_info`. The server is read-only, hides model file I/O tools, rejects path-like parameters, accepts no call-time file paths, does not load third-party plugins, validates tool names, parameters, sheets, and columns, and currently supports stdio transport only.
