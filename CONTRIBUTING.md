# 贡献指南 | Contributing to QA-Tool

> [中文](CONTRIBUTING.md) | [English](CONTRIBUTING.en.md)

感谢你对 QA-Tool 的关注！本文档说明如何参与贡献，以及提交贡献前需要了解的许可证条款。

---

## 目录

1. [项目技术栈](#项目技术栈)
2. [开发环境搭建](#开发环境搭建)
3. [代码规范](#代码规范)
4. [测试要求](#测试要求)
5. [提交规范](#提交规范)
6. [Pull Request 流程](#pull-request-流程)
7. [许可证与贡献条款（必读）](#许可证与贡献条款必读)
8. [问题反馈](#问题反馈)

---

## 项目技术栈

| 项 | 说明 |
|----|------|
| 语言 | Python 3.14（仅 Windows 桌面） |
| UI 框架 | PySide6（Qt 6） |
| 测试 | pytest |
| 硬件 | MicroPython（ESP32）/ MaixCAM（可选） |
| 文档 | README / ROADMAP 中英双语同步维护 |

## 开发环境搭建

```bash
# 1. 克隆仓库
git clone https://github.com/chrisliuu345/QA-Tool.git
cd QA-Tool

# 2. 安装依赖（建议使用虚拟环境）
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 3. 运行主程序验证环境
python main.py
```

## 代码规范

- 遵循现有代码风格：模块分层为 `core/`（内核）、`ui/`（界面）、`analysis/`（分析引擎）、`utils/`（工具）
- 新增 UI 文案使用 i18n 机制（`core/i18n.py` + `locales/`），中英文案同步维护
- 不引入与 AGPL-3.0 不兼容的第三方依赖（见[许可证条款](#许可证与贡献条款必读)）
- 修复缺陷请附带可复现的回归测试；新功能请附带对应单元测试

## 测试要求

```bash
# 逐文件运行测试（不要批量组合运行，Windows 下曾引发崩溃）
python -m pytest tests/test_core_modules.py -q

# 无头/离屏环境（无显示器或 CI）需设置
set QT_QPA_PLATFORM=offscreen
```

- 提交 PR 前请运行与改动相关的测试文件，并保证全部通过
- 当前基线：全量测试约 278 项，全部通过

## 提交规范

采用 Conventional Commits 风格，描述可使用中文：

```
<type>(<scope>): <简要描述>

类型（type）：feat / fix / docs / refactor / test / chore
范围（scope）：ui / core / analysis / devices / roadmap 等
```

示例：

```
feat(spc): 新增 EWMA 控制图 lambda 自适应
fix(ui): 修复设置对话框切换主题崩溃
docs(roadmap): 更新 v2.6.2 硬件收尾进度
```

## Pull Request 流程

1. Fork 本仓库并创建特性分支：`git checkout -b feat/your-feature`
2. 完成开发与测试，按上述规范提交
3. 向 `main` 分支发起 Pull Request，描述改动内容与测试结果
4. 等待代码审查与合并

---

## 许可证与贡献条款（必读）

本项目采用 **GNU Affero 通用公共许可证 v3.0（AGPL-3.0）**，完整文本见 [LICENSE](LICENSE)。提交贡献前请务必了解以下条款：

### 1. 贡献即授权

你没有义务签署 CLA 或 DCO。**向本项目提交 Pull Request（或以其他方式贡献代码、文档），即表示你同意该贡献内容以 AGPL-3.0 或更高版本纳入并再发布本项目。**

### 2. 你必须拥有贡献内容的权利

- 贡献的代码必须是你本人编写，或来自 AGPL-3.0 兼容许可的开源项目（并注明来源与许可证）
- 不得提交无法再授权的代码：包括抄自闭源项目、受雇主/客户知识产权约束、或来自 GPL 不兼容许可的代码
- 若贡献涉及专利，提交即视为向本项目用户授予 AGPL 第 11 条所述的专利许可

### 3. AGPL-3.0 的传染性（对下游用户）

- 任何基于本项目的修改、扩展并以任何形式**分发**的衍生作品，必须以 AGPL-3.0 开源全部源码
- **网络服务条款（第 13 条）**：即使不分发、仅以网络服务形式向用户提供修改版运行结果，也必须向该等用户提供对应完整源码。这是 AGPL 区别于 GPL 的核心条款
- 商业闭源集成需求请联系维护者另行协商授权

### 4. 第三方依赖

新增依赖必须与 AGPL-3.0 兼容（GPL-3.0 兼容清单：MIT / BSD / Apache-2.0 / LGPL-3.0 / GPL-3.0 等）。**注意：LGPL-2.1、MPL-2.0、Apache-2.0 与 GPLv3 组合的边界问题请先在 issue 中讨论。**

---

## 问题反馈

- 缺陷报告与功能建议：[GitHub Issues](https://github.com/chrisliuu345/QA-Tool/issues)
- 报告缺陷时请附：版本号、复现步骤、报错信息/截图

---

*感谢你的贡献！| Thank you for contributing!*
