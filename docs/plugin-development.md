# AKIA Plugin Development

AKIA uses directory-style plugins. A plugin declares its public contribution points in `plugin.json`; the host validates the manifest before importing code and only loads user plugins after explicit trust.

## 中文

### 生成脚手架

```bash
python tools/new_plugin.py \
  --id sample_plugin \
  --name "示例插件" \
  --capabilities tab,agent_tools,data_source \
  --output ~/.akia_plugins
```

生成目录：

```text
sample_plugin/
  plugin.json
  sample_plugin_impl.py
  README.md
```

脚手架不会覆盖已有目录。第三方插件不应把真实生产数据、密钥或用户配置写入仓库。

### 能力声明

| 能力 | 实现方法 | 用途 |
|------|----------|------|
| `tab` | `create_tab(host, parent=None)` | 增加工作页 |
| `agent_tools` | `register_agent_tools(registry, context=None)` | 注册带插件前缀的分析工具 |
| `settings` | `create_settings_page(host, parent=None)` | 增加设置页 |
| `data_source` | `provide_measurements(context=None)` | 返回受控的测量事件批次 |

`plugin.json` 中的 `api_version` 遵循主版本兼容规则：主程序 2.x 可加载所有 2.x 插件；破坏性改动只进入下一个主 API 版本。`requires.akia` 可进一步限制主程序版本。

### 静态兼容性检查

```bash
python tools/plugin_check.py ~/.akia_plugins/sample_plugin
python tools/plugin_check.py ~/.akia_plugins --json
python tools/plugin_check.py ~/.akia_plugins --app-version 4.5.0
```

检查器只读取 `plugin.json` 和 Python AST，不导入或执行插件代码。它会检查：

- 插件 id、目录名、API 版本和主程序版本要求；
- `entry` 是否为安全的 `module:Class` 路径；
- 入口类和源码是否可解析；
- 声明能力所需的方法是否存在；
- 是否实现 `is_available()`（缺失仅警告）。

数据源事件契约见 [插件数据源合同](plugin-data-source.md)。插件贡献点落地后可运行：

```bash
python tools/run_tests.py --files tests/test_plugin_api.py
python tools/run_tests.py --files tests/test_plugin_data_source.py
```

### 信任模型

- 随包插件默认信任。
- 用户目录与 pip entry point 插件首次只登记 manifest，不导入代码。
- 用户显式信任后才执行插件代码。
- 插件代码在本机用户权限下运行，不是安全沙箱；只安装来源可信的插件。

## English

Generate a plugin with `python tools/new_plugin.py --id <id> --name <name> --capabilities <list> --output <directory>`. The generator refuses to overwrite existing directories.

Capabilities map to `create_tab`, `register_agent_tools`, `create_settings_page`, and `provide_measurements`. Plugin API 2.x is backward-compatible within the same major version; `requires.akia` can add a host-version constraint.

Validate plugins with `python tools/plugin_check.py <path>` or `--json`. The checker parses the manifest and Python AST without importing plugin code, and verifies ids, API compatibility, host requirements, safe entry paths, entry classes, and capability methods.

Bundled plugins are trusted by default. User-directory and entry-point plugins are registered without import until the user explicitly trusts them. Plugins run with the current user's permissions and are not a security sandbox; install only trusted code.
