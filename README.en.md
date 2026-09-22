# QA-Tool

> Personal subscription quality engineering desktop tool (Minitab-like), integrating SPC + MSA + DOE + IE + Reliability + AI Analytics

[中文](README.md) | [English](README.en.md)

---

## Quick Start

v4.2.0 ships **two official editions** (all standalone, no Python required, fully offline):

| Edition | Installer file | Systems | Install |
|---------|----------------|---------|---------|
| **Linux AppImage** | `QA-Tool-4.2.0-x86_64.AppImage` | Any x86_64 Linux (Debian / Ubuntu / elementary, …) | Portable: make executable and run |
| **Windows installer** | `QA-Tool-Setup-4.2.0.exe` | Windows 10/11 (64-bit) | Run the Inno Setup wizard; menu/desktop shortcuts |

> Linux ships **AppImage only** (`.deb` is no longer built); works across Debian/Ubuntu/Fedora and derivatives.

### Linux (AppImage, portable)

```bash
chmod +x QA-Tool-4.2.0-x86_64.AppImage
./QA-Tool-4.2.0-x86_64.AppImage
```

### Windows (installer)

Download `QA-Tool-Setup-4.2.0.exe` from
[Releases](https://github.com/chrisliuu345/QA-Tool/releases) and run the Inno Setup wizard
(start-menu and desktop shortcuts included).

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
| **SPC Control Charts** | XBar-R/S · I-MR · P/NP/C/U · CUSUM · EWMA · **MEWMA** · **generalized variance \|S\|** · Hotelling T² + Nelson 8 rules · **changepoint detection (PELT)** · **ARIMA residual chart** |
| **Capability** | Normal / Non-normal / Johnson / Sixpack · Cp/Cpk/Pp/Ppk |
| **MSA** | Gage R&R · EMP Method · Attribute Agreement · Type 1 · Uncertainty Budget |
| **Hypothesis Testing** | t-test · ANOVA · Normality · Non-parametric · Equivalence |
| **DOE** | Full/Partial Factorial · CCD · Box-Behnken · PB · DSD · Taguchi · Mixture |
| **Reliability** | Weibull 2P/3P/4P · KM Survival · Cox Regression · ALT · RBD |
| **Time Series** | ARIMA · Exponential Smoothing · Seasonal Decomposition · Forecasting |

### Predictive Analytics & Machine Learning (v4.0.0)

| Module | Capabilities |
|--------|--------------|
| **AutoML** | Linear/logistic regression · CART · Random Forests (OOB) · Gradient boosting (built-in HistGradientBoosting, optional XGBoost) · MARS; CV ranking and recommendation |
| **Feature engineering** | Missing values · one-hot encoding · quantile binning · standardization; leak-proof Pipeline · stratified split |
| **Model evaluation** | R²/adj-R²/RMSE/MAE/MAPE · Accuracy/P/R/F1/AUC · confusion matrix · ROC · K-fold CV · learning curve · residual diagnostics |
| **Explain & deploy** | SHAP (auto-fallback to native/permutation importance) · single-sample explanation · `.qamodel` save/load · prediction export |
| **QAM Harness tools** | `ml_prepare_data` · `ml_train` · `ml_automl` · `ml_evaluate` · `ml_explain` · `ml_predict` |

### IE Engineering

| Module | Capabilities |
|--------|-------------|
| **Time Study** | Stopwatch · Rating Factor · Allowance · Standard Time |
| **OEE** | Overall Equipment Effectiveness · Loss Breakdown |
| **SMED** | Quick Changeover · Internal/External Separation |
| **TPM** | Total Productive Maintenance · Six Big Losses |
| **Line Balance** | LPT Balancing · Bottleneck Identification |
| **VSM** | Value Stream Map · VA/NVA · Production Cycle |

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
| **QAM Harness** | AI agent with 37 local tools (SPC/capability/MSA/hypothesis/DOE/regression/reliability/time-series/IE/cost/realtime/five-chain/root-cause/machine-learning) + offline tool mode · BYOK cloud providers (OpenAI/Claude/Gemini/DeepSeek/Z.ai/KIMI + custom endpoints) · encrypted keys + cloud privacy gate · Knowledge Base RAG |
| **Plugin API v2** | External plugins developed/published separately: pip entry point or user dir · Tab / agent tools / settings contributions · dependency probing + trust model (e.g. [QA-Tool-Vision-expansion](https://github.com/chrisliuu345/QA-Tool-Vision-expansion)) |
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
| Build | PyInstaller (onedir) · Inno Setup · AppImage (sole Linux format) |

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
├── ai/                # AI Root Cause Analysis
└── ml/                # Predictive analytics & ML (AutoML/MARS/explain)
core/                  # Core Engines
ui/                    # PySide6 UI (37 Tabs + plugin Tabs)
output/                # Report Engine
tests/                 # 1500+ Tests
```

---

## Download

Download the latest version from [Releases](https://github.com/chrisliuu345/QA-Tool/releases).

---

## License

Proprietary commercial software. Unauthorized copying, modification, or distribution is prohibited.

© 2026 QA-Tool. All rights reserved.

---

*Python 3.14 + PySide6 · 1950+ Tests · 37 Analysis Tabs + Plugin API v2*
