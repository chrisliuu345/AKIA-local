# AKIA

[中文](README.md) | [English](README.en.md) | [路线图](ROADMAP.md) | [发布版本](https://github.com/chrisliuu345/AKIA-local/releases) | [问题反馈](https://github.com/chrisliuu345/AKIA-local/issues)

[![CI](https://github.com/chrisliuu345/AKIA-local/actions/workflows/ci.yml/badge.svg)](https://github.com/chrisliuu345/AKIA-local/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

AKIA 是一款开源、本地优先的个人工业工程（IE）与质量分析桌面软件，面向现场改善、质量工程和数据分析工作。它将统计过程控制、测量系统分析、试验设计、可靠性分析、IE 工具和改善案例管理整合在一个离线桌面应用中。

当前版本：v4.5.0。

AKIA 不要求账号、订阅或在线激活。数据默认保存在本机；只有在你主动配置云模型、数据库、看板或外部设备时，软件才会建立相应的网络连接。

## 功能

- **IE 工具**：时间研究、OEE、SMED、TPM、线平衡、价值流图、技能约束排班。
- **统计与质量**：SPC、过程能力、MSA、假设检验、DOE、可靠性、时间序列与预测。
- **改善闭环**：改善案例、标准版本记录、证据账本、8D、FMEA、控制计划与 PPAP。
- **实时分析**：实时 SPC、设备数据接入、产线拓扑、告警与看板。
- **可复现分析**：已知值测试、抽样决定记录、判定凭证与可独立校验的证据包。
- **可选 AI 助手**：支持本地 Ollama 和用户自带的 OpenAI 兼容服务，密钥加密保存。
- **报告与扩展**：PDF、Word、Excel、HTML 报告，以及插件式数据源和工具扩展。
- **开放接口**：无界面 CLI/SDK、本地 MCP stdio 服务、版本化规则包和插件脚手架。
- **发布安全**：归档读取资源限制、哈希依赖锁、第三方许可证清单、依赖漏洞审计和发布溯源。

完整能力可在软件内「帮助 → 使用指南」中查看。

## 快速开始

### Linux AppImage

从 [Releases](https://github.com/chrisliuu345/AKIA-local/releases) 下载 `AKIA-4.5.0-x86_64.AppImage` 和同名 `.sha256` 文件：

```bash
sha256sum -c AKIA-4.5.0-x86_64.AppImage.sha256
chmod +x AKIA-4.5.0-x86_64.AppImage
./AKIA-4.5.0-x86_64.AppImage
```

无 FUSE 的环境可使用 `--appimage-extract-and-run` 启动。若要自行构建 AppImage，请运行 `bash build_appimage.sh`，产物位于 `build/`。

### Windows

下载 `AKIA-Setup-4.5.0.exe`，双击运行。
或在 Windows 上执行：

```powershell
python build_pyinstaller.py --onefile
```

随后使用 Inno Setup 编译 `packaging/AKIA-installer.iss`。

### 从源码运行

需要 Python 3.11+：

```bash
git clone https://github.com/chrisliuu345/AKIA-local.git
cd AKIA-local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

图表、数据库和工业连接器依赖均为可选安装；缺少时软件会给出明确提示。连接器依赖见 `requirements-connectors.txt`。

## 无界面接口

```bash
.venv/bin/python -m akia_sdk tools --pretty
.venv/bin/python -m akia_sdk run \
  --input data.xlsx \
  --tool run_capability \
  --params '{"column":"直径","usl":10.4,"lsl":9.6}'
.venv/bin/python -m akia_sdk.mcp --project analysis.qap
```

接口默认不加载第三方插件，MCP 服务在启动时固定数据源且只读。接口与格式说明：

- [CLI / SDK](docs/sdk-cli.md)
- [MCP 服务](docs/mcp.md)
- [规则包](docs/rule-packs.md)
- [插件开发](docs/plugin-development.md)
- [依赖与发布管理](docs/dependency-management.md)
- [标准数据验证](docs/standards-validation.md)

## 开发

```bash
.venv/bin/ruff check .
python tools/check_version.py
python tools/check_dependencies.py
python tools/check_aql_reference.py
python tools/run_tests.py --quiet
```

测试按文件逐个进程执行，以隔离 Qt、数值计算和资源占用。GUI 测试默认使用 `QT_QPA_PLATFORM=offscreen`。

主要构建入口：

- Linux：`build_appimage.sh`
- Windows：`build_pyinstaller.py` + `packaging/AKIA-installer.iss`
- CI 与发布门禁：`.github/workflows/ci.yml`

## 项目结构

```text
analysis/    统计算法与领域分析引擎
core/        核心数据模型、工作流和服务
ui/          PySide6 桌面界面
output/      报告与图表输出
server/      可选实时看板服务
config/      默认配置、模板和内置帮助
connectors/  数据库、设备和工业协议连接器
tests/       单元、集成与界面回归测试
tools/       开发、演示、性能与发布工具
```

## 参与贡献

欢迎通过 Issue 报告缺陷、提出使用场景或讨论实现方案，也欢迎提交 Pull Request。

- 提交前请运行相关测试、`ruff check .` 和 `python tools/check_version.py`。
- 涉及统计算法的修改应补充已知值或边界条件测试。
- 请不要在公开 Issue 中提交真实生产数据、密钥或个人敏感信息。
- 安全问题请通过 GitHub 私密漏洞报告功能联系维护者，不要公开披露利用细节。

更多接口说明见 [插件数据源契约](docs/plugin-data-source.md)，算法验证约定见 [KNOWN_VALUES.md](KNOWN_VALUES.md)。

## 许可证

AKIA 以 [Apache License 2.0](LICENSE) 开源，版权与归属说明见 [NOTICE](NOTICE)。第三方依赖、算法参考文献和外部插件分别遵循其各自许可证。
