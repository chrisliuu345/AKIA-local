# AKIA Roadmap

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> Current: v4.3.0 Improvement cases & evidence ledger (case lifecycle / measurement channels / standard version records / evidence ledger & exchange v1 / lazy-tab startup hardening) (✅ 2026-10-09 release: source + Linux AppImage `AKIA-4.3.0-x86_64.AppImage`) | Latest installers: v4.3.0 Linux AppImage | Next: **v4.4.0 Closed-loop execution & effect verification (planned)**
> Deepening line: **v4.2 Trust → v4.3 Case & evidence → v4.4 Closed loop → v4.5 Open → v4.6 Intelligence** (from analysis tool to a shop-floor improvement evidence chain) | Tests: 2194 passed · 37 analysis tabs | Updated: 2026-10-12
> Status: **v4.3.0 released** (B0 ✅ contracts · B1 ✅ case lifecycle & persistence · B2 ✅ measurement channels & plugin data sources · B3 ✅ standard version records · B4 ✅ evidence ledger & exchange v1 · B5 ✅ integration & quality wrap-up · B6 ✅ release wrap-up & Linux AppImage); `.qap` 1.9 (1.6–1.8 read-compatible) · full per-file regression 178 files / 2194 passed / 0 failed · all 10 benchmark metrics pass · missing matplotlib/seaborn no longer blocks the main window; next up **v4.4.0 Closed-loop execution & effect verification** (plan decomposed → `PLAN_v4.4.0.md`)

> **Maintenance convention (from 2026-09-12)**: each version entry is one summary line plus key numbers; implementation details live in code/tests/user guide, not here.
> This file was compressed from 1100+ lines to under 500; the expanded history is in git history (`git log -p -- ROADMAP.md`).

---

## Version Overview

```
v2.0 ──→ v2.1 ──→ v2.2 ──→ v2.3 ──→ v2.4 ──→ v2.4.1 ──→ v2.5 ──→ v2.6.0 ~ v2.6.5 ──→ v2.7.0
      ──→ v2.8.0 ──→ v2.9.0 ──→ v3.0.0 ──→ v3.1.0 ──→ v3.2.0 ──→ v3.3.0 ──→ v3.4.0 ──→ v3.5.0
      ──→ v3.6.0 (incl. 3.6.1) ──→ v3.7.0 (incl. review) ──→ v3.7.1 ──→ v3.7.2 ──→ v3.8.0 ──→ v4.0.0
      ──→ v4.2.0 ✅ (trust · AppImage published) ──→ v4.2.1 ✅ (quality hardening · source-only)
      ──→ v4.3.0 ✅ current (case·evidence · source + AppImage) ──→ v4.4.0 Closed loop (planned) ──→ v4.5.0 Open (planned) ──→ v4.6.0 Intelligence (planned)
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
| 🔌 | [AKIA-Vision-expansion](https://github.com/chrisliuu345/AKIA-Vision-expansion) | External vision plugin (video time study) built on Plugin API v2 |
| ✅ | **v4.0.0** | **Predictive analytics & ML (CART / Random Forests / gradient boosting / MARS / AutoML + feature engineering / evaluation / SHAP / model deployment)** |
| ✅ | **v4.1.0** | **Chart & UI experience unification (B1 style layer / B2 chart fixes / B3 command palette·batch progress·toasts·empty state / B4 quality & performance baseline)** |
| ✅ | **v4.2.0** | **Algorithm trust & depth (known-value validation matrix / multivariate SPC · change-point detection · residual control charts / conclusion credentials / first closed-loop slice) · Linux AppImage published** |
| ✅ | **v4.2.1** | **Quality hardening & UX fixes (P1–P5: static ratchet / silent-failure governance / numeric robustness / SPC & import vectorisation; AKIA rename wrap-up · new icon · chart-type popup selector · splash removal) · source-only patch** |
| ✅ | **v4.3.0** | **Improvement cases & evidence ledger (B0–B6: case lifecycle / measurement channels + plugin data sources / standard version records / evidence ledger & exchange v1 / lazy-tab startup hardening) · `.qap` 1.9 · +263 tests · source + Linux AppImage published** |
| 🚧 | v4.4.0 | Closed-loop execution & effect verification (alert→8D auto case / measurement system online / trustworthy sampling / benefit ledger · COPQ / skill-constrained line balancing) |
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
| 4 | **QAM Harness** (BYOK agent: 37 tools + offline routing + privacy gate) | Copilot is cloud-only | v3.8.0 ✅ growing |
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
| 10-12 | v4.4.0-plan | **v4.4.0 execution plan (B0–B8)**: contract base (sampling / gauge / benefit / skill schemas + `.qap` 2.0 + ledger event types) → alert→8D auto case → measurement system online → trustworthy sampling (transfer state machine / lot history / scheme trail / decisions in the ledger) → benefit ledger & COPQ → skill-constrained line balancing → sampling-transparency wrap-up → integration & quality wrap-up (incl. v4.3.0 review carry-overs) → release wrap-up; 55–70 person-days total (~12 weeks solo), regression recorded per batch; no feature work before B0 is frozen |
| 10-11 | roadmap-rev | **Trustworthy sampling scheduled**: v4.4.0 B3 expanded into trustworthy sampling — transfer state machine + lot history + scheme trail (incl. manual-override reasons) + sampling decisions in the evidence ledger (method / seed / AQL / sample size / selected-row fingerprint) + method choice; new **B6 sampling-transparency wrap-up** (chart / trend / profiler implicit thinning unified into a sampling-decision record + reproducibility fixes); v4.5.0 rule packs and CLI gate explicitly cover sampling strategies and compliance; minimal reproducibility fix listed as an on-demand candidate |
| 10-09 | **v4.3.0 released** | **Improvement cases & evidence ledger (B0–B6)**: case lifecycle v1 (closure gated by re-measurement + statistical verdict) + CaseWorkflow 8-phase workbench · measurement channels + Plugin API 2.1 `data_source` (5s timeout / bad-data isolation / source enforcement) · standard version records with as-of restore · sha256 evidence ledger + independently verifiable evidence packs + desensitised share packs + 12-digit report trace codes · `.qap` 1.9 (1.6–1.8 read-compatible) · lazy-tab isolation + dependency notice pages so missing matplotlib no longer blocks the main window; full per-file regression **178 files / 2184 passed / 56 skipped / 0 failed**, all 10 benchmark metrics pass (cold start 0.997s vs baseline 2.101s); first release with the unified Linux AppImage name `AKIA-4.3.0-x86_64.AppImage` + `.sha256` |
| 10-02 | **v4.2.1 released (source-only patch)** | **Quality hardening & UX fixes, source only**: the GitHub release ships Source zip / tar.gz (tag `v4.2.1`) and no new AppImage / installers (the latest installers remain v4.2.0); `check_version.py` consistent across all ends (settings / version_info / Inno / docs); full per-file regression **159 files / 1917 passed / 56 skipped / 0 failed**; all 8 benchmark metrics pass (cold start 1.06s vs baseline 2.101s) |
| 10-01 | **Branding & UX wrap-up** | **AKIA rename wrap-up + legacy migration layer** (one-shot migration of QSettings / user config / keyring / `.qamodel` / plugin dirs, with 7 migration tests) · **new app icon** (layered porcelain, 1024 / 256 / ICO sizes, reproducible via `tools/generate_logo.py`) · **fixed** the PyInstaller `--add-data` destination that kept frozen builds from finding the logo / default config · **fixed** the general chart-type selector as a popup panel (Qt.Popup, three fixed columns, no more clipping or squeezing in the narrow config column) · **startup** splash removed — the main window shows immediately (lazy `scipy.stats` / `sqlalchemy` imports + deferred warm-up; cold start 2.10s→1.19s, end-to-end 3.3s→1.35s) |
| 09-28 | **v4.2.1 quality hardening (P1–P5)** | **Full code-quality review + algorithm optimisation (shipped as the v4.2.1 patch)**: **P1 static ratchet** — 11 rule sets (RET505/506 · RUF010/RUF100 · SIM105/113/114/201 · C408/416/420 · PERF102 · PLW0108 · PLW3301) cleared and gated, two dead counters removed (`sampling_engine` write-only `total`, `smed_tab` gantt `y`), 100 files touched · **P2 silent-failure governance** — audit write failures are counted and warned, session/scheduler/one-click/config-migration paths log again, all 31 pass-only handlers now carry a reason; **batch scheduling fixed** (dialog never injected an executor → new Qt-free `run_task_headless`: source → analyses → docx/pdf/xlsx/Markdown report) · **P3 numeric robustness** — new `analysis/_sanitize.py` + `spc/_validation.py`, ±inf/missing values normalised at every analysis entry, six classes of low-level errors fixed (exponential smoothing "No supported index" · count charts NaN/inf conversion · residual chart Ljung-Box IndexError · capability sixpack range-not-finite) · **P4 performance** — vectorised Nelson rules (2100-case equivalence check, 0 diffs) → **SPC 1M points 21.96s → 1.62s (13.5×)**; vectorised per-cell parsing callbacks → **1M-row import 14.27s → 5.19s (2.7×)**, `perf_baseline.json` tightened to lock the gains |
| 09-23 | **v4.2.0 packaged** | **Linux AppImage built + GitHub release delivered**: the historical asset `QA-Tool-4.2.0-x86_64.AppImage` (built by `build_appimage.sh`: PyInstaller onedir → AppDir → appimagetool) plus a `.sha256` checksum file; systems without FUSE launch it via `--appimage-extract-and-run`; README (zh/en) / ROADMAP (zh/en) / guide.html / `docs/releases/v4.2.0.md` now document the release form and verification steps; version stays 4.2.0 (`check_version.py` passes, no API change); the Windows installer is still built on Windows |
| 09-22 | **v4.2.0 released** | **Algorithm trust & depth (source prerelease)**: P0–P6 complete — known-value matrix 29 cases · algorithm depth 60 cases (MEWMA exact per-point Σ_z / generalized variance / PELT changepoints / ARIMA residual chart / non-normal bootstrap CI / reliability interval fix / ARIMA robustness) · benchmarks to 8 metrics + robustness contracts + BLE001 ratchet + coverage backfill · credential loop (analysis records → report trace code → `.qap` 1.8 → re-run diff) + guide "Methods & references" · first improvement closed loop (8-phase case spine + workbench entry) · version across all ends + full gates; full per-file regression **157 files / 1950 cases green**, ruff clean |
| 09-22 | v4.2.0-P2 | **Algorithm depth delivered (7 files / 60 cases)**: MEWMA (Lowry 1992, exact per-point Σ_Z(i) + Phase I/II semantics + optional steady-state form; matches hotelling point-by-point at r=1) · generalized variance chart (Montgomery b1/b2) · PELT changepoint detection (pure numpy, equals brute-force DP optimum, default penalty 2.5σ̂²log n calibrated with fixed seeds) · ARIMA residual control chart (AR(1) false alarms drop markedly) · non-normal capability bootstrap CI (vectorised; small-sample accuracy warning: upward bias below n≈1000) · reliability intervals (Weibull CI cross-checked vs lifelines; **ALT extrapolation interval fixed** — the old form ignored the leverage term, coverage now 0.950) · ARIMA robustness (**crash on series with missing values fixed** — "No supported index"; constant/short-series guards; sample-size-bounded search) |
| 09-17 | v4.2.0-audit | **Full UI feature & wiring audit**: offscreen survey of 37+1 tabs plus receiver scan of every button/menu action (no zero-wiring); 4 gap classes fixed — Time Series/Predictive Analytics missing from worksheet routing · self-contained tools 29-32 blocked by the import overlay · manual/context tools 14/16/17/25/26 blocked (including the FMEA→Control Plan chain) · menu missing entries for 35/36/37; 3 routing-coverage regressions added (all analysis tabs / five-chain unblocked / self-contained tabs clean) |
| 09-17 | fix-ie | **IE tab import wiring fixed**: (1) the empty-state blue button on every tab was connected to the worksheet importer, while worksheet routing skips IE tabs (7-11/21-22) → IE-import tabs (7/9/10/11) now open "Import IE data" and the button label matches; (2) `_tab_has_data` only looked at `df`, but IE data lives in `ie_*` lists → the overlay stayed after a menu IE import; it now recognises IE data and empty states refresh right after import; (3) tabs 8/21/22 are self-contained IE tools (manual/preset driven) and no longer get an import overlay; 6 wiring regression cases added |
| 09-17 | fix-import | **Duplicate-header crash on real report import fixed**: `CO401-20220930.xls` has two "二维码" header columns → after `_apply_header` the frame carried duplicate labels → `df[col]` returned a DataFrame → `pd.to_numeric` raised TypeError; the parser now dedupes columns at `_analyze_frame` entry (`二维码.1`) and records renames in parse info; 4 regression cases added (including the real-world header structure); the real file imports as 722×77 → 589×77 |
| 09-17 | v4.2.0-P1b | **Known-value matrix batch 2 complete**: +9 cases — EWMA / CUSUM / Hotelling T² · Gage R&R (AIAG average-range) · Weibull 2P-MLE (independent brentq solution) · ARIMA(0,1,0) random walk · CART perfect split; P1 totals 12 files / 29 cases, all 7 domains covered |
| 09-17 | fix-ui | **Empty-state "Import data" button fix**: the overlay's `WA_TransparentForMouseEvents` also blocks mouse events for all children, so the button never received clicks; the attribute was removed and a real hit-test + mouse-click regression test added (`widgetAt` locates the button centre, then QTest clicks it) |
| 09-17 | v4.2.0-P1a | **Known-value matrix batch 1**: 20 cases across 7 domains (SPC charts + all 8 Nelson rules / normal capability / Cohen κ / 2² factorial / KM + Crow-AMSAA / sample ACF / regression + classification metrics); **2 real defects found and fixed** — numeric-label confusion matrix all zeros, DOE perfect-fit divide-by-zero warning; tolerance presets extended with `rounded_6dp` / `rounded_4dp` |
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

## Current Release: v4.3.0 Highlights (improvement cases & evidence ledger)

- **Release form**: source + Linux AppImage `AKIA-4.3.0-x86_64.AppImage` (with a `.sha256`
  checksum file, tag `v4.3.0`); the Windows installer is built on Windows (scripts and `.iss` ready)
- **Case as the spine**: `ImprovementCase` v1 state machine (closure gated by re-measurement +
  evidence-backed statistical verdict) · `CaseWorkflow` 8-phase workbench · cases persisted across
  the main window save / load / share paths (G1/G2 fixes)
- **Measurement & plugins**: connector bypass collection + `MeasurementStore` (idempotent / 2000-entry
  FIFO / JSONL recovery) · Plugin API 2.1 `data_source` (5s timeout, bad-data isolation, forced
  `plugin/<id>` provenance)
- **Standards replayable**: spec limits / control limits / standard times / work combinations /
  control-plan entries versioned with change reasons and a timeline; as-of restore; credentials
  follow the standard version
- **Evidence verifiable**: sha256 hash chain over every action (tail corruption recovery) ·
  evidence packs hashed per file and independently verifiable · desensitised share packs
  (parametric synthesis + leak scan) · 12-digit trace code in HTML reports
- **Startup hardening**: lazy-tab isolation + dependency notice pages; missing matplotlib / seaborn
  no longer blocks the main window, missing core dependencies produce an actionable message
- **Gates**: version consistency passed · ruff clean · per-file regression 178 files / 2184 passed /
  56 skipped / 0 failed · all 10 benchmark metrics pass (cold start 0.997s vs baseline 2.101s, ×4 tolerance)
- **Release notes**: [`docs/releases/v4.3.0.md`](docs/releases/v4.3.0.md)

---

## Previous Release: v4.2.1 Highlights (source-only patch, historical)

- **Release form**: **source only** (GitHub Source zip / tar.gz, tag `v4.2.1`) — no new AppImage or
  installers are produced; the latest installers remain v4.2.0 (Linux AppImage published; the
  Windows Inno installer is built on a Windows box)
- **Quality hardening (P1–P5)**: 11 static rule sets gated + dead code removed · silent-failure
  governance (31 pass-only handlers annotated, batch-scheduler executor fixed) · numeric robustness
  (±inf / missing values normalised at every entry, six classes of low-level errors fixed) ·
  vectorisation (**SPC 1M rows 21.96s→1.62s, 1M-row import 14.27s→5.19s**) · regression fix-up
- **Branding & UX**: AKIA rename wrap-up (one-shot legacy migration: QSettings / user config /
  keyring / `.qamodel` / plugin dirs) · new icon (layered lighting + reproducible
  `tools/generate_logo.py`) · chart-type selector as a popup panel (no more clipping or squeezing) ·
  splash removed, cold-start benchmark **2.10s→1.06s** (end-to-end 3.3s→1.35s)
- **Gates**: version consistency passed · ruff clean · per-file regression 159 files / 1917 passed /
  56 skipped / 0 failed · all 8 benchmark metrics pass (cold start 1.06s vs baseline 2.101s, tolerance ×4)
- **Release notes**: [`docs/releases/v4.2.1.md`](docs/releases/v4.2.1.md)

---

## Previous Release: v4.2.0 Highlights (historical)

- **Renamed**: the product is now **AKIA (AKIM IE/Quality analyzer-local)** and the repository
  moved to [chrisliuu345/AKIA-local](https://github.com/chrisliuu345/AKIA-local); the published
  v4.2.0 Linux AppImage keeps its historical asset name `QA-Tool-4.2.0-x86_64.AppImage`,
  later releases use `AKIA-*`

- **Trustworthy algorithms**: 29 known-value cases plus 60 algorithm-depth cases covering MEWMA, generalized variance, PELT changepoints, ARIMA residual charts and non-normal bootstrap CIs; the new algorithms are exposed through QAM Harness (`run_spc` chart types + `detect_changepoints`, 37 local tools)
- **Traceable**: conclusion credentials (rule version + params + data fingerprint + app version) land in analysis records and `.qap` 1.8; reports carry a 12-digit trace code; re-runs produce an item-by-item diff; guide.html "Methods & references" documents 16 method families
- **Closed-loop slice**: the improvement-case workbench drives an 8-phase spine (baseline → time study → line balance → improvement → re-measurement → paired test → conclusion → standard draft) with timestamps, data references and credentials per step
- **Stability**: 8 benchmark metrics (SPC 100k/1M rows, MSA 100k, ML 100k) gated in CI; 22 degenerate-input contracts; `BLE001` blind-except gate enabled for the algorithm layer
- **Release form**: Linux ships AppImage only; the **`v4.2.0` GitHub release** delivers the historical asset `QA-Tool-4.2.0-x86_64.AppImage` (with a `.sha256` checksum file) plus source zip/tar.gz; the Windows installer is built on Windows from `packaging/AKIA-installer.iss`

---

## Earlier Release: v4.1.0 Highlights (historical)

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
| Release artifacts (Windows Inno) | Latest installers are v4.3.0 (Linux AppImage published); the Windows installer needs a Windows box (scripts and .iss are ready) | On demand |
| ImprovementCase object + evidence ledger | ✅ Delivered in v4.3.0 (B0–B6) | Done |
| Case workspace entry | ✅ Delivered in v4.3.0 (Home card + workbench) | Done |
| MCP server + native tool calling | Decides the AI-ecosystem position; see v4.5.0 | v4.5.0 |
| Alert→8D auto case / measurement system online / skill-constrained balancing | Reuses alert · MSA · connector-health · line-balance engines | v4.4.0 |
| Trustworthy sampling (transfer / history / trail / transparency) | Today: normal-inspection AQL table only · `systematic_sample` unseeded · sampling decisions not in the ledger · display-layer thinning unlabelled; a minimal reproducibility fix can ship earlier as an on-demand v4.3.x patch | v4.4.0 B3/B6 |
| Full English pack | i18n framework lands in v4.5.0; translation after | v4.5 / later |
| Connector expansion (more PLC/CMM protocols) | Driven by site needs | v4.6.0 B4 |
| Anonymous industry benchmark | Needs server-side aggregation + privacy review; not in this repo's near-term scope | Server stage |
| FMEA / Control Plan Excel import | Both tables are manual / project-context / five-chain driven; workbook import is not mapped into their table model | Candidate (on demand) |

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

### v4.2.0 — Algorithm Trust & Depth (released)

> Trust layer: first prove the maths is right, then prove how a judgement was made; and validate the case loop with a minimal vertical slice.
> **Phase order**: P0 contracts → P1 known-value matrix → P2 algorithm depth → P3 stability → P4 conclusion credentials & method docs → P5 first closed-loop slice → P6 wrap-up; P1–P3 touch only `analysis/` + `tests/`, P4–P5 touch `core/` + `ui/`, so they can be scheduled in parallel (4–6 weeks total + 20% buffer).
> **Execution breakdown** (target files / acceptance commands / schedule / tech-debt list): see `PLAN_v4.2.0.md` (2026-09-22).

| Phase | Deliverables | Acceptance |
|-------|--------------|------------|
| **P0 Contracts & test base** ✅ 2026-09-17 | Known-value convention `KNOWN_VALUES.md` + framework `tests/known_values.py` · credential schema v1 `core/evidence.py` (data fingerprint `pd-hash-v1` + conclusion diff) · case schema v0 `core/improvement_case.py` · `.qap` 1.7 case section (1.6 read-compatible) | 4 contract test files, 40 cases pass; repo-wide ruff clean; layering guards pass |
| **P1 Known-value matrix** (B1) ✅ 2026-09-17 (batches 1+2) | 29 cases in 12 files across 7 domains: SPC (Xbar-R / I-MR / EWMA / CUSUM / Hotelling T² + all 8 Nelson rules) · capability (Cp/Cpk/Pp/Ppk/Cpm/PPM) · MSA (Cohen κ / Gage R&R average-range) · DOE (2² effects/SS) · reliability (KM / Crow-AMSAA / Weibull 2P-MLE) · time series (ACF / ARIMA random walk) · ML (metrics / CART) | 29 cases green; **2 real defects found and fixed** (numeric-label confusion matrix all zeros; DOE perfect-fit divide-by-zero warning); deeper algorithms (MEWMA / non-normal / Weibull CI / tuning) move to P2 cross-validation |
| **P2 Algorithm depth** (B2) ✅ 2026-09-22 | Multivariate SPC: `analysis/spc/mewma.py` (Lowry 1992, **exact per-point Σ_Z(i)**, `baseline_size` for Phase I/II, switchable steady-state form) · `analysis/spc/gen_var.py` (Montgomery b1/b2) · `analysis/spc/change_point.py` (PELT in pure numpy; K=0 pruning equals the global optimum) · `analysis/spc/residual_chart.py` (ARIMA whitening + I-MR + before/after comparison) · `analysis/capability/non_normal_cap.py::bootstrap_capability_ci` (vectorised percentile bootstrap + small-sample accuracy warning) · reliability intervals (Weibull CI cross-checked vs lifelines · ALT extrapolation interval fixed) · ARIMA auto-order robustness (NaN-index crash fixed, constant/short-series guards, sample-size-bounded search) | 7 new known-value files, 60 cases: MEWMA matches `hotelling.py` point-by-point at r=1, constrained false-alarm rate 0.00267 ≈ α=0.0027; PELT matches brute-force DP optimum with zero false positives on pure noise; residual chart cuts AR(1) false alarms; bootstrap CI coverage 0.94 (n=1500); Weibull β/η coverage 0.940/0.945 with <1% endpoint gap vs lifelines; ALT mean-life CI coverage 0.950 (previously ignored the leverage term); ARIMA no longer crashes on series with missing values |
| **P3 Stability & large samples** (B3) ✅ 2026-09-22 | Benchmark suite extended to 8 metrics (added `spc_100k_rows_s` / `spc_1m_rows_s` / `msa_100k_rows_s` / `ml_train_100k_rows_s`, measured 3.12s / 20.73s / 0.96s / 3.78s) · `tests/test_robustness_numeric.py` (22 cases: inverted limits, degenerate spread, constant/missing-value charts, rank-deficient covariance, single-class classification, zero-variance DOE, single-operator MSA) · coverage backfill `test_core_coverage_gaps.py` (16) + `test_analysis_coverage_gaps.py` (12) for excel_utils / session_manager / audit / base_report_engine / between_within_cap / variance_tests / eight_d_engine · **quality ratchet**: `BLE001` (blind except) now gated, 31 sites in the algorithm and reporting layers justified one by one · deprecation cleanup (websockets legacy connect: 50 warnings eliminated; `main.py` global RuntimeWarning suppression → `once`) | Benchmarks gated in CI and all 8 within tolerance ×4; robustness/coverage cases pass; `ruff check .` clean (with BLE001 enabled); full per-file regression across 154 files green |
| **P4 Conclusion credentials + method docs** (B4) ✅ 2026-09-22 | Credentials written into analysis records (`_store_analysis` → `core/evidence.make_credential`; fingerprints the tab's actual data, degrading to `no-data`) · report traceability code (`credential_trace` + PDF/Word/Excel footers + i18n `report.trace_code`) · review mode (`diff_analysis_records` + automatic `rerun_diff` on re-run) · `.qap` 1.8 credential section (1.6/1.7 read-compatible) · guide.html "Methods & references" (16 method families with sources + credential semantics) | 18 new cases (`test_evidence_wiring.py` 15 + 3 `.qap` credential cases): identical re-run reports `identical=True`, parameter changes visible, trace code order-independent and content-sensitive, Excel footer carries a readable trace code; ruff clean |
| **P5 First closed-loop slice** (B5) ✅ 2026-09-22 | `core/case_workflow.py`: case-spine orchestration over 8 phases (baseline → time study → line-balance bottleneck → improvement → re-measurement → paired test → conclusion → standard draft); every step records **timestamp + data reference + conclusion credential** (reusing P4), wired to the real paired t-test engine (`analysis.hypothesis.t_tests.paired`), with Markdown export and dict round-trip (`.qap` cases section); UI entry: Tools → "Improvement case workbench" + `ui/dialogs/case_workflow_dialog.py` (phase progress, trace preview, Markdown export), seeding the baseline from the currently imported data | `tests/test_case_workflow.py` (14 cases: full 8-phase chain, credential/reference/timestamp traceability, paired test both significant and null, Markdown/dict round-trip, legacy case compatibility, offscreen menu and entry verification); full per-file regression across 157 files green; ruff clean |
| **P6 Wrap-up** ✅ 2026-09-23 | Version 4.2.0 across all four ends · README / guide / roadmap sync · full per-file regression + ruff gate · release-mode decision and execution (09-22 source prerelease → 09-23 packaged: Linux AppImage build + GitHub release + `.sha256`) | `check_version.py` passes; all green; demo reproducible; `bash build_appimage.sh` output launches |

**Key design decisions**: no new hard dependencies (PELT self-implemented; statsmodels as a dev-only reference) · credential and case schemas live in `core/` (Qt-free) · `.qap` stays backward compatible (reads 1.6, writes 1.7) · UI entry reuses Home, no new tab · the full MeasurementEvent contract lands in 4.3.0, with only the interface reserved here · **Linux ships AppImage only (decided 2026-09-22; the `.deb` build chain and `packaging/deb/` were removed)**.
**Risks & mitigations**: known-value sourcing/licensing (NIST public domain first, literature values cited) · PELT effort (fall back to binary segmentation if over time-box) · closed-loop slice scope creep (1.5-week time box, one case template only) · performance regressions (P3 baseline comparison, revert if out of bounds).

### v4.3.0 — Improvement Case & Evidence Ledger (planned)

> Data-model layer (the most important step): establish the case spine first, then let time, provenance and confidence serve it; bitemporal covers only measurements / standards / conclusions, not the whole database.
> **Execution plan** (Chinese): [`PLAN_v4.3.0.md`](PLAN_v4.3.0.md) (2026-10-03).
> **Progress (2026-10-08)**: B0 ✅ contracts (MeasurementEvent / StandardRecord / EvidenceLedger / time semantics / `.qap` 1.9) · B1 ✅ case lifecycle & persistence (ImprovementCase v1 closure gate · case center · actionable workbench · window/shared-project save & restore) · B2 ✅ measurement channels & plugin data sources (connector sink · `query_ref` readback · MeasurementStore + `.qap` `measurements.jsonl` · plugin API 2.1 `data_source` with timeout/bad-data isolation · four-channel workbench intake) · B3 ✅ standard version records (spec/control limits · standard time · work combination · control-plan rows with change reasons · as-of replay · credential `standard_ref` · Tools → standard history timeline) · B4 ✅ evidence ledger & exchange v1 (hash-chain wiring for all actions · evidence view with fingerprint recheck & trace lookup · independently verifiable `.qap` evidence pack · desensitized share pack with leak scan · HTML trace code) · B5 ✅ integration & quality wrap-up (`tools/demo_v43_case.py` one-command E2E · 10 ledger/import performance baselines · migration guide & help section · optional matplotlib at startup); B6 release in progress. Quality: full per-file regression 178 files / 2180 passed / 56 skipped / 0 failed (544.7s) · ruff clean · 10 performance baselines pass (cold start 1.258s).

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
| **B3 Trustworthy sampling (transfer state machine + sampling-decision trail)** | GB/T 2828.1 normal/tightened/reduced transfers per supplier and product line; inspection-lot history; scheme trail (why this lot was tightened / manual-override reason); method choice (random / stratified / systematic / sequential / measurement / C=0); sampling decisions enter the evidence ledger — method · seed · AQL · sample size · selected-row fingerprint | Transfers execute deterministically (same parameters → identical sample rows); any lot's scheme rationale is reconstructable; sampling decisions verify independently from the evidence pack; 1M-row sampling time in the perf baseline |
| **B4 Benefit ledger & COPQ** | Improvement-case benefit ledger (monthly recompute, consistent standard-version basis, double-count protection) · COPQ in four categories (prevention/appraisal/internal failure/external failure) + ROI; only A/A-/B-confidence data may enter; improvement and appraisal data are separated | Answers "how much did this improvement actually save"; low-confidence data is blocked |
| **B5 Skill-constrained line balancing (case template #2)** | Skill matrix (operator × process × proficiency) plus equipment/headcount constraints feed the LPT solver; output is an executable staffing plan, not just a balance rate; results attach to a case as baseline + re-measurement | A theoretical balance rate becomes a shop-floor-feasible roster under skill constraints; synthetic-data E2E demo |
| **B6 Sampling-transparency wrap-up** | Implicit thinning in display / analysis unified into a labelled "sampling decision" record: chart 300-point smart systematic thinning (violations kept) · trend tab 1000 points · large-table normality-test policy (currently skipped); non-reproducible points fixed (e.g. `systematic_sample` without a seed) | Every display / analysis sample has a UI note and a reproducible record; no unlabelled sampling |

### v4.5.0 — Open Ecosystem & AI Infrastructure (planned)

> Interface layer: expose the core engines externally so .qap / MCP / rule packs can become exchange standards.

| Batch | Deliverables | Acceptance |
|-------|--------------|------------|
| **B1 MCP server** | Tool registry exposed as an MCP server: Claude Desktop / Cursor / AI IDEs can call SPC · capability · MSA · DOE · ML engines directly; read-only by default + permission model | An external MCP client completes a real analysis in one instruction |
| **B2 Native tool calling** | JSON-Schema tool calling + streaming replaces prompt/regex parsing (fallback kept); better routing and parallel calls | Higher tool hit-rate and stability; the legacy path still works |
| **B3 CLI quality gate + SDK** | `akia check --spec quality.yaml` (Cpk / rule violations / sampling compliance — judged against the effective scheme and transfer rules, sampling decisions verifiable) · headless report export · `akia-core` local Python SDK | One command yields a CI verdict; embeddable in enterprise systems |
| **B4 Rule packs & plugin ecosystem** | Industry rule packs (IATF / ISO 13485 / IPC / HACCP: judgement rules + sampling strategies (scheme choice / transfer rules) + report templates + terminology + alert rules) · plugin scaffold CLI + index + compatibility matrix + 2 sample plugins · i18n framework | A third party ships a plugin in 30 minutes; rule packs import/export cleanly |

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
- **Build**: PyInstaller onedir (`build_pyinstaller.py`) → Inno (Windows) / AppImage (**sole Linux release format**); `build/` and `dist/` are not committed
- **Tests**: never run `pytest tests/` in bulk (conftest blocks it); run file by file; GUI tests use `QT_QPA_PLATFORM=offscreen`
- **Quality gates**: zero ruff warnings + relevant regression + packaging smoke (required for releases)
- **Layering**: `analysis/` must not import Qt; `core`/`config`/`output` must not import `ui`; `core/agent/` stays Qt-free
- **Plugins**: interact only through `core/plugin_api.py`, API major-version compatible; untrusted plugins are never imported
- **Docs**: keep README (zh/en), the in-app guide (guide.html) and this roadmap in sync
- **New-tab checklist**: registry → worksheet routing (`sheet_map` / `all_indices`) → empty-state class (`_EMPTY_STATE_SKIP` or data-model check) → menu / command-palette entry → regression in `tests/test_tab_data_routing.py`

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
