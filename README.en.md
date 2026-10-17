# AKIA

[中文](README.md) | [English](README.en.md) | [Roadmap](ROADMAP.en.md) | [Releases](https://github.com/chrisliuu345/AKIA-local/releases) | [Issues](https://github.com/chrisliuu345/AKIA-local/issues)

[![CI](https://github.com/chrisliuu345/AKIA-local/actions/workflows/ci.yml/badge.svg)](https://github.com/chrisliuu345/AKIA-local/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)

AKIA is an open-source, local-first desktop application for personal industrial engineering (IE) and quality analysis. It brings statistical process control, measurement system analysis, design of experiments, reliability, IE methods, and improvement-case management into one offline desktop workspace.

Current stable version: v4.4.0.

AKIA requires no account, subscription, or online activation. Data stays on your machine by default; network connections are made only when you explicitly configure a cloud model, database, dashboard, or external device.

## Features

- **IE toolkit**: time study, OEE, SMED, TPM, line balancing, value-stream mapping, and skill-constrained scheduling.
- **Statistics and quality**: SPC, process capability, MSA, hypothesis testing, DOE, reliability, time series, and forecasting.
- **Improvement workflow**: improvement cases, standard versioning, evidence ledgers, 8D, FMEA, control plans, and PPAP.
- **Live analysis**: live SPC, device data ingestion, line topology, alerts, and dashboards.
- **Reproducible results**: known-value tests, recorded sampling decisions, conclusion credentials, and independently verifiable evidence packs.
- **Optional AI assistant**: local Ollama or user-supplied OpenAI-compatible services, with encrypted credential storage.
- **Reports and extensions**: PDF, Word, Excel, and HTML reports, plus plugin-based data sources and tools.

The in-app guide under Help → User Guide provides the complete feature reference.

## Quick Start

### Linux AppImage

Download `AKIA-4.4.0-x86_64.AppImage` and its `.sha256` file from [Releases](https://github.com/chrisliuu345/AKIA-local/releases):

```bash
sha256sum -c AKIA-4.4.0-x86_64.AppImage.sha256
chmod +x AKIA-4.4.0-x86_64.AppImage
./AKIA-4.4.0-x86_64.AppImage
```

On systems without FUSE, launch with `--appimage-extract-and-run`. To build the AppImage yourself, run `bash build_appimage.sh`; output is written to `build/`.

### Windows

On Windows, run:

```powershell
python build_pyinstaller.py --onefile
```

Then compile `packaging/AKIA-installer.iss` with Inno Setup.

### Run from Source

Python 3.11+ is required:

```bash
git clone https://github.com/chrisliuu345/AKIA-local.git
cd AKIA-local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Charting, database, and industrial-connector dependencies are optional. The application shows installation guidance when they are unavailable. Connector dependencies are listed in `requirements-connectors.txt`.

## Development

```bash
.venv/bin/ruff check .
python tools/check_version.py
python tools/run_tests.py --quiet
```

Tests run one file per process to isolate Qt, numerical workloads, and memory use. GUI tests use `QT_QPA_PLATFORM=offscreen`.

Main build entry points:

- Linux: `build_appimage.sh`
- Windows: `build_pyinstaller.py` and `packaging/AKIA-installer.iss`
- CI and release gates: `.github/workflows/ci.yml`

## Project Layout

```text
analysis/    Statistical and domain-analysis engines
core/        Core data models, workflows, and services
ui/          PySide6 desktop interface
output/      Reports and chart output
server/      Optional live dashboard service
config/      Default configuration, templates, and in-app help
connectors/  Database, device, and industrial-protocol connectors
tests/       Unit, integration, and UI regression tests
tools/       Development, demo, benchmark, and release utilities
```

## Contributing

Issues with bug reports, use cases, and design proposals are welcome. Pull requests are also welcome.

- Run the relevant tests, `ruff check .`, and `python tools/check_version.py` before submitting.
- Changes to statistical algorithms should include known-value or boundary-condition tests.
- Do not post production data, credentials, or personal information in public issues.
- Report security vulnerabilities privately through GitHub's security advisory feature instead of disclosing them publicly.

See the [plugin data-source contract](docs/plugin-data-source.md) for extension interfaces and [KNOWN_VALUES.md](KNOWN_VALUES.md) for algorithm validation conventions.

## License

AKIA is released under the [Apache License 2.0](LICENSE), with attribution details in [NOTICE](NOTICE). Third-party dependencies, algorithm references, and external plugins retain their own licenses.
