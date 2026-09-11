# QA-Tool

> Personal subscription quality engineering desktop tool (Minitab-like), integrating SPC + MSA + DOE + IE + Reliability + AI Analytics

[中文](README.md) | [English](README.en.md)

---

## Quick Start

### Linux (AppImage)

```bash
chmod +x QA-Tool-3.7.2-x86_64.AppImage
./QA-Tool-3.7.2-x86_64.AppImage
```

### Linux (.deb)

```bash
sudo dpkg -i qa-tool_3.7.2_amd64.deb
qa-tool
```

### From Source

```bash
git clone https://github.com/chrisliuu345/QA-Tool.git
cd QA-Tool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Requires Python 3.11+

---

## Core Features

### Statistical Analysis

| Module | Capabilities |
|--------|-------------|
| **SPC Control Charts** | XBar-R/S · I-MR · P/NP/C/U · CUSUM · EWMA + Nelson 8 rules |
| **Capability** | Normal / Non-normal / Johnson / Sixpack · Cp/Cpk/Pp/Ppk |
| **MSA** | Gage R&R · EMP Method · Attribute Agreement · Type 1 · Uncertainty Budget |
| **Hypothesis Testing** | t-test · ANOVA · Normality · Non-parametric · Equivalence |
| **DOE** | Full/Partial Factorial · CCD · Box-Behnken · PB · DSD · Taguchi · Mixture |
| **Reliability** | Weibull 2P/3P/4P · KM Survival · Cox Regression · ALT · RBD |
| **Time Series** | ARIMA · Exponential Smoothing · Seasonal Decomposition · Forecasting |

### IE Engineering

| Module | Capabilities |
|--------|-------------|
| **Time Study** | Stopwatch · Rating Factor · Allowance · Standard Time |
| **OEE** | Overall Equipment Effectiveness · Loss Breakdown |
| **SMED** | Quick Changeover · Internal/External Separation |
| **TPM** | Total Productive Maintenance · Six Big Losses |
| **Line Balance** | LPT Balancing · Bottleneck Identification |
| **VSM** | Value Stream Map · VA/NVA · Production Cycle |
| **Vision Time Study** | Camera/video action recognition (working/idle/walking/carrying/away) · work cycles · standard time (optional deps) |

### Quality Tools

| Module | Capabilities |
|--------|-------------|
| **8D** | Eight Discipline Problem Solving · D1-D8 Wizard |
| **FMEA** | RPN=S×O×D · Risk Coloring · PFMEA/DFMEA |
| **PPAP** | Production Part Approval Process · 18-item Checklist |
| **Control Plan** | FMEA → Control Plan → SPC Five-chain Integration |

### AI & Reports

| Module | Capabilities |
|--------|-------------|
| **QAM Harness** | AI agent with 34 local tools (SPC/capability/MSA/hypothesis/DOE/regression/reliability/time-series/IE/vision time study/cost/realtime/five-chain/root-cause) + offline tool mode · BYOK cloud providers (OpenAI/Claude/Gemini/DeepSeek/Z.ai/KIMI + custom endpoints) · encrypted keys + cloud privacy gate · Knowledge Base RAG |
| **Charts** | 15+ chart types · Dark theme · CJK fonts |
| **Reports** | PDF / Word / Excel / HTML · Inline charts |

### Hardware Extension

| Module | Capabilities |
|--------|-------------|
| **Device Monitor** | ESP32 / MaixCAM · Auto-discovery · Real-time data |
| **ESP32** | 7-channel acquisition · Actuator control · MicroPython firmware |

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| UI | PySide6 (Qt) · Fusion Dark Theme |
| Numerical | NumPy · SciPy · pandas · scikit-learn |
| Charts | matplotlib · seaborn |
| Reports | reportlab · python-docx · openpyxl |
| AI | Ollama · OpenAI-compatible API · TF-IDF RAG |
| Hardware | pyserial · MicroPython (ESP32) |
| Live Dashboard | FastAPI · uvicorn · websockets (optional: `pip install -r requirements-server.txt`) |
| Build | PyInstaller (onedir) · Inno Setup · AppImage · .deb |

---

## Project Structure

```
main.py                # Entry point
analysis/              # Analysis engines (14 modules)
├── spc/               # SPC Control Charts
├── capability/        # Process Capability + Sixpack + Auto
├── msa/               # Measurement System (Gage R&R / EMP / Attribute)
├── hypothesis/        # Hypothesis Testing
├── doe/               # Design of Experiments
├── reliability/       # Reliability Analysis
├── time_series/       # Time Series
├── ie/                # IE Engineering
├── charts/            # Chart Generator
└── ai/                # AI Root Cause Analysis
core/                  # Core Engines
ui/                    # PySide6 UI (37 Tabs)
output/                # Report Engine
tests/                 # 1000+ Tests
```

---

## Download

Download the latest version from [Releases](https://github.com/chrisliuu345/QA-Tool/releases).

---

## License

Proprietary commercial software. Unauthorized copying, modification, or distribution is prohibited.

© 2026 QA-Tool. All rights reserved.

---

*Python 3.14 + PySide6 · 1280+ Tests · 37 Analysis Tabs*
