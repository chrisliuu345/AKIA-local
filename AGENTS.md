# AKIA 本地开发约定

本文件适用于 AKIA 工作区内的开发者和代码代理。

## 远端基准

- `origin/main` 是源码、文档和配置的唯一基准。
- 开始修改前先执行 `git fetch origin main`，确认本地与远端的关系。
- 本地落后时使用 `git merge --ff-only origin/main`；需要整理自己的未推送提交时使用 rebase。
- 不使用强制推送，不改写已经推送到远端的提交。
- 只有用户明确要求时才提交或推送。

## 工作区边界

以下目录或文件属于本机运行与构建环境，不是远端源码的一部分：

- `.venv/`
- `.pytest_cache/`、`.ruff_cache/`、`__pycache__/`
- `build/`、`dist/`
- `TEMP/` 里的暂存文件（目录占位 `TEMP/.gitkeep` 除外）
- `data/`
- `user_config.json`
- 本地发布归档和其他被 `.gitignore` 排除的文件

临时文件、一次性生成物和审查草稿只放在 `TEMP/`。这是唯一的本地暂存目录；不要在仓库根目录或其他源码路径另建 `tmp/`、`temp/` 或 `scratch/`。`.gitignore` 排除该目录的内容，只跟踪 `TEMP/.gitkeep`，不要提交暂存文件。

清理时应优先删除可再生成的缓存和明确的旧发布产物。`.venv/`、`data/`、`TEMP/`、`build/`、`dist/`、`user_config.json` 以及 `.agents/`、`.aws/`、`.codex/` 可能包含开发环境或用户数据，除非用户明确要求，否则不要删除。

项目只保留与当前源码有关的文件。过时的 Word 指南、历史发布包、临时报告和一次性审查材料不要放回仓库；软件内指南位于 `config/help/guide.html`。

## 开发环境

- Python 版本要求为 3.11+。
- 使用项目虚拟环境中的解释器和工具：`.venv/bin/python`、`.venv/bin/ruff`。
- 安装依赖使用 `requirements.txt`；需要连接器时再安装 `requirements-connectors.txt`。
- CI 和可复现环境中使用哈希锁：核心 `requirements.lock`，全量测试 `requirements-ci.lock`；
  更新锁文件的方法见 `docs/dependency-management.md`。
- GUI 测试使用 `QT_QPA_PLATFORM=offscreen`。

## 测试与质量门禁

- 测试必须逐文件运行，禁止直接执行 `pytest tests/`：

  ```bash
  .venv/bin/python tools/run_tests.py --files tests/test_example.py
  ```

- 修改后至少运行相关测试、静态检查和版本一致性检查：

  ```bash
  .venv/bin/ruff check .
  .venv/bin/python tools/check_version.py
  ```

- 修改依赖、许可证或发布脚本时，额外运行
  `.venv/bin/python tools/check_dependencies.py`。
- 修改抽样表、AQL 映射或转移规则时，额外运行
  `.venv/bin/python tools/check_aql_reference.py`；完整标准原文复核状态见
  `docs/standards-validation.md`。
- 修改 SDK、CLI 或 MCP 时，至少运行 `tests/test_sdk_cli.py`、`tests/test_mcp_server.py`；
  MCP 保持 stdio、只读、启动时固定数据源，调用期不得接受任意文件路径。
- 修改插件接口或脚手架时，运行 `tests/test_plugin_api.py`、
  `tests/test_plugin_data_source.py`、`tests/test_plugin_scaffold.py`。
- 验证插件契约使用 `python tools/plugin_check.py <插件目录>`；该检查不得导入或执行插件代码。
- 涉及发布、打包、公共接口或核心数据模型的改动，应扩大到相关集成测试和打包冒烟。
- 统计算法改动必须补充已知值、边界条件或等价性测试。
- 性能相关改动应运行 `tools/benchmark.py`，不要在没有基线证据时宣称性能提升。

## 代码约定

- 保持 `analysis/` 不依赖 Qt；`core/`、`config/`、`output/` 不导入 `ui/`。
- `core/agent/` 保持无 Qt；核心数据模型优先放在 `core/`。
- 修改现有代码时保持局部化，不进行与任务无关的重构或格式化。
- 新功能必须接入统一的 Tab 注册、工作表路由、菜单或命令面板入口，并补充回归测试。
- 新文件使用 UTF-8，代码注释说明“为什么”而不是重复“做了什么”。
- 公共 SDK 输出使用 `schema_version`；工具名、参数、错误码和 JSON 字段的破坏性变更必须升级
  SDK/API 主版本并在发布说明中标注。

## 文档与许可证

- `README.md` 与 `README.en.md`、`ROADMAP.md` 与 `ROADMAP.en.md` 必须同步维护。
- 面向公开项目，不写入闭源、订阅、商业版本、竞品对标或产品更名历史等定位信息。
- 许可证为 Apache License 2.0；修改程序元数据、安装器或关于页时，同步保持 `LICENSE`、`NOTICE` 和许可证声明一致。
- 版本号以 `config/settings.py::APP_VERSION` 为单一事实源；构建脚本和文档通过 `tools/check_version.py` 校验。
- 不在仓库中保存真实生产数据、个人敏感信息、密钥或访问令牌。

## 构建与发布

- Linux 使用 `bash build_appimage.sh`，Windows 使用 `build_pyinstaller.py` 和 `packaging/AKIA-installer.iss`。
- `build/`、`dist/` 和本地发布归档不入库；发布产物放在 GitHub Releases。
- 发布前必须通过版本一致性、ruff、逐文件回归、性能基线和打包冒烟。
- 发布锁文件由 `constraints-known-good.txt` 约束关键主版本；升级 Qt、pandas、SQLAlchemy、
  FastAPI 等依赖前必须跑全量逐文件回归。
- 发布产物必须附带 `licenses/`、`THIRD_PARTY_NOTICES.md` 和可验证的
  `release-manifest.json`；不得在未确认的情况下上传或覆盖远端发布资产。
- 安装包必须包含项目许可证、第三方许可证与归属信息。
