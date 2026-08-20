# Contributing to QA-Tool

> [中文](CONTRIBUTING.md) | [English](CONTRIBUTING.en.md)

Thank you for your interest in QA-Tool! This document explains how to contribute and the license terms you need to understand before submitting.

---

## Contents

1. [Tech Stack](#tech-stack)
2. [Development Setup](#development-setup)
3. [Code Guidelines](#code-guidelines)
4. [Testing Requirements](#testing-requirements)
5. [Commit Convention](#commit-convention)
6. [Pull Request Workflow](#pull-request-workflow)
7. [License and Contribution Terms (Must Read)](#license-and-contribution-terms-must-read)
8. [Reporting Issues](#reporting-issues)

---

## Tech Stack

| Item | Details |
|------|---------|
| Language | Python 3.14 (Windows desktop only) |
| UI framework | PySide6 (Qt 6) |
| Testing | pytest |
| Hardware | MicroPython (ESP32) / MaixCAM (optional) |
| Docs | README / ROADMAP maintained in both English and Chinese |

## Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/chrisliuu345/QA-Tool.git
cd QA-Tool

# 2. Install dependencies (a virtual environment is recommended)
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 3. Run the app to verify your environment
python main.py
```

## Code Guidelines

- Follow the existing code style: modules are layered as `core/` (kernel), `ui/` (interface), `analysis/` (analysis engines), `utils/` (utilities)
- New UI strings must go through the i18n mechanism (`core/i18n.py` + `locales/`), with both English and Chinese maintained
- Do not introduce third-party dependencies incompatible with AGPL-3.0 (see [License Terms](#license-and-contribution-terms-must-read))
- Bug fixes should include a regression test; new features should include unit tests

## Testing Requirements

```bash
# Run tests file by file (do not batch them together; this has caused crashes on Windows)
python -m pytest tests/test_core_modules.py -q

# For headless/offscreen environments (no display or CI)
set QT_QPA_PLATFORM=offscreen
```

- Before submitting a PR, run the test files related to your changes and make sure they all pass
- Current baseline: ~278 tests in total, all passing

## Commit Convention

We follow the Conventional Commits style; descriptions may be written in Chinese:

```
<type>(<scope>): <short description>

Types: feat / fix / docs / refactor / test / chore
Scopes: ui / core / analysis / devices / roadmap, etc.
```

Examples:

```
feat(spc): add adaptive lambda for EWMA control chart
fix(ui): fix crash when switching theme in settings dialog
docs(roadmap): update v2.6.2 hardware wrap-up progress
```

## Pull Request Workflow

1. Fork this repository and create a feature branch: `git checkout -b feat/your-feature`
2. Complete development and testing, then commit following the convention above
3. Open a Pull Request against `main`, describing the changes and test results
4. Wait for code review and merge

---

## License and Contribution Terms (Must Read)

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**; see [LICENSE](LICENSE) for the full text. Please read the following terms before contributing:

### 1. Contribution Means Consent

You are not required to sign a CLA or DCO. **By submitting a Pull Request to this project (or contributing code or documentation in any other way), you agree that your contribution is incorporated into and redistributed under AGPL-3.0 or any later version of this project.**

### 2. You Must Have the Rights to Your Contribution

- Contributed code must be written by you, or come from open-source projects under AGPL-3.0-compatible licenses (with source and license attributed)
- Do not submit code you cannot relicense: including code copied from proprietary projects, code bound by your employer's/client's IP, or code under GPL-incompatible licenses
- If your contribution involves patents, submitting it grants the patent license described in Section 11 of AGPL-3.0 to users of this project

### 3. AGPL-3.0 Copyleft (for Downstream Users)

- Any derivative work based on this project that is modified, extended, and **distributed** in any form must be released in full source code under AGPL-3.0
- **Network Service Clause (Section 13)**: even without distribution, if you run a modified version as a network service for users, you must offer the corresponding complete source code to those users. This is the core clause distinguishing AGPL from GPL
- For commercial closed-source integration needs, please contact the maintainer to negotiate a separate license

### 4. Third-Party Dependencies

New dependencies must be AGPL-3.0-compatible (GPL-3.0-compatible list: MIT / BSD / Apache-2.0 / LGPL-3.0 / GPL-3.0, etc.). **Note: boundary issues around LGPL-2.1, MPL-2.0, and Apache-2.0 combined with GPLv3 should be discussed in an issue first.**

---

## Reporting Issues

- Bug reports and feature suggestions: [GitHub Issues](https://github.com/chrisliuu345/QA-Tool/issues)
- When reporting a bug, please include: version number, reproduction steps, error message/screenshots

---

*Thank you for contributing! | 感谢你的贡献！*
