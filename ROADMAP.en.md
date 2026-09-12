# QA-Tool Roadmap

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> Current: v3.8.0 Industrial AI Agent (QAM Harness + BYOK + Plugin API v2) (✅ 2026-09-12) | Next: **v4.0.0 Predictive Analytics & Machine Learning (planned)** | Tests: 1567 pytest · 36 analysis tabs | Updated: 2026-09-12

> **Maintenance convention (from 2026-09-12)**: each version entry is one summary line plus key numbers; implementation details live in code/tests/user guide, not here.
> This file was compressed from 1100+ lines to under 500; the expanded history is in git history (`git log -p -- ROADMAP.md`).

---

## Version Overview

```
v2.0 ──→ v2.1 ──→ v2.2 ──→ v2.3 ──→ v2.4 ──→ v2.4.1 ──→ v2.5 ──→ v2.6.0 ~ v2.6.5 ──→ v2.7.0
      ──→ v2.8.0 ──→ v2.9.0 ──→ v3.0.0 ──→ v3.1.0 ──→ v3.2.0 ──→ v3.3.0 ──→ v3.4.0 ──→ v3.5.0
      ──→ v3.6.0 (incl. 3.6.1) ──→ v3.7.0 (incl. review) ──→ v3.7.1 ──→ v3.7.2 ──→ v3.8.0 ✅ current ──→ v4.0.0
```

| Status | Version | Theme |
|--------|---------|-------|
| ✅ | v2.0 ~ v3.0.0 | Initial release → code + AI → engineering tools → reports → live dashboard → hardware (ESP32/MaixCAM) → security/RBAC → stats hardening → UI robustness → defect cleanup → stats deepening → five-chain integration → security refactor |
| ✅ | v3.1.0 | DOE & Power Analysis |
| ✅ | v3.2.0 | Linux port + dual-system distribution |
| ✅ | v3.3.0 | Time series & forecasting (ARIMA / exponential smoothing / seasonal decomposition) |
| ✅ | v3.4.0 | Reliability & survival analysis (Weibull / KM / Cox / ALT / RBD / Crow-AMSAA / warranty) |
| ✅ | v3.5.0 | MSA & capability deepening (attribute agreement / EMP / Gage R&R / Sixpack / Edgeworth) |
| ✅ | v3.6.0 | Graph Builder enhancement & interaction (includes v3.6.1 full quality audit) |
| ✅ | v3.7.0 | Real-time SPC cloud dashboard & data connectors (P1-P6) |
| ✅ | v3.7.1 | Five-chain fixes + data-semantics and engineering-consistency hardening |
| ✅ | v3.7.2 | Realtime-monitoring benchmark polish, 8 items |
| ✅ | **v3.8.0** | **Industrial AI Agent (QAM Harness + Plugin API v2; vision moved to an external plugin)** |
| 🔌 | [QA-Tool-Vision-expansion](https://github.com/chrisliuu345/QA-Tool-Vision-expansion) | External vision plugin (video time study) built on Plugin API v2 |
| 🚧 | v4.0.0 | Predictive analytics & machine learning (next stage) |

---

## Core Competitive Positioning (2026-08 rework)

> Positioning: personal-subscription quality engineering tool (Minitab-like). No open-source product covers this breadth; the closest alternative is the commercial Datalyzer (~$2593/yr).

| # | Pillar | Landscape | Delivered in |
|---|--------|-----------|--------------|
| 1 | **Quality workflow integration** (FMEA→CP→SPC→PPAP→8D data chain) | Open gap | v2.8.0 ✅, ongoing |
| 2 | **Real-time factory integration** (ESP32/MaixCAM native + PLC/CMM/gauge connectors + cloud dashboard) | Minitab needs paid Prolink | v3.7.0 ✅ |
| 3 | **IE tool suite** (SMED/TPM/OEE/8D/FMEA/PPAP/Control Plan) | Minitab has no IE | v2.2.0 ✅ |
| 4 | **QAM Harness** (BYOK agent: 30 tools + offline routing + privacy gate) | Copilot is cloud-only | v3.8.0 ✅ |
| 5 | **Chinese-first + offline desktop** (GB/T built in) | Open gap | Throughout |

Planning principles:

1. Defect fixes before feature expansion; verify statistics against NIST/literature known values
2. Test baseline only grows; per-file regression + zero ruff warnings are release gates
3. One domain per release; add a Tab only when truly necessary
4. Personal-subscription scope: desktop + real-time device connectivity, no enterprise multi-company platform
5. External capabilities ship as Plugin API v2 plugins (e.g. vision); the main app keeps only the interface

---

## Version History (condensed)

| Date | Version | Summary |
|------|---------|---------|
| 09-12 | v3.8.0 | **Industrial AI Agent released**: QAM Harness (30 real tools + online/offline dual path + 6 BYOK providers + custom OpenAI-compatible endpoints + privacy gate + streaming chat UI); Plugin API v2 (manifest/capabilities/dependencies/trust + Tab/tool/settings contributions); vision moved to an external plugin project; wrap-up fixed Hotelling T² control limits (30% → 0.06% false flags) and a PyInstaller `unittest` exclusion that crashed the bundle; 108 files / 1567 passed / 2 skipped / 0 failed, ruff clean, onedir build + launch smoke passed |
| 09-12 | v3.8.1-plugin-api | Plugin API v2 + vision migration (`core/plugin_api.py` / `plugin_manager.py` / `ui/plugin_host.py`; 7 contract tests) |
| 09-11 | v3.8.0-P3 | Vision AI video time study (multi-source input / pipeline / pose / state machine / cycle splitting; later moved out as an external plugin) |
| 09-11 | v3.8.0-P1/P2 | QAM Harness core (16→30 tools, online + offline routing, chat UI, BYOK + privacy gate) |
| 09-10 | v3.7.2 | Realtime-monitoring benchmark polish, 8 items (spec limits & zoom / plant.json editor / alert levels & ack / cost loss / takt-based OEE P / downsampling & retention / connector health / dashboard auth) |
| 09-10 | v3.7.1 | Five-chain bridge fixes + column-semantics + packaging config isolation & secret encryption + APP_VERSION single source |
| 09-08 | v3.7.0 | Real-time SPC cloud dashboard & data connectors (stream bus / SQLite time series / FastAPI+WS dashboard / connector SPI / line topology / live OEE / alert center) |
| 09-07 | v3.7.0-prereq | Style debt cleared + ruff gate + build chain switched to PyInstaller (onedir) |
| 09-06 | v3.6.0 / v3.6.1 | Graph Builder enhancement (chart editor / heatmap / small multiples / exports / help center) + full quality audit (7 latent crash fixes) |
| 09-05 | v3.5.0 | MSA & capability deepening (Fleiss Kappa / EMP / Gage R&R enhancement / Sixpack / auto capability / Edgeworth) |
| 09-04 | v3.4.0 | Reliability & survival analysis (Weibull 2P-4P+CI / KM / Cox / ALT / RBD / Crow-AMSAA / warranty) |
| 09-01 | v3.3.0 | Time series (ARIMA auto-order / exponential smoothing / seasonal decomposition / forecasting / E2E) |
| 09-01 | v3.2.0 | Linux port (font system / keyring / AppImage / dual-system release) |
| 08-28 | v3.1.0 | DOE & power analysis (screening / fractional factorial / Taguchi / mixture / power engine) |
| 08-25 | v3.0.0 | Stabilization milestone (35-tab baseline) |
| 08-25 | v2.9.0 | Security architecture refactor (Auth removed + offline license + build-chain switch) |
| 08-25 | v2.8.0 | Workflow integration (ProjectContext as single source of truth + five chains) |
| 08-23 | v2.7.0 | Statistical engine deepening (P1 7 items + P2 6 items + 4 UI integrations) · 537+ tests |
| 08-23 | v2.6.5 | W-series defect cleanup + Info batch #1 · 450+ tests |
| 08-21 | v2.6.2 | RBAC matrix + auth hardening + device links + on-hardware verification · 296 tests |
| 08-19 | v2.6.1 | Security validation (password policy / audit log / secret store) · 282 tests |
| 08-18 | v2.6.0 | ESP32 deployment extension + Device Monitoring Tab 35 + PyInstaller/Inno packaging · 278 tests |
| 08-15 | v2.4.1 | Adaptive dashboard cards + animations · 215 tests |
| 08-13 | v2.4 | Dashboard E4 (KPI extractor / live refresh / card layout / formula editor / shop-floor display) · 136 tests |
| 08-12 | v2.3 | Report template engine + HTML export + menu restructure |
| 08-10 | v2.2 | 32 tabs · SMED/8D/TPM/PPAP · 87 tests |
| 08-04 | v2.0 | Initial release (28 tabs / 65 tests / AI assistant / plugin system) |

> Security, hardware and stabilization details from v2.1 ~ v3.0.0 are in git history and not repeated here.

---

## Current Release: v3.8.0 Highlights

- **QAM Harness agent**: 30 real tools (covering the main capabilities of 36 analysis tabs) + online LLM tool protocol / offline keyword routing (works without network) + 6 BYOK cloud providers (OpenAI / Anthropic / Google / DeepSeek / Z.ai / KIMI) + custom OpenAI-compatible endpoints + per-provider one-shot privacy gate; chat UI with anchored whole-block streaming, tool cards, an independent resizable window and fully custom model names
- **Plugin API v2**: `core/plugin_api.py` + `core/plugin_manager.py` + `ui/plugin_host.py`; three-tier discovery (bundled / user dir / pip entry point) + trust model + tool prefixing + dependency probing; untrusted plugins are parsed from the manifest but never imported
- **Vision moved out**: `analysis/vision`, Tab 37, tools and dependencies now live in [QA-Tool-Vision-expansion](https://github.com/chrisliuu345/QA-Tool-Vision-expansion); the main app keeps 36 tabs / 30 built-in tools plus plugin contributions
- **Wrap-up fixes**: Hotelling T² control limits (individual-observation UCL was 0, subgroup limits too tight); PyInstaller `unittest` exclusion that crashed the bundle on startup; dashboard-auth test port collisions
- **Quality numbers**: 1567 passed / 2 skipped / 0 failed (108 files, per-file regression); ruff clean; PyInstaller onedir build + offscreen launch smoke passed

---

## Known Backlog / Candidates

| Item | Note | Owner |
|------|------|-------|
| Manual review of proactive-suggestion accuracy (≥3.5/5) | Needs engineer scoring | User |
| Vision acceptance on real footage (site video + labelled CSV, ≥85% agreement) | Needs site material | Plugin project |
| Release artifacts (AppImage / .deb / Inno) | Scripts ready; build and upload to Releases on demand | Optional |
| Multi-site / multi-language | Deferred item #9 from v3.7.2 | Candidate |
| Connector expansion (more PLC/CMM protocols) | Driven by site needs | Candidate |
| Predictive analytics & ML | v4.0.0 | Next stage |

---

## v4.0.0 — Predictive Analytics & Machine Learning (planned)

> Theme: close the gap to Minitab Predictive Analytics-level machine learning; main app only, no plugin involvement.

### Scope

- **Data prep / feature engineering**: missing-value imputation · binning · encoding · feature crossing · standardization/normalization
- **CART**: tree building + pruning (pre/post) · confusion matrix · ROC
- **Random Forests**: bagging + feature randomness · OOB error · feature importance
- **Gradient boosting**: sklearn HistGradientBoosting as the primary implementation (optional XGBoost adapter) · learning-rate/depth tuning
- **MARS**: piecewise-linear basis functions · interaction detection (pure numpy)
- **AutoML**: multi-algorithm trials + AIC/BIC/AUC ranking + best-model recommendation
- **Model evaluation**: cross-validation · learning curves · overfitting diagnosis · residual analysis

### Implementation notes

- New `analysis/ml/`: `prep.py` / `trees.py` / `forest.py` / `boosting.py` / `mars.py` / `evaluate.py` / `automl.py`
- Reuse existing sklearn / shap dependencies plus `analysis/ai/root_cause.py` (RF+SHAP) and `analysis/regression/`
- New "Predictive Analytics" tab (index 37; plugin tabs shift automatically) + 6-8 QAM Harness tools (30 → ~38)
- Respect the layering guards (`analysis/` must not import Qt) and per-file test rules

### Acceptance criteria

- CART / Random Forests cross-validated against scikit-learn
- AutoML selection consistent with manual model selection
- End-to-end: data prep → feature engineering → modeling → evaluation → visualization

---

## Engineering Conventions

- **Version**: `config/settings.py::APP_VERSION` is the single source of truth; `tools/check_version.py` validates version_info / Inno / README / INSTALL / ROADMAP in CI
- **Build**: PyInstaller onedir (`build_pyinstaller.py`) → Inno (Windows) / AppImage / .deb; `build/` and `dist/` are not committed
- **Tests**: never run `pytest tests/` in bulk (conftest blocks it); run file by file; GUI tests use `QT_QPA_PLATFORM=offscreen`
- **Quality gates**: zero ruff warnings + relevant regression + packaging smoke (required for releases)
- **Layering**: `analysis/` must not import Qt; `core`/`config`/`output` must not import `ui`; `core/agent/` stays Qt-free
- **Plugins**: interact only through `core/plugin_api.py`, API major-version compatible; untrusted plugins are never imported
- **Docs**: keep README (zh/en), the in-app guide (guide.html) and this roadmap in sync

---

## Sidebar Evolution

> No new tabs during v2.6.5 ~ v3.0.0 (deepening focus); v3.8.0 is conversation-first and adds no dedicated tab.

| Version | Tabs | Change |
|---------|------|--------|
| v2.0 | 28 | Initial (Home / Quality / IE / Charts / Eng / Worksheet / Sampling / Report / Data / Plugins) |
| v2.2 | 32 | +SMED · +TPM · +8D · +PPAP |
| v2.4 | 34 | +Live Monitor · +Multi-Plant |
| v2.5 ~ v2.6 | 35 | +Device Monitoring (Tab 35) |
| v3.3.0 | 36 | +Time Series |
| v3.8.0 | 36 + plugins | Vision tab moved out; plugin tabs get dynamic indices (≥37); QAM Harness is a chat window (not a tab) |
