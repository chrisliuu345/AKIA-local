# QA-Tool — IE Quality Analyzer

A Python 3.14 + PySide6 desktop application for quality engineering and industrial engineering analysis. 34 analysis modules, AI-powered insights, and comprehensive reporting.

## Features

### Quality Analysis (6 modules)

| Module | Capabilities |
|------|------|
| **SPC Control Charts** | XBar-R/S · I-MR · P/NP/C/U · CUSUM · EWMA + Nelson 8 rules |
| **Process Capability** | Normal / Non-normal (Box-Cox) / Between-Within · Cp/Cpk/Pp/Ppk/PPM |
| **MSA** | Gauge R&R (crossed/nested) · Bias/Linearity · Attribute agreement |
| **Hypothesis Testing** | t-test · ANOVA · Normality · Variance equality · **Non-parametric** (MWU/Wilcoxon/Kruskal) |
| **DOE** | Full factorial / 2^k · Response surface CCD · Box-Behnken |
| **Regression** | Linear / Multiple · R² · Residual diagnostics · Correlation heatmap |

### IE Industrial Engineering (7 modules)

| Module | Capabilities |
|------|------|
| Time Study | Standard time · Rating factor · Allowance · Capacity vs Takt |
| Work Sampling | Ratio analysis · Confidence intervals · Utilization |
| Line Balancing | LPT balancing · Bottleneck identification · Yamazumi chart |
| **OEE** | A×P×Q · Loss decomposition · World-class / Good / Fair grading |
| VSM | Value stream mapping · VA/NVA · Lead time |
| **Worker-Machine** | Worker-Machine timeline chart (presets + editable) |
| **Standard Work** | Manual / Auto / Walk stacked bar chart |

### Engineering Tools (5 modules)

| Module | Capabilities |
|------|------|
| **Reliability** | Weibull 2P/3P MLE · MTBF/MTTR · **ALT** (Arrhenius / Inverse power law) |
| **Fishbone** | Interactive QGraphicsView · 3-level nesting · Drag / Double-click / Right-click |
| **Pareto** | Two-level drill-down · Top-N · Threshold line |
| **FMEA** | RPN=S×O×D · Risk coloring · PFMEA/DFMEA |
| Control Plan | 9-column template · Excel export |

### Chart Tools (4 modules)

15 chart types: Histogram / Box / Scatter / Pareto / Probability / Matrix / Residual / Main Effects / Interaction / Contour / 3D Surface / Time Series / Bubble / Radar / Waterfall + Capability Comparison + Multi-series Trend + Statistical Summary Panel

### Worksheet Tools (3 modules)

Merge (Append / JOIN / Batch) · Split (by column / row / condition / group) · LPA Audit Sheet

### Data Tools + Sampling (2 modules)

AQL Lookup (GB/T 2828.1 / ANSI/ASQ Z1.4) · Random / Stratified / Systematic Sampling · Sequential Testing · Data Generator (7 distributions) · Format Conversion · Outlier Detection (IQR / Z / Grubbs)

### IE Engineering Tools (NEW in v2.2)

| Module | Capabilities |
|------|------|
| **SMED** | Single-Minute Exchange of Die · Internal/External separation · Gantt timeline · Before/After comparison |
| **8D** | 8 Disciplines problem solving · D1-D8 stepper · Fishbone (D4) · PDF/Markdown export |
| **TPM** | Total Productive Maintenance · OEE / MTBF / MTTR · Six big losses · Pareto + Calendar |
| **PPAP** | Production Part Approval Process · 18-item checklist · Dimension Cp/Cpk · Submission levels |

### Reporting (NEW in v2.3)

| Feature | Description |
|------|------|
| **Template Engine** | 5 built-in HTML templates (Daily / Monthly SPC / Audit / 8D / PPAP) |
| **Template Dialog** | Preview + Export to PDF / Word / HTML |
| **HTML Export** | Self-contained offline report with matplotlib charts embedded as base64 |

---

## Quick Start

### Option 1: Portable (Recommended)

Download `QA-Tool-v2.4.1.exe` (~200MB single file), double-click to run. No Python required.

### Option 2: From Source

```bash
# Requires Python 3.11+
pip install PySide6 pandas numpy scipy matplotlib scikit-learn statsmodels reportlab openpyxl
python main.py
```

### Default Login

```
Username: admin
Password: admin
```

---

## Tech Stack

| Layer | Technology |
|------|------|
| UI | PySide6 (Qt) · Fusion dark theme · Global QSS |
| Numeric | NumPy · SciPy · pandas |
| ML | scikit-learn (RandomForest) · SHAP |
| Charts | matplotlib · seaborn |
| Reporting | reportlab (PDF) · python-docx (Word) · openpyxl (Excel) |
| AI | Ollama · OpenAI-compatible API · char-ngram TF-IDF RAG |
| Auth | PBKDF2-SHA256 (150K rounds) |
| Packaging | PyInstaller (single-file .exe) |

---

## Project Structure

```
├── main.py              # Entry point + Splash loader
├── analysis/            # Analysis engines (14 modules)
│   ├── spc/             # SPC control charts (9 types + Nelson rules)
│   ├── capability/      # Process capability (3 types)
│   ├── msa/             # Measurement system analysis (3 types)
│   ├── hypothesis/      # Hypothesis testing + non-parametric
│   ├── doe/             # Design of experiments (4 types)
│   ├── regression/      # Regression analysis
│   ├── ie/              # IE industrial engineering (SMED, TPM)
│   ├── reliability/     # Reliability (Weibull/MTBF/ALT)
│   ├── quality/         # 8D engine, PPAP engine, Fishbone engine
│   ├── charts/          # Chart generators (15 types)
│   └── ai/              # AI root cause analysis (SHAP)
├── core/                # Core engines (17 modules)
│   ├── auth.py          # 4-level RBAC + PBKDF2 auth
│   ├── data_loader.py   # Excel/CSV loader
│   ├── data_profiler.py # Smart diagnostics (20+ recommendation types)
│   ├── knowledge_base.py # TF-IDF RAG (124 entries)
│   ├── llm_client.py    # Ollama + OpenAI dual backend
│   ├── plugin_manager.py # Plugin system
│   ├── report_templates.py # Template engine (5 built-in)
│   ├── sampling_engine.py # GB/T 2828.1 AQL
│   └── ...
├── ui/                  # PySide6 UI
│   ├── tabs/            # 34 analysis tabs
│   ├── dialogs/         # 16 dialogs
│   ├── widgets/         # Toast / Fishbone canvas
│   └── theme.py         # Dark theme + font constants
├── config/              # Config + knowledge base + templates
│   ├── templates/       # HTML report templates
│   └── knowledge/       # Knowledge base JSON files
├── locales/             # zh.json / en.json
├── plugins/             # Third-party plugins
├── output/              # Report engines (Word/Excel/PDF/HTML)
└── tests/               # 215 pytest tests
```

---

## Enterprise Features

- **Multi-user**: 4-level roles (admin / dept_admin / analyst / readonly) + department / team
- **.qap project files**: ZIP-packaged projects containing data + charts + analyses
- **SQL Direct Connect**: MySQL / PostgreSQL / SQL Server
- **Batch Scheduling**: Scheduled tasks (daily / hourly / one-shot)
- **Shared Projects**: Department-level .qap file sharing
- **Audit Log**: `~/.qa_tool_audit.log`

---

## Version History

| Date | Version | Highlights |
|------|---------|------------|
| 2026-08-15 | **v2.4.1** | Adaptive dashboard card grid · fade-in / count-up / cross-fade animations · shop floor display aspect & readability fixes · batch analysis guards · 215 tests |
| 2026-08-13 | **v2.4** | Dashboard enhancement: unified KPI extractor · real-time refresh · card layout · formula editor · shop floor display mode |
| 2026-08-12 | v2.3 | Report template engine · Template dialog · HTML self-contained export · Menu restructure |
| 2026-08-10 | v2.2 | SMED · 8D · TPM · PPAP (4 new engineering tools) · 32 tabs |
| 2026-08-10 | v2.1 | Code audit · AI enhancement · Lazy loading · One-click analysis · 87 tests |
| 2026-08-04 | v2.0 | Initial release: 28 tabs · 65 tests · AI assistant · Plugin system |

---

## License

MIT

---

*Built with Python 3.14 + PySide6 · 215 tests passing · 34 analysis tabs*
