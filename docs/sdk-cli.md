# AKIA Headless SDK and CLI

The AKIA headless interface runs the same local analysis engines as the desktop application. It does not create a Qt application and does not scan or execute third-party plugins by default.

## 中文

### 快速开始

命令行入口：

```bash
.venv/bin/python -m akia_sdk --help
.venv/bin/python -m akia_sdk tools --pretty
.venv/bin/python -m akia_sdk run \
  --input data.xlsx \
  --tool run_capability \
  --params '{"column":"直径","usl":10.4,"lsl":9.6}' \
  --pretty
```

Python SDK：

```python
from akia_sdk import AKIAClient

client = AKIAClient.from_file("data.xlsx")
result = client.run("run_capability", {"column": "直径", "usl": 10.4, "lsl": 9.6})
if result.ok:
    print(result.data["cpk"])
else:
    print(result.error)
```

### 命令

| 命令 | 作用 |
|------|------|
| `tools` | 列出分析工具、参数和返回字段 |
| `run` | 调用单个工具并输出 JSON |
| `profile` | 生成数据画像、质量问题和分析推荐 |
| `one-click` | 执行画像、推荐、分析和本地规则结论 |

常用选项：

- `--input`：CSV、`.xlsx`、`.xlsm` 或 `.xls` 数据文件。
- `--project`：读取 `.qap` 项目及其分析上下文（与 `--input` 互斥）。
- `--sheet`：只加载指定工作表，可重复。
- `--params` / `--params-file`：工具参数 JSON；不会静默忽略未知参数。
- `--output`：写入 JSON 文件；默认输出到标准输出。
- `--force`：允许覆盖已有输出文件。
- `--pretty`：格式化 JSON。

### Python SDK

```python
from akia_sdk import AKIAClient

client = AKIAClient.from_project("project.qap")

for spec in client.tool_specs():
    print(spec["name"], spec["description"])

result = client.run("run_spc", {"column": "直径", "chart_type": "imr"})
payload = result.as_dict()  # 可稳定序列化为 JSON
```

可用入口：

- `AKIAClient.from_file(path, sheets=None)`：加载数据文件。
- `AKIAClient.from_project(path, sheets=None)`：加载 `.qap`，无需 Qt。
- `AKIAClient.from_dataframes(frames)`：直接传入 `{工作表名: DataFrame}`。
- `tool_specs(category=None)`：读取版本化工具清单。
- `run(tool, params)`：返回 `SDKResult`。
- `profile()` / `one_click(selected=None)`：执行画像和一键分析。

第三方插件默认不加载。只有在调用方明确传入
`include_plugins=True` 时，SDK 才会扫描和执行插件代码。

### 输出与退出码

JSON 结果包含 `schema_version`、`sdk_api_version`、`app_version` 和 `ok`。
工具结果还包含 `tool`、`data`、`text`、`error` 与 `duration_ms`。

命令行退出码：

- `0`：命令执行成功。
- `1`：工具已执行，但分析返回失败；JSON 中 `ok=false`。
- `2`：输入文件、工具名、参数或输出路径错误。

错误以结构化 JSON 写入标准错误：

```json
{
  "ok": false,
  "error": {
    "code": "invalid_parameters",
    "message": "工具 run_capability 不接受参数: typo"
  }
}
```

## English

### Quick start

```bash
python -m akia_sdk tools --pretty
python -m akia_sdk run \
  --input data.xlsx \
  --tool run_capability \
  --params '{"column":"diameter","usl":10.4,"lsl":9.6}' \
  --pretty
```

```python
from akia_sdk import AKIAClient

client = AKIAClient.from_project("project.qap")
result = client.run("run_spc", {"column": "diameter", "chart_type": "imr"})
print(result.as_dict())
```

Commands are `tools`, `run`, `profile`, and `one-click`. Supported data inputs are CSV, `.xlsx`, `.xlsm`, `.xls`, and `.qap`. `--sheet` can be repeated, `--params-file` accepts a JSON object, and `--output` writes atomically unless the target exists without `--force`.

The Python SDK uses the same `schema_version` and result fields as the CLI. `AKIAClient.from_file`, `from_project`, and `from_dataframes` create a reusable client; `tool_specs()` lists the versioned tool catalogue; `run()` returns `SDKResult`; `profile()` and `one_click()` expose the desktop one-click workflow.

Plugins are never scanned by default in headless mode. A Python caller must explicitly use `include_plugins=True` to accept execution of third-party plugin code.

Exit codes are `0` for success, `1` when the selected tool returns an analysis failure, and `2` for invalid input, parameters, tool names, or output paths. Errors are emitted as JSON on standard error.

## Stability

`SDK_API_VERSION` and `OUTPUT_SCHEMA_VERSION` are currently `1.0`. Additive tool and response fields are allowed within the 1.x line. Renaming or removing a documented field requires a new major SDK/API version and release-note callout.
