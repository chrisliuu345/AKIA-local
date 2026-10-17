# AKIA

> **AKIA (AKIM IE/Quality analyzer-local)** — a personal-subscription quality engineering
> desktop tool (Minitab-like), integrating SPC + MSA + DOE + IE + Reliability + AI Analytics

[中文](README.md) | [English](README.en.md)

> **Naming note**: as of v4.2.0 the product is renamed **AKIA (AKIM IE/Quality analyzer-local)**.
> The v4.2.0 Linux AppImage asset keeps its original file name `QA-Tool-4.2.0-x86_64.AppImage`
> (published GitHub assets cannot be renamed); releases from v4.3.0 use `AKIA-*`.
>
> **Release form**: current version **v4.4.0 — closed-loop execution & effect verification** — source plus a
> Linux AppImage (`AKIA-4.4.0-x86_64.AppImage` with a `.sha256` checksum file); the Windows installer
> is built on Windows.

---

## Quick Start

The latest release is v4.4.0, shipping standalone, fully offline packages — a **Linux AppImage** (published with the release)
and a **Windows Inno Setup installer** (built on Windows):

| Edition | Installer file | Systems | Status | Install |
|---------|----------------|---------|--------|---------|
| **Linux AppImage** | `AKIA-4.4.0-x86_64.AppImage` | Any x86_64 Linux (Debian / Ubuntu / Fedora / elementary, …) | ✅ Ships with the [v4.4.0 release](https://github.com/chrisliuu345/AKIA-local/releases/tag/v4.4.0) (plus a `.sha256` checksum file) | Portable: make executable and run |
| **Windows installer** | `AKIA-Setup-4.4.0.exe` | Windows 10/11 (64-bit) | Built on Windows (`build_pyinstaller.py` + `packaging/AKIA-installer.iss`) | Run the Inno Setup wizard; menu/desktop shortcuts |

> Linux ships **AppImage only** (`.deb` is no longer built); works across Debian/Ubuntu/Fedora and derivatives.

### Linux (AppImage, portable)

```bash
# download both files from the v4.4.0 release first
sha256sum -c AKIA-4.4.0-x86_64.AppImage.sha256
chmod +x AKIA-4.4.0-x86_64.AppImage
./AKIA-4.4.0-x86_64.AppImage
```

> On systems without FUSE (containers / minimal distros) add `--appimage-extract-and-run`.
> To build it yourself from source: `bash build_appimage.sh` (output lands in `build/`).

### Windows (installer)

On Windows run `python build_pyinstaller.py --onefile`, then compile
`packaging/AKIA-installer.iss` with Inno Setup to produce `AKIA-Setup-4.4.0.exe`
(start-menu and desktop shortcuts included).

### From Source

```bash
git clone https://github.com/chrisliuu345/AKIA-local.git
cd AKIA-local
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Requires Python 3.11+

> **Optional chart dependencies**: missing matplotlib / seaborn no longer blocks the
> main window or data/analysis/evidence features; chart tabs show an install hint
> (`pip install matplotlib seaborn`). See `requirements.txt` for the full set.

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
| **Closed-loop execution (v4.4.0)** | **Alert→8D auto case** (critical alerts open a case synchronously · 30-min cooldown merge · D6 data gate: closure needs re-measurement data) · **Measurement system online** (rolling repeatability/bias · MPC detection · health score & drift alerts) · **Trustworthy sampling** (GB/T 2828.1 transfer state machine · deterministic sampling with seed + row fingerprint · scheme trail in the evidence ledger · lot-inspection panel) · **Benefit ledger & COPQ** (monthly recompute · double-count protection · confidence gate · ROI) · **Skill-constrained line balancing** (skill matrix + headcount/equipment caps → executable roster) · **Sampling transparency** (chart/trend/profiler sampling uniformly labelled and reproducible) |

### AI & Reports

| Module | Capabilities |
|--------|-------------|
| **QAM Harness** | AI agent with 37 local tools (SPC/capability/MSA/hypothesis/DOE/regression/reliability/time-series/IE/cost/realtime/five-chain/root-cause/machine-learning) + offline tool mode · BYOK cloud providers (OpenAI/Claude/Gemini/DeepSeek/Z.ai/KIMI + custom endpoints) · encrypted keys + cloud privacy gate · Knowledge Base RAG |
| **Plugin API v2.1** | External plugins developed/published separately: pip entry point or user dir · Tab / agent tools / settings / **measurement data source (`data_source`)** contributions · dependency probing + trust/timeout/bad-data isolation (e.g. [AKIA-Vision-expansion](https://github.com/chrisliuu345/AKIA-Vision-expansion); contract & example: [plugin data source contract](docs/plugin-data-source.md)) |
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
tests/                 # 2400+ Tests
```

---

## Download

Download from [Releases](https://github.com/chrisliuu345/AKIA-local/releases):

- `v4.4.0` (current) — **closed-loop execution & effect verification** (B0–B8): alert→8D auto case /
  measurement system online / trustworthy sampling (transfer state machine + sampling-decision trail) /
  benefit ledger & COPQ / skill-constrained line balancing / sampling transparency
  (eight-link end-to-end demo `tools/demo_v44_case.py`); Linux AppImage `AKIA-4.4.0-x86_64.AppImage`
  plus source archives (zip / tar.gz) —
  see the [v4.4.0 Release](https://github.com/chrisliuu345/AKIA-local/releases/tag/v4.4.0)
- `v4.3.0` — **improvement cases & evidence ledger** (B0–B6): case lifecycle /
  measurement channels / standard version records / evidence ledger & exchange v1;
  Linux AppImage (x86_64) plus source archives (zip / tar.gz) —
  see the [v4.3.0 Release](https://github.com/chrisliuu345/AKIA-local/releases/tag/v4.3.0)
- `v4.2.1` — **source-only patch** (quality hardening + branding/UX/startup fixes);
  source zip / tar.gz only, no new installers —
  see the [v4.2.1 Release](https://github.com/chrisliuu345/AKIA-local/releases/tag/v4.2.1)
- `v4.2.0` — Linux AppImage (historical asset name `QA-Tool-4.2.0-x86_64.AppImage` + `.sha256`) and source archives (zip / tar.gz) —
  see the [v4.2.0 Release](https://github.com/chrisliuu345/AKIA-local/releases/tag/v4.2.0)

---

## Developer Docs

- [Plugin data source contract (API 2.1)](docs/plugin-data-source.md)
- [Known-value and test conventions](KNOWN_VALUES.md) · [Per-file test rules](PYTEST_RULES.md)
- [In-app guide](config/help/guide.html)
- Closed-loop eight-link end-to-end demo: `python tools/demo_v44_case.py --output TEMP/demo_v44`
- End-to-end evidence-chain demo: `python tools/demo_v43_case.py --output TEMP/demo_v43`

---

## License

Proprietary commercial software. Unauthorized copying, modification, or distribution is prohibited.

© 2026 AKIA. All rights reserved.

---

*Python 3.14 + PySide6 · 2400+ Tests · 37 Analysis Tabs + Plugin API v2.1*
