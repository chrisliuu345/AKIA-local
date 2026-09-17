# QA-Tool Roadmap

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> Current: v4.1.0 Chart & UI experience unification (chart style layer / defect fixes / command palette / performance baseline) (✅ 2026-09-15 · source prerelease) | Next: **v4.2.0 Algorithm trust & depth (planned)**
> Deepening line: **v4.2 Trust → v4.3 Case & evidence → v4.4 Closed loop → v4.5 Open → v4.6 Intelligence** (from analysis tool to a shop-floor improvement evidence chain) | Tests: 1708 pytest · 37 analysis tabs | Updated: 2026-09-17

> **Maintenance convention (from 2026-09-12)**: each version entry is one summary line plus key numbers; implementation details live in code/tests/user guide, not here.
> This file was compressed from 1100+ lines to under 500; the expanded history is in git history (`git log -p -- ROADMAP.md`).

---

## Version Overview

```
v2.0 ──→ v2.1 ──→ v2.2 ──→ v2.3 ──→ v2.4 ──→ v2.4.1 ──→ v2.5 ──→ v2.6.0 ~ v2.6.5 ──→ v2.7.0
      ──→ v2.8.0 ──→ v2.9.0 ──→ v3.0.0 ──→ v3.1.0 ──→ v3.2.0 ──→ v3.3.0 ──→ v3.4.0 ──→ v3.5.0
      ──→ v3.6.0 (incl. 3.6.1) ──→ v3.7.0 (incl. review) ──→ v3.7.1 ──→ v3.7.2 ──→ v3.8.0 ──→ v4.0.0
      ──→ v4.1.0 ✅ current ──→ v4.2.0 Trust (planned) ──→ v4.3.0 Case·evidence (planned) ──→ v4.4.0 Closed loop (planned)
      ──→ v4.5.0 Open (planned) ──→ v4.6.0 Intelligence (planned)
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
| ✅ | **v4.0.0** | **Predictive analytics & ML (CART / Random Forests / gradient boosting / MARS / AutoML + feature engineering / evaluation / SHAP / model deployment)** |
| ✅ | **v4.1.0** | **Chart & UI experience unification (B1 style layer / B2 chart fixes / B3 command palette·batch progress·toasts·empty state / B4 quality & performance baseline)** |
| 🚧 | v4.2.0 | Algorithm trust & depth (known-value validation matrix / multivariate SPC · change-point detection · residual control charts / conclusion credentials / first closed-loop slice) |
| 🚧 | v4.3.0 | Improvement case & evidence ledger (ImprovementCase lifecycle / MeasurementEvent · plugin data sources / standard version records / evidence view · desensitized sharing) |
| 🚧 | v4.4.0 | Closed-loop execution & effect verification (alert→8D auto case / measurement system online / sampling transfer / benefit ledger · COPQ / skill-constrained line balancing) |
| 🚧 | v4.5.0 | Open ecosystem (MCP server · native tool calling / CLI · SDK quality gate / industry rule packs · plugin scaffold) |
| 🚧 | v4.6.0 | Intelligent online & local data assets (model governance · online scoring / process window recommendation / IE evidence chain / local assets · edge SPC) |

---

## Core Positioning & Moats (2026-09 rework)

> Positioning: personal-subscription quality engineering tool (Minitab-like) → deepening into a "shop-floor improvement evidence-chain tool". No open-source product covers this breadth; the closest alternative is the commercial Datalyzer (~$2593/yr).
> The moat is not feature count but two things: (1) a data model competitors cannot cheaply rewrite — improvement cases plus bitemporal/provenance/confidence grading (scoped to measurements · standards · conclusions, not bitemporal everywhere); (2) data assets that thicken with use (process baselines / gauge health history / benefit ledger / case library).

| # | Pillar | Landscape | Delivered in |
|---|--------|-----------|--------------|
| 1 | **Quality workflow integration** (FMEA→CP→SPC→PPAP→8D data chain) | Open gap | v2.8.0 ✅, ongoing |
| 2 | **Real-time factory integration** (ESP32/MaixCAM native + PLC/CMM/gauge connectors + cloud dashboard) | Minitab needs paid Prolink | v3.7.0 ✅ |
| 3 | **IE tool suite** (SMED/TPM/OEE/8D/FMEA/PPAP/Control Plan) | Minitab has no IE | v2.2.0 ✅ |
| 4 | **QAM Harness** (BYOK agent: 36 tools + offline routing + privacy gate) | Copilot is cloud-only | v3.8.0 ✅ |
| 5 | **Chinese-first + offline desktop** (GB/T built in) | Open gap | Throughout |
| 6 | **Improvement cases & evidence system** (ImprovementCase spine + provenance/confidence grading + replayable conclusions + evidence-pack exchange) | Minitab / Datalyzer have none | v4.2.0–v4.3.0 |
| 7 | **Open interface ecosystem** (MCP server + headless CLI/SDK + industry rule packs) | Open in the AI ecosystem; no de-facto plugin standard | v4.5.0 |

Planning principles:

1. Defect fixes before feature expansion; verify statistics against NIST/literature known values
2. Test baseline only grows; per-file regression + zero ruff warnings are release gates
3. One domain per release; add a Tab only when truly necessary
4. Personal-subscription scope: desktop + real-time device connectivity, no enterprise multi-company platform
5. External capabilities ship as Plugin API v2 plugins (e.g. vision); the main app keeps only the interface
6. **Data-model first**: time (bitemporal), provenance and confidence grading come before feature expansion; every conclusion must be traceable and replayable
7. **Open the engine**: core engines ship through MCP/CLI/SDK; the app keeps the experience and evidence layers
8. **Case first**: every new capability must plug into the improvement loop (measure → analyse → improve → verify → standardise) rather than ship as an isolated tool; existing tools are capabilities inside a case

---

## Version History (condensed)

| Date | Version | Summary |
|------|---------|---------|
| 09-17 | v4.2.0-P0 | **Contracts & test base complete**: `core/evidence.py` (credential schema v1 + data fingerprint + diff) · `core/improvement_case.py` (case schema v0) · `.qap` 1.6 → 1.7 case-section compatibility · `KNOWN_VALUES.md` + `tests/known_values.py` known-value framework · 4 contract test files / 40 cases |
| 09-17 | v4.2.0-plan | **v4.2.0 phased development plan**: P0 contracts → P1 known-value matrix → P2 algorithm depth → P3 stability → P4 credentials & method docs → P5 first closed-loop slice → P6 wrap-up; no new hard dependencies (statsmodels is a test-only reference); `.qap` 1.6 → 1.7 incremental compatibility |
| 09-17 | roadmap-rev | **Plan review revision (vs the GPT critique)**: established "improvement case as the spine, bitemporal as the mechanism" — v4.3 moves from storage-first to case-first (ImprovementCase → MeasurementEvent/plugin data sources → standard versions → evidence pack); v4.2 gains the first vertical closed-loop slice; skill-constrained line balancing moves from v4.6 up to v4.4; case closure now requires re-measurement + statistical verdict; anonymous benchmarking is demoted to a server-stage candidate |
| 09-17 | roadmap | **v4.2–v4.6 deepening plan**: converged into the five-step line "trust → evidence → closed loop → open → intelligence"; four moat layers defined (bitemporal data model / judgement verification / exchange interfaces / data assets); new items: known-value matrix, change-point detection & residual control charts, conclusion credentials, bitemporal evidence ledger, desensitized evidence pack, alert→8D auto case, measurement-system online, sampling transfer state machine, benefit ledger & COPQ, MCP server, CLI·SDK, industry rule packs, process window, IE evidence chain, anonymous benchmark, edge SPC |
| 09-15 | v4.1.0 | **Chart & UI experience unification released**: B1 `output/chart_style.py` unified style layer (dark/light themes + Okabe-Ito semantic colours + smart y-limits / violation markers / limit lines) migrated across both chart entry points; B2 all 8 audit findings cleared (auto-faceted boxplots, Pareto 80% line + bar labels, outside control-chart legend + rule annotations, capability stats card, diverging heatmap with masked diagonal…); B3 global command palette (Ctrl+K/Ctrl+P), stepwise batch analysis with progress/cancel (Ctrl+Shift+B), Toast wiring, unified empty state; B4 type modernisation (whole UP family + RUF013, 155 files), hotspot split (main_window/tools_ext → two helper modules), performance baseline in CI (cold start 2.2s / 1M import 14.0s / 5k chart 1.5s / 5k-row ML 1.5s); version 4.1.0 across all four ends; 124 files / 1708 passed / 2 skipped / 0 failed, ruff clean; **source prerelease (no installers)** |
| 09-13 | v4.0.0 | **Predictive Analytics & ML released**: `analysis/ml/` (task detection + leak-proof Pipeline, CART pre/post pruning, Random Forests with OOB, HistGradientBoosting with optional XGBoost, pure-numpy MARS, SHAP explanation, AutoML ranking); new "Predictive Analytics" tab (37) + 6 agent tools (30 → 36) + `.qamodel` save/load/predict; version 4.0.0 across all four ends; 1665 passed / 2 skipped / 0 failed, ruff clean; Linux AppImage + .deb built, Windows installer produced by the Inno script on Windows |
| 09-13 | v4.0.0-quality | **Full code-quality review**: ruff gate extended and driven to zero (T10/ISC/PIE/RUF012/RUF021/RUF034/RUF059/PLW1510/PLW2901/PLW0602); 12 real defects fixed (fishbone duplicate condition, loop-variable shadowing x2, bogus global declaration, redundant branches in SMED/cost/sampling/project manager, unused unpacking in DOE/regression/charts, startswith merged x3, explicit subprocess check); `ClassVar` annotations for class-level mutable constants; repo hygiene (untrack `test_quality.db` and stale compliance docx artifacts); full per-file regression 118 files green + packaging smoke passed |
| 09-13 | v4.0.0-fix2 | **Shared scroll-area height fix (W58 recurrence)**: the `QStackedWidget` size hint now follows only the current page, so hidden tabs (parameter panels / data tables) no longer stretch the shared scroll area; switching tabs explicitly recomputes the range and scrolls to top (staged syncs at 0/120/260 ms to beat Qt's cached hints); canvas-less analysis pages record and restore their page height so switching back keeps the scroll range; 2 new regression cases |
| 09-13 | v4.0.0-fix | **QAM Harness connection detection fix**: any cloud provider with a stored key now counts as connected, so opening the chat no longer shows the false "no API connected" prompt; the connected provider is auto-selected and persisted as `llm_active_provider`; the provider combo populates with signals blocked (no spurious switch back to Ollama); 5 new regression cases |
| 09-13 | v4.0.0-dev | **Predictive analytics & ML P0-P4**: `analysis/ml/` (common/prep/trees/evaluate/forest/boosting/explain/mars/automl/train/persist) — task detection + leak-proof Pipeline, CART (pre/post pruning + rules), regression/classification metrics with CV/learning curve/residuals, Random Forests (OOB/permutation importance), HistGradientBoosting (optional XGBoost fallback), SHAP explanation, pure-numpy MARS (beats the linear baseline on Friedman #1), AutoML ranking; new "Predictive Analytics" tab (37: QThread training + `.qamodel` save/load/predict); QAM Harness tools 30 → 36 |
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

## Current Release: v4.1.0 Highlights

- **Chart style layer (B1)**: `output/chart_style.py` as the single style source — dark/light themes, Okabe-Ito colour-blind-safe semantic palette (data/centre/control limit/spec/fit/violation), unified rcParams plus `smart_ylim` / `add_limit_lines` / `mark_violations` / `style_for_export`; chart_engine, chart_generator, heatmap and faceting all migrated
- **Chart defect fixes (B2)**: all 8 audit findings cleared — auto-faceted multi-scale boxplots, Pareto 80% line with bar labels, outside control-chart legend with rule annotations, capability stats card with grade badge, diverging heatmap with masked diagonal, smart time-series y-limits, theme-coupled colours and font/grid unification
- **UI experience (B3)**: global command palette (Ctrl+K / Ctrl+P across 37 tabs + plugins + 16 actions), stepwise batch analysis with progress and cancel (Ctrl+Shift+B), Toast wiring (analysis/export/batch), unified empty state (tabs without data show the import overlay)
- **Quality & performance baseline (B4)**: complete type modernisation (whole UP family + RUF013 cleared), `main_window` / `tools_ext` hotspot split, `tools/benchmark.py` with four metrics gated in CI (tolerance ×4)
- **Quality numbers**: 1708 passed / 2 skipped / 0 failed (124 files, per-file regression); extended ruff gate (incl. all UP rules) clean; **source prerelease (no installers)**

---

## Known Backlog / Candidates

| Item | Note | Owner |
|------|------|-------|
| Manual review of proactive-suggestion accuracy (≥3.5/5) | Needs engineer scoring | User |
| Vision acceptance on real footage (site video + labelled CSV, ≥85% agreement) | Needs site material | Plugin project |
| Release artifacts (AppImage / .deb / Inno) | Not built for v4.1.0; scripts ready for on-demand builds | Optional |
| ImprovementCase object + evidence ledger | Bitemporal narrowed to measurements/standards/conclusions; see v4.3.0 | v4.3.0 |
| Case workspace entry | Reuse Home first; adding a tab requires explicit review | v4.3.0 decision |
| MCP server + native tool calling | Decides the AI-ecosystem position; see v4.5.0 | v4.5.0 |
| Alert→8D auto case / measurement system online / skill-constrained balancing | Reuses alert · MSA · connector-health · line-balance engines | v4.4.0 |
| Full English pack | i18n framework lands in v4.5.0; translation after | v4.5 / later |
| Connector expansion (more PLC/CMM protocols) | Driven by site needs | v4.6.0 B4 |
| Anonymous industry benchmark | Needs server-side aggregation + privacy review; not in this repo's near-term scope | Server stage |

---

## v4.0.0 ✅ Released — Predictive Analytics & ML (2026-09-13)

> Theme: close the gap to Minitab Predictive Analytics-level capability; main app only. Reuse sklearn 1.9 / shap 0.52, no new hard dependencies (XGBoost is an optional adapter).

> **Release status**: P0-P5 complete — version 4.0.0 across all four ends (settings / version_info / Inno / README·INSTALL·ROADMAP·guide);
> full per-file regression 118 files green; extended ruff gate clean; Linux AppImage + .deb built (Windows installer produced by the Inno script on Windows).

### Phases (P0 → P5)

| Phase | Deliverables | Acceptance |
|-------|--------------|------------|
| **P0 Data & contracts** ✅ | `analysis/ml/{__init__,common,prep}.py`: task-type detection (regression/classification), missing values, encoding, binning, standardization, train/test split, K-fold, leak-proof Pipeline | Preprocessing matches sklearn behaviour; `analysis/ml` is Qt-free (layering guard) |
| **P1 CART + evaluation** ✅ | `trees.py` (classification/regression trees, pre-pruning + ccp_alpha post-pruning, rule export); `evaluate.py` (R²/adj-R²/RMSE/MAE/MAPE, Acc/P/R/F1/AUC, confusion matrix, ROC, K-fold CV, learning curve, residual diagnostics) | Same-seed metrics match sklearn within tolerance; both regression and classification covered |
| **P2 Ensembles + explanation** ✅ | `forest.py` (OOB, feature importance, permutation importance); `boosting.py` (HistGradientBoosting primary + optional XGBoost adapter); `explain.py` (SHAP with sampling cap + native-importance fallback + single-sample explanation) | All three models train/evaluate/explain; graceful fallback when XGBoost is absent or SHAP exceeds the cap |
| **P3 MARS + AutoML** ✅ | `mars.py` (pure numpy: forward basis functions + backward pruning + GCV knot selection + interactions); `automl.py` (model zoo CV ranking + time budget + recommendation + leaderboard) | On the Friedman #1 synthetic set MARS is no worse than the linear baseline; AutoML reproducible under the same seed and consistent with manual selection |
| **P4 UI + agent tools** ✅ | "Predictive Analytics" tab (index 37; prepare/train/evaluate/predict + QThread training), `.qamodel` save/load and prediction export, `core/agent/tools_ml.py` with 6 tools (30 → 36) | E2E: prepare→train→evaluate→visualize→predict; offscreen UI tests + real-engine tool tests pass |
| **P5 Release wrap-up** | Sync README (zh/en) / guide.html / this roadmap; version 4.0.0 across all four ends; full per-file regression + packaging smoke | `tools/check_version.py` passes; ruff clean; onedir bundle starts and model inference works |

### Key design decisions

- **Layering**: `analysis/ml/` uses only numpy/pandas/sklearn (no Qt); all UI training runs on a worker thread
- **Leak prevention**: preprocessing is wrapped in an sklearn Pipeline, CV fits inside folds; stratified split for classification
- **Dependencies**: no new hard dependencies; XGBoost optional (auto-fallback), MARS self-implemented to avoid pyearth
- **Model files**: `.qamodel` = joblib + JSON metadata (model/features/metrics/version); only files produced by this tool are loaded
- **Explanation performance**: SHAP capped at ≤300 rows by default (same policy as `analysis/ai/root_cause.py`), falling back to native importance
- **Wiring points** (P4, verified): `ui/_tab_registry.py` (37) · `ui/sidebar.py` quality category · `locales/zh.json` · `analyses[idx]` records · report/PPT export · agent tool registration (`build_default_registry` hook)
- **Out of scope for now**: extending template batch analysis (`core/template_parser.py`) with ML types — candidate item

### Overall acceptance criteria

- CART / Random Forests cross-validated against scikit-learn
- AutoML selection consistent with manual model selection
- End-to-end: data prep → feature engineering → modeling → evaluation → visualization

---

## Upcoming Releases (v4.1.0 → v4.6.0)

> **Main line**: from a "quality analysis tool" to a "shop-floor improvement evidence-chain tool" — with the **ImprovementCase as the spine**: measure → analyse → improve → re-measure → verify → standardise. Make algorithms trustworthy (4.2), then connect cases, data, standards and judgements into a ledger (4.3), execute the closed loop on that ledger (4.4), open the engines through MCP/CLI/rule packs (4.5), then let models and time-accumulated data compound (4.6).
> **Moat layers**: L1 data model (improvement case + bitemporal/provenance/confidence grading, scoped to measurements · standards · conclusions) · L2 judgement verification (known-value matrix + replayable conclusions) · L3 exchange interfaces (.qap evidence pack / desensitized sharing / MCP / rule packs) · L4 data assets (process baselines / gauge health history / benefit ledger / case library).
> **Cadence**: one release every 4–6 weeks, 3–5 items per release, ~20% buffer for user-reported issues; same DoD (per-file regression + extended ruff gate + version consistency + packaging smoke).
> **Boundaries**: in principle no new tabs (the case workspace reuses Home first; adding one requires explicit review); no heavy hard dependencies, no enterprise features; Plugin API 2.x stays backward compatible (new capabilities ship as additive 2.1).
> **Not doing**: enterprise multi-user QMS/MES · generic BI dashboards · home-grown statistical solvers · cloud-dependent SaaS (keeps the offline + trustworthy-evidence differentiation).

### v4.1.0 ✅ Released — Chart & UI Experience Unification (2026-09-15)

> **Release status**: B1–B4 complete, version 4.1.0 across all four ends (settings / version_info / Inno / README·INSTALL·ROADMAP·guide);
> full per-file regression 124 files green; extended ruff gate clean; performance baseline gated in CI; **not packaged — released as a source prerelease (GitHub Source zip / tar.gz)**.

| Batch | Deliverables | Acceptance |
|-------|--------------|------------|
| **B1 Chart style layer** ✅ 2026-09-14 | New `output/chart_style.py` (single source: dark/light themes · Okabe-Ito colour-blind-safe semantic palette · rcParams · `smart_ylim` / `mark_violations` / `add_limit_lines`); migrated `chart_engine` + `chart_generator` + `heatmap`/`faceting`; smart y-limits for control/time-series charts; diverging heatmap with masked diagonal | 16 new tests pass; 10+ chart types share one style; no default colour-cycle leakage; themes switchable (before/after gallery in `TEMP/chart_audit_{before,after_b1}_2026-09-14.png`) |
| **B2 Chart defect fixes** ✅ 2026-09-15 | All 8 audit findings cleared: smart y-limits for time series (B1) · auto-faceted multi-scale boxplots (`box_mode=auto/single/split`) · Pareto 80% reference line + bar labels · control-chart legend moved outside + rule annotations · capability stats card redesign (two metric columns + grade badge) · diverging heatmap with masked diagonal and contrast-aware labels · theme-coupled colours removed · font/grid unified | 22 style/defect tests pass; galleries in `TEMP/chart_audit_{before,after_b1,after_b2}_2026-09-*.png` |
| **B3 UI experience** ✅ 2026-09-15 | Global command palette (Ctrl+K / Ctrl+P: 37 tabs + plugins + 16 common actions) · stepwise batch analysis with progress and cancel (Ctrl+Shift+B) · Toast wiring (analysis done / export / batch summary, suppressed per-tab during batches) · unified empty state (auto "import data" overlay for tabs without data, with a working button) | 15 new tests pass; main flows keyboard-accessible; batch analysis stays responsive and cancellable |
| **B4 Quality & performance baseline** ✅ 2026-09-15 | Type modernisation complete (**whole UP family + RUF013 cleared**: PEP 585/604 annotations, deprecated typing imports, implicit Optional; 154 files) · hotspot split: `ui/main_window_helpers.py` (tab checks / current-page stack / LLM detection) + `core/agent/tool_helpers.py` (shared tool helpers), main_window 2295→2241 and tools_ext 1175→1061 · `tools/benchmark.py` with four metrics (cold start 2.2s / 1M-row import 14.0s / 5k-point chart 1.5s / 5k-row ML train 1.5s) + `perf_baseline.json` + CI step (tolerance ×4, subprocess isolation) | Benchmarks gated in CI; extended ruff gate (incl. all UP rules) clean; full regression green |

### v4.2.0 — Algorithm Trust & Depth (planned)

> Trust layer: first prove the maths is right, then prove how a judgement was made; and validate the case loop with a minimal vertical slice.
> **Phase order**: P0 contracts → P1 known-value matrix → P2 algorithm depth → P3 stability → P4 conclusion credentials & method docs → P5 first closed-loop slice → P6 wrap-up; P1–P3 touch only `analysis/` + `tests/`, P4–P5 touch `core/` + `ui/`, so they can be scheduled in parallel (4–6 weeks total + 20% buffer).

| Phase | Deliverables | Acceptance |
|-------|--------------|------------|
| **P0 Contracts & test base** ✅ 2026-09-17 | Known-value convention `KNOWN_VALUES.md` + framework `tests/known_values.py` · credential schema v1 `core/evidence.py` (data fingerprint `pd-hash-v1` + conclusion diff) · case schema v0 `core/improvement_case.py` · `.qap` 1.7 case section (1.6 read-compatible) | 4 contract test files, 40 cases pass; repo-wide ruff clean; layering guards pass |
| **P1 Known-value matrix** (B1) | NIST StRD / NIST/SEMATECH / literature known values covering SPC · capability · MSA · DOE · reliability · time-series/ML algorithms; tolerance table recorded per case; wired into the per-file CI regression | ≥1 known-value case per critical algorithm; CI green; tolerances auditable |
| **P2 Algorithm depth** (B2) | Multivariate SPC (MEWMA / generalized variance) · change-point detection (PELT, pure numpy) · residual control charts for autocorrelated data · non-normal capability + bootstrap CI · reliability intervals · robust ARIMA auto-ordering | Cross-validated against statsmodels/scipy (test-only optional deps); false alarms on autocorrelated data drop materially |
| **P3 Stability & large samples** (B3) | Large-sample benchmarks (100k / 1M rows SPC·MSA·ML) · ill-conditioned matrix and extreme-value robustness cases · refreshed performance baseline | Benchmarks gated in CI (within tolerance); robustness cases pass |
| **P4 Conclusion credentials + method docs** (B4) | Credentials written into analysis records (`analyses[idx]` / snapshots) · report traceability codes · two-run diff on the same data (report review mode) · guide.html "methods & references" chapter | Re-run diff empty, parameter-change diff visible; traceability code parseable; docs traceable to code |
| **P5 First closed-loop slice** (B5) | Lightweight `.qap` case record v0 + Home workspace entry: baseline → time study → line-balance bottleneck → improvement plan → re-measurement → paired test → conclusion → standard draft; manual/CSV sources, plugin data-source interface reserved | Single-case E2E demo (offscreen E2E + manual script); every step timestamped and data-referenced; old `.qap` untouched |
| **P6 Wrap-up** | Version 4.2.0 across all four ends · README / guide / roadmap sync · full per-file regression + ruff gate · release-mode decision (source prerelease or packaged) | `check_version.py` passes; all green; demo reproducible |

**Key design decisions**: no new hard dependencies (PELT self-implemented; statsmodels as a dev-only reference) · credential and case schemas live in `core/` (Qt-free) · `.qap` stays backward compatible (reads 1.6, writes 1.7) · UI entry reuses Home, no new tab · the full MeasurementEvent contract lands in 4.3.0, with only the interface reserved here.
**Risks & mitigations**: known-value sourcing/licensing (NIST public domain first, literature values cited) · PELT effort (fall back to binary segmentation if over time-box) · closed-loop slice scope creep (1.5-week time box, one case template only) · performance regressions (P3 baseline comparison, revert if out of bounds).

### v4.3.0 — Improvement Case & Evidence Ledger (planned)

> Data-model layer (the most important step): establish the case spine first, then let time, provenance and confidence serve it; bitemporal covers only measurements / standards / conclusions, not the whole database.

| Batch | Deliverables | Acceptance |
|-------|--------------|------------|
| **B1 Improvement case object & lifecycle** | `ImprovementCase` as a first-class object: phases (baseline measure / analyse / improve / re-measure / verify / standardise), baseline data refs, analysis-conclusion refs, improvement plan and implementation records; UI entry reuses Home first (a new tab needs review); old `.qap` files still load | A case replays "problem → improvement → result" end to end; old `.qap` files are untouched |
| **B2 MeasurementEvent contract + plugin data sources** | Unified `MeasurementEvent` (source / method / ts / recorded_at / confidence / validity / raw_ref); device connectors, the vision plugin, manual entry and file imports all emit it; Plugin API 2.1 adds a `data_source` capability (2.0 plugins unaffected) | The vision plugin can inject data into a case; manual/CSV paths work equally |
| **B3 Standard version records** | Spec limits / control limits / standard time / standard work combination sheets / control-plan rows gain `valid_from / valid_to / change_reason` with automatic change history; bitemporal applies only to measurements / standards / conclusions | Any historical lot restores the standard then in force; "who changed what, when and why" is answerable |
| **B4 Evidence view & exchange v1** | Conclusion credentials (rule version + parameters + data fingerprint + event refs) join the ledger; structured append-only audit events (data edits / alert acks / 8D actions / report exports); report traceability code + evidence-chain view; `.qap` evidence-pack export + desensitized share pack (synthetic data + statistical-equivalence statement) | Conclusions replayable; every number in a report points back to events; the share pack has no raw values and can be reviewed independently |

### v4.4.0 — Closed-Loop Execution & Effect Verification (planned)

> Closed-loop layer: quality and IE improvement actions both land on cases; closing a case requires data-verified effects, not paperwork.

| Batch | Deliverables | Acceptance |
|-------|--------------|------------|
| **B1 Alert→8D auto case** | A critical alert auto-generates an 8D draft: data snapshot + violation points + ProjectContext characteristics + FMEA entries; D1–D3 prefilled, D4 left open; D6 must link re-measurement data + a statistical verdict (paired/SPC/capability), not free text | Case opened the moment the exception occurs (≤1 min); closure has data evidence |
| **B2 Measurement system online** | Standard-part/repeat measurements accumulate → rolling repeatability and bias · measurement-process control charts · gauge health score (reusing the connector-health model) · drift beyond limits triggers a re-study prompt | MSA turns from a one-off study into a live state; drift is alarmable |
| **B3 Sampling transfer state machine** | GB/T 2828.1 normal/tightened/reduced transfers per supplier and product line; inspection-lot history remembered; rationale recorded (why this lot was tightened) | Transfer rules execute deterministically; auditable |
| **B4 Benefit ledger & COPQ** | Improvement-case benefit ledger (monthly recompute, consistent standard-version basis, double-count protection) · COPQ in four categories (prevention/appraisal/internal failure/external failure) + ROI; only A/A-/B-confidence data may enter; improvement and appraisal data are separated | Answers "how much did this improvement actually save"; low-confidence data is blocked |
| **B5 Skill-constrained line balancing (case template #2)** | Skill matrix (operator × process × proficiency) plus equipment/headcount constraints feed the LPT solver; output is an executable staffing plan, not just a balance rate; results attach to a case as baseline + re-measurement | A theoretical balance rate becomes a shop-floor-feasible roster under skill constraints; synthetic-data E2E demo |

### v4.5.0 — Open Ecosystem & AI Infrastructure (planned)

> Interface layer: expose the core engines externally so .qap / MCP / rule packs can become exchange standards.

| Batch | Deliverables | Acceptance |
|-------|--------------|------------|
| **B1 MCP server** | Tool registry exposed as an MCP server: Claude Desktop / Cursor / AI IDEs can call SPC · capability · MSA · DOE · ML engines directly; read-only by default + permission model | An external MCP client completes a real analysis in one instruction |
| **B2 Native tool calling** | JSON-Schema tool calling + streaming replaces prompt/regex parsing (fallback kept); better routing and parallel calls | Higher tool hit-rate and stability; the legacy path still works |
| **B3 CLI quality gate + SDK** | `qatool check --spec quality.yaml` (Cpk / rule violations / sampling compliance) · headless report export · `qa-tool-core` local Python SDK | One command yields a CI verdict; embeddable in enterprise systems |
| **B4 Rule packs & plugin ecosystem** | Industry rule packs (IATF / ISO 13485 / IPC / HACCP: judgement rules + sampling + report templates + terminology + alert rules) · plugin scaffold CLI + index + compatibility matrix + 2 sample plugins · i18n framework | A third party ships a plugin in 30 minutes; rule packs import/export cleanly |

### v4.6.0 — Intelligent Online & Data Assets (planned)

> Asset layer: models and time-accumulated data compound; AI moves from "can analyse" to "can advise".

| Batch | Deliverables | Acceptance |
|-------|--------------|------------|
| **B1 Model governance & online scoring** | Model registry / versions / model cards · train → deploy → live-dashboard inference and predictive alerts · drift monitoring · ML in template batch analysis | Models traceable; drift alerts demonstrable; E2E online scoring |
| **B2 Process window recommendation** | DOE response surfaces + ML feature importance + live data → acceptable parameter windows for a quality target (confidence level + sample-size requirement); injection/welding templates | Hit-rate on a frozen validation set; output is an actionable recommendation |
| **B3 IE evidence chain** | IE-flavoured SPC (standard time / cycle time / line-balance stability) · operator-facing standard work sheets and team views · benefits post to the ledger automatically (skill-constrained balancing shipped in 4.4) | IE variation is judgeable; operator views usable; benefits post automatically |
| **B4 Local data assets & edge** | Local process baselines / gauge health history / case library accumulation and search · ESP32 edge judging + offline backlog · connector expansion · lightweight tuning and prediction intervals | Assets thicken with use and stay searchable; no data loss while offline |

> Vision online (invisible measurement, removing observation bias) is delivered by the Vision-expansion plugin; the main app only provides interfaces and the evidence format.

> Anonymous industry benchmarking needs server-side aggregation and privacy review; it is a separate server-stage candidate, not in this repo's near-term batches.

> **After 4.6 (candidates)**: full English localisation · light/high-contrast themes and accessibility · auto-update · subscription & activation · mobile dashboard · multi-site collaboration · server stage (anonymous benchmarks / multi-client aggregation / factory-level dashboard).

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

> No new tabs during v2.6.5 ~ v3.0.0 (deepening focus); v3.8.0 is conversation-first; v4.1.0 ~ v4.6.0 deepen existing capabilities and add no tabs in principle; the case workspace reuses Home first and a new tab requires explicit review.

| Version | Tabs | Change |
|---------|------|--------|
| v2.0 | 28 | Initial (Home / Quality / IE / Charts / Eng / Worksheet / Sampling / Report / Data / Plugins) |
| v2.2 | 32 | +SMED · +TPM · +8D · +PPAP |
| v2.4 | 34 | +Live Monitor · +Multi-Plant |
| v2.5 ~ v2.6 | 35 | +Device Monitoring (Tab 35) |
| v3.3.0 | 36 | +Time Series |
| v3.8.0 | 36 + plugins | Vision tab moved out; plugin tabs get dynamic indices (≥37); QAM Harness is a chat window (not a tab) |
| v4.0.0 | 37 + plugins | +Predictive Analytics (Tab 37); plugin tabs start at 38 |
| v4.1.0 ~ v4.6.0 | 37 + plugins | No new tabs in principle (case workspace reuses Home first; evidence views / online scoring attach to existing tabs and dialogs; vision online stays in the plugin project) |
