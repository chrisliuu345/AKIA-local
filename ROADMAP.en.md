# QA-Tool Roadmap

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> Current: v3.8.0 Industrial AI Agent (QAM Harness + BYOK + Plugin API v2) (✅ 2026-09-12) | Next: **v4.0.0 Predictive Analytics & Machine Learning (planned)** | Tests: 1567 pytest · 36 analysis tabs | Updated: 2026-09-12

---

## Version Roadmap Overview

> **Strategic Repositioning (2026-08-24)**: positioning shifted from enterprise multi-company platform to **personal subscription quality engineering tool** (Minitab-like), with differentiation core in real-time factory data integration + IE engineering tools + five-chain workflow + BYOK AI Agent (QAM Harness). See [Core Competitive Positioning](#core-competitive-positioning-2026-08-rework).

```
v2.0 ──→ v2.1 ✅ ──→ v2.2 ✅ ──→ v2.3 ✅ ──→ v2.4 ✅ ──→ v2.4.1 ✅ ──→ v2.5 ✅ ──→ v2.6.0 ✅ ──→ v2.6.1 ✅ ──→ v2.6.2 ✅ ──→ v2.6.3 ✅ ──→ v2.6.4 ✅ ──→ v2.6.5 ✅ ──→ v2.7.0 ✅ ──→ v2.8.0 ✅ ──→ v2.9.0 ✅ ──→ v3.0.0 ✅ ──→ v3.1.0 ✅ ──→ v3.2.0 ✅ ──→ v3.3.0 ✅ ──→ v3.4.0 ✅ ──→ v3.5.0 ✅ ──→ v3.6.0 ✅ ──→ v3.6.1 ✅(folded into 3.6.0) ──→ v3.7.0 ✅ ──→ v3.7.1 ✅ ──→ v3.7.2 ✅ ──→ v3.8.0 ──→ v4.0.0
```

| Stage | Version | Theme |
|-------|---------|-------|
| Done | v2.0 ~ v3.1.0 | Release → Code+AI → Eng Tools → Reports → Live Monitoring → UX+Anim → HW Expansion → ESP32 Deploy → Security → RBAC+Auth → Stats Hardening → UI Robustness → Defect Cleanup → Stats Engine Deepening → Workflow Integration → Security Restructure → Stabilization → DOE & Power Analysis |
| Done | v3.2.0 | **Linux Port + Dual-System Distribution** (Debian/Ubuntu) |
| Done | v3.3.0 | **Time Series & Forecasting** (ARIMA / Exponential Smoothing / Seasonal Decomposition / Model Comparison) |
| Done | v3.4.0 | **Reliability & Survival Analysis** (Weibull 2P/3P/4P + CI / KM + Cox / ALT / RBD / Crow-AMSAA / Warranty) |
| Done | v3.5.0 | **MSA & Capability Deepening** (Attribute Agreement Enhancement / EMP Method / Gage R&R Enhancement / Capability Sixpack / Auto Capability / Edgeworth Approximation) |
| Done ✅ | v3.6.0 | **Graph Builder Enhancement & Interactive Experience** (chart editor architecture / pie·pareto real-time interaction / heatmap·scatter matrix / small multiples faceting / PPT·PNG·SVG export + thumbnail gallery / help center + menu redesign / integration tests) — code acceptance passed 2026-09-06, release packaging pending |
| Done | v3.6.1 | **Full code-quality audit** (7 latent crash fixes / hazard cleanup / full-repo ruff scan / 72-file regression) |
| Done ✅ | v3.7.0 | **Real-Time SPC Cloud Dashboard & Data Connectors** (P1−P6, 2026-09-08) |
| Done ✅ | v3.7.1 | **Five-chain fixes + data semantics & engineering consistency hardening** (FMEA→CP→SPC bridge fixes + ProjectContext as single source of truth / value-first column typing (measurement & duration columns) + post-clean re-analysis / packaging no longer ships local config, secrets stored as `<key>_enc` / APP_VERSION single source + CI version gate / dead-module cleanup + layer fix) — 2026-09-10 |
| Done ✅ | v3.7.2 | **Realtime-monitoring benchmark polish, 8 items** (live chart USL/LSL + zoom / plant.json visual config editor / alert levels, ack & audit, linked actions / cost-loss analysis / OEE takt-based performance P with downtime reason codes & shift calendar / minute downsampling + tiered retention / connector health page + auto-reconnect / optional dashboard auth) — 2026-09-10 |
| Done ✅ | v3.8.0 | **Industrial AI Agent** (QAM Harness + BYOK + Plugin API v2; vision moved to external plugin project) — 2026-09-12 |
| Merged | v3.9.0 | Merged into v3.8.0 (Video Time Study → Vision AI capability) |
| TBD | v3.9.0 | Predictive Analytics & Machine Learning |
| TBD | v4.1.0 | TBD (defined based on v3.x progress) |

---

## Core Competitive Positioning (2026-08 Rework)

> **Positioning**: personal subscription quality engineering tool (Minitab-like), with differentiation core in real-time factory data integration + IE engineering tools + five-chain workflow + BYOK AI Agent.
> Based on the 2026-08 open-source landscape survey (JASP / Jamovi / Cassini / SigmaExacta / Point85 OEE / pyDOE / R ecosystem qcc·FrF2·gageRR, etc.) and Minitab feature benchmarking: **no open-source project simultaneously covers SPC + capability + MSA + hypothesis testing + DOE + IE tools + FMEA/8D/PPAP + AI + hardware + Chinese in one desktop application.** The only near-complete coverage is the commercial package Datalyzer (~$2,593/year).

### Differentiation Pillars (by uniqueness)

| # | Pillar | Competitor landscape | Deepening track |
|---|--------|----------------------|-----------------|
| 1 | **Quality workflow integration** (FMEA→Control Plan→SPC→PPAP→8D data chain) | Blank: SigmaExacta's three tools are disconnected; Minitab has no such chain | **v2.8.0 (differentiation core)** |
| 2 | **Real-time factory integration** (ESP32/MaixCAM native desktop integration, PLC/CMM/gage data connectors) | Minitab requires separate Prolink + Real-Time SPC purchase; nearly blank in open-source | **v3.6.0 (cloud dashboard + data connectors)** |
| 3 | **IE engineering tool suite** (SMED/TPM/OEE/8D/FMEA/PPAP/control plan) | Minitab has no IE tools; JASP/Cassini lack FMEA/PPAP | **v2.2.0 delivered, ongoing deepening** |
| 4 | **QAM Harness** (BYOK AI Agent, proactive-suggestion type, multi-provider API integration) | Minitab Copilot cloud-only; competitor AI all cloud-dependent or prototype | **v3.7.0** |
| 5 | **Chinese-first + offline desktop** (factory-floor scenarios, GB/T standards built-in) | Blank: no open-source QE tool offers a native Chinese UI | Ongoing guarantee |

### Planning Principles

1. **Numbered-defect fixes first** — major-version iteration starts only after the full W-series cleanup (v2.6.5)
2. **v2.6.5~v3.0.0 deepen, don't expand** — no new Tabs, no standalone feature modules; all effort goes into correctness, depth, and integration of existing capabilities
3. **v3.1.0~v3.5.0 continuous small releases** — each release focuses on one statistical domain (benchmarked against Minitab core capabilities)
4. **v3.5.0+ major feature expansions** — centered on differentiation core (real-time factory / QAM Harness / video study / predictive analytics)
5. **Statistical correctness verified against known values** — every new statistical method must ship unit tests validated on NIST / authoritative published datasets
6. **Test baseline never shrinks** — 537+ is the floor (ratcheted upward per release); full regression every release
7. **Personal subscription positioning** — no enterprise multi-company platform / RBAC tiers / server deployment; focus on desktop standalone + real-time device connectivity

---

> **Archive note (2026-08-24)**: the plan sections for v2.1 ~ v2.5 (Code Quality & AI / Engineering Tools / Report Enhancement / Live Monitoring & Dashboard / ESP32 Hardware Expansion) have been trimmed; the full records remain in the [Version History](#version-history) table at the end of this document.

---

## v2.6.0 ✅ Released — ESP32 Deployment Extension + Device Monitoring Tab

### Deployment Extension (ESP32 Input)
- Firmware v1.1.0 deployed on real hardware: `esp32_in_6cc84055ec48` live on COM3 (MicroPython v1.20 + UART1 remap, 7 channels) — auto-discovery → ONLINE → META → DATA every second verified end-to-end
- Host discovery/monitor is now reset-pulse aware

### Device Monitoring Tab 35 (polished)
- Device cards: type icon/badge, elided name + tooltip, state color dot (online/offline/error), port + heartbeat display, selected-state highlight
- **Stop / Resume monitoring**: dual buttons on the card (disabled-state style); new devices default to monitoring ON; stopped state persists across refreshes; resume re-attaches (serial reopen + board reset + HELLO)
- Live data preview table: 20 rows always visible (doubled from initial), stable Stretch column widths
- One-click import: device sample DataFrame → routed to other analysis tabs (`_route_sheets_to_tabs`)
- Fixes: card text clipping (_ElidedLabel ellipsis), empty-hint overlapping cards, button text clipping

### ESP-32 Config Gating
- `user_config.json` gains `esp32_extension` switch (default on, backward compatible); when off, sidebar hides the device-monitor button and Tab 35 is not loaded
- New in `config/settings.py`: `tab_allowed(idx)` / `esp32_extension_enabled()`

### Packaging & Release Pipeline
> ⚙️ 2026-09-07: build chain switched from Nuitka back to **PyInstaller (onedir)** (`build_pyinstaller.py`); Inno/AppImage/.deb packaging kept, consuming `build/<name>.dist` output; `build_nuitka.py` and the nuitka dependency removed.
- Branding: `assets/logo.ico` (7 sizes) + `version_info.txt` (Windows version resource, reused via PyInstaller --version-file)
- PyInstaller **onedir**: QA-Tool.exe (38MB) + `_internal/` (454MB total), GUI subsystem (no console)
- **Inno Setup installer** (135MB): Chinese UI, admin install to Program Files, "ESP-32 硬件拓展" component page (writes the install-time switch), desktop/start-menu shortcuts, uninstall support
- Linux: `build_appimage.sh` → AppImage; `build_deb.sh` → .deb (version injected from APP_VERSION)
- Tests: 278 (+3 monitoring stop/resume + 5 config gating + bilingual docs)

---

## v2.6.1 ✅ Completed — Security Validation

### Password Policy (`core/password_policy.py`)
- Minimum 8 chars + letters & digits, Chinese validation hints
- Wired into `create_user` / `reset_password` / `change_password` (weak passwords rejected and audited)
- UI sync: settings dialog change-password validation, user-management default password → Pass1234

### Audit Logging (`core/audit.py`)
- Public audit entry (same `~/.qa_tool_audit.log`, UTF-8 append, exceptions swallowed)
- Business events added: data imports (quality/IE/database), single/summary/compliance exports, settings save, data clean, shared project save

### Secret Store (`core/secret_store.py`)
- Windows DPAPI encryption (`dpapi:` prefix, smooth migration from legacy base64)
- DB connection passwords encrypted at rest (was base64 obfuscation)
- SQL connection-string error masking (`sanitize_connection_error`)

> Tests: 278 → 282 (new `tests/test_security_fixes.py`, 4 cases)
>
> Not included: auth hardening (attempts/lockout) and RBAC matrix enforcement → moved to v2.6.2; hardware wrap-up (2 items) → moved to v2.6.2

---

## v2.6.2 — RBAC Matrix + Auth Hardening + Device Reliability (Completed)

> All tasks completed (Commits A-I, b8de78a…84c5945): RBAC guards/menu/sidebar/welcome filtering + auth lockout & forced password change + security fixes W01-W17 + device link C04/C05/C06/C19/W87-W100 + synthetic test data contract fixes + esp32_out real-device verification (COM3, 8 protocol checks passed) + MaixCAM network integration (TCP 192.168.50.46:9000, full end-to-end verification). Code review prerequisite fixes (12/19 Critical, commits ae04c38/d2c7426/53e888d): auth privilege escalation C01/C02/C03/C13/C14, nav_buttons pollution C08, functional/crash C07/C09/C10/C11/C12/C17, synthetic test data C18.

### RBAC Permission Matrix Enforcement (core)
- Goal: make `_ROLE_PERMISSIONS` (admin/dept_admin/analyst/readonly) effective — two-layer "hide + block"
- Permission mapping: import (4 import entries + data Tab), analyze (analysis Tabs + batch F5), clean (clean wizard), export (3 export entries), settings, share_project, view (Tab viewing / display mode F11 / welcome page)
- Key points: `MainWindow._check_permission(action)` unified guard (user=None allows all) → handler blocking + menu greying + shortcut guards + sidebar/welcome role filtering + `_lazy_load_tab` fallback; denial shows dialog and writes audit
- Five bypass paths unified: `_switch_tab` / handler / drag-drop / shortcuts / welcome direct
- New `tests/test_rbac_ui.py`; regression: test_v2_1 / test_main_window / test_extension_gating
- RBAC-coupled UI fixes: W40 plugin Tab double instantiation, W44 refresh_menu text match → action key, W45 hardcoded 35/36 → TAB_REGISTRY, W47 drag-drop audit

### Auth & Security Hardening
- Login attempt limit & lockout (5 failed attempts, persisted) + first-login forced password change (`must_change_password`)
- Legacy users-file migration (W03 `User(**u)` old-field tolerance)
- Security fixes (auth-coupled): W01 change_password audit misleading, W04/W05 audit dual-impl sync & rotation, W06/W07 SQL masking regex & cross-dialect, W08 project_manager dept-name path traversal, W09 log_util singleton cache, W11 login default credentials, W13/W14 user-mgmt return values & prompts, W15 DPAPI silent degradation, W16 compliance template_id validation, W17 Excel formula injection

### Device Link Hardening
- Critical: C04 transport buf sliding-window cap, C05 callback exception isolation, C06 batch_scheduler `_running` set concurrency guard, C19 esp32_out loop body exception guard
- Warning: W87 discovery parallel scan, W88 monitor stop timeout, W89 registry persistence lock, W93 context_builder acceptance type check, W94 batch daily window, W97 esp32_in DS18B20 non-blocking, W98 esp32_in channel init tolerance, W100 esp32 RTC sync

### Hardware Wrap-up (moved from v2.6.1)
- **esp32_out real-device verification** ✅: second board flashed, COMMAND→ACK drives real actuators (LED/relay/servo)
- **MaixCAM** ✅: network transport (TCP/SSH) device integration — firmware/maixcam_server.py deployed on device :9000; PC side TcpTransport/probe_network_device/monitor branch/add-network-device dialog; 18 unit tests + real-device end-to-end verification

### Tests
- T44 sidebar missing `import_db_clicked` signal ✅ (import_db routed via menu QAction + RBAC registration)

---

## v2.6.3 ✅ Completed — Statistical Engine Hardening

> Theme: statistical correctness — the core value of a quality tool. Fixes statistical boundary defects and constant-table errors found in the full-codebase review.
> Tests: 104+ pytest all pass | Fixes: 2 Critical + 29 Warning | 2026-08-21

### Critical Statistical Correctness
- C15 `gage_rr.py` AV/PV constant table: SPC d2 → MSA d2* (n=2 overestimate 25%, n=3 ~13%), add d2* factor table to settings.py
- C16 `chart_generator.py` waterfall cumulative baseline error: i=0 not accumulated causes global offset

### Statistical Boundary Hardening (W18-W39)
- Nelson rules: W18 rule 5 two-point same-side judgment
- Hypothesis tests: W19/W20 paired-test dropna alignment, W27 alt min-sample guard, W28 temperature unit symmetry
- Normality & capability: W21 normaltest n<8, W22 shapiro n=2, W23 std=0 return value, W24 non_normal_cap divide-by-zero, W25 single-obs subgroup, W33 xbar_s magic number
- Control charts: W29 cusum constant column, W30/W31 p/u/c chart validation, W32 ewma initial value μ0
- ANOVA & DOE: W34 anova single-obs group, W35 factorial coding mask, W36 doe shapiro N<3
- Reliability: W26 weibull all-equal degenerate, W37 censored length match
- Sampling: W39 sampling_engine _NORMAL_TABLE vs _AQL_VALS misalignment

### Statistical Output Robustness
- W76 chart empty data, W77 all-zero divide, W78 figure_to_bytes leak, W79 griddata duplicate coords

### IE Statistical Modules
- W10 one_click grr_pct unit, W82 smed improved_time, W85 time_study kstest, W90 data_profiler iloc guard, W92 data_validator kstest degenerate

---

## v2.6.4 ✅ Completed — UI Robustness + Report Safety + Test Quality

> Theme: remaining UI crashes/correctness + output safety + test reliability. Focus on crashes and contract consistency; low-value polish demoted to P2.
> Tests: 289+ pytest all pass | Fixes: 26 code changes | 2026-08-22

### UI Crashes & Correctness (15 items)
- W58 fmea mode-before-confirm → confirm then assign
- W41 _on_import_db connection leak → try/finally
- W53 closeEvent no discovery stop → add _discovery_running=False
- W55 doe overwrites raw data → backup _original_df
- W56 hypothesis factor2 nullable → validate non-empty
- W57 msa part column empty → validate part for linear
- W42 USL/LSL=0 skipped → spec limits checkbox
- W64 oee=None crash → or 0 safe default
- W65 ppap single-point fake Cp → n<2 / σ=0 message
- W66 3P Weibull NaN → post-fit NaN check
- W67 sheet_split dtype=str → remove dtype=str
- W46 F5 full-load freeze → processEvents yield
- W52 background-thread QWidget → signal to main thread
- W68 cellChanged per-keystroke → blockSignals
- W110 batch _refresh_log O(n²) → set incremental

### Output & Reports (5 items)
- W48 base_tab plt.close collateral → plt.close(self.current_figure)
- W75 excel no try/finally → try/finally wb.close()
- W80 word image A4 overflow → min(width, 6.0) proportional
- W71 8D PDF unescaped → html escape
- W107 AnalyzeWorker no try/except → try/except + error dict

### Contract Consistency (4 items)
- W59-W62 current_result triplet unified → smed/time_study standardized
- W43 compliance load_template → try/except + fallback
- W109 root_cause KeyError → .get() safe access
- W111 llm closeEvent block → non-blocking wait

### Test Quality (4 items)
- W101 or True tautology → remove
- W102 zero assertions → add assert
- W105 time.time global replace → mock.patch
- W84 work_sampling z_value hardcoded → scipy.stats.norm.ppf

### Confirmed Already Fixed (7 items)
- W70/W83/W95/W96/W91/W103/W104 → existing guards or no actual issue

---

## v2.6.5 ✅ Done — Numbered-Defect Cleanup + Info Batch #1

> Theme: full W-series cleanup (10 items) + first tech-debt batch. No new features in this release — it establishes a clean baseline for the deepening versions that follow.
> Tests: 450+ pytest all pass | Fixes: 10 W-series + 6 Info items | 2026-08-23

### W-Series Cleanup (10 items, each with a regression test)

| ID | Origin | Issue summary | Action |
|----|--------|---------------|--------|
| W49 | demoted v2.6.4 | Bulk-fill blocks UI | Fix (chunked/async processing) |
| W50 | demoted v2.6.4 | Grubbs label error | Fix |
| W51 | demoted v2.6.4 | Uniform-distribution μ error | Fix |
| W69 | demoted v2.6.4 | Trend analysis has no sampling (large-data stalls) | Fix (auto sampling) |
| W72 | demoted v2.6.4 | Sidebar height issue | Fix |
| W73 | demoted v2.6.4 | Fishbone iteration issue | Fix |
| W74 | demoted v2.6.4 | animate cleanup missing | Fix |
| W99 | demoted v2.6.4 | esp32 transport buf (duplicate of C04) | Re-verify, then close with a recorded note |
| W86 | unassigned | `utils/co401_analysis.py:5` / `co401_round2.py:5` hardcoded `sys.path.insert(0, r"D:\...")` | Fix (remove hardcoded path; move one-off scripts out of `utils/`) |
| W106 | unassigned | `ui/dialogs/import_dialog.py:155` `xl.parse(s, nrows=0)` always returns 0 rows | Fix (column-name read logic) |

### Info Cleanup Batch #1 (~50 items)
- Dead code removal + unused imports (tool-assisted scan + manual review)

### Acceptance Criteria
- Open W-series items = 0 ✅ (W99 re-verified and closed on record)
- ≥10 new regression tests ✅ (27 W-fix regression tests)
- Full pytest suite passes and stays at or above the 289 baseline ✅ (450+ tests)

---

## v2.7.0 ✅ Completed — Statistical Engine Deepening

> Theme: close the statistical gaps versus Minitab — reinforcing the core value of a quality-analysis tool. The gap list comes from a 2026-08 code-level audit (not guesswork).
> **Quality rule: every new method ships unit tests validated against NIST StRD / AIAG handbook / authoritative published known-value datasets.**
> Status (2026-08-23): P1 (7 engines) + P2 (6 engines with UI integration) + code quality review (9 fixes) complete · 122 new tests · 537+ tests
> Leftovers: 5 P1 UI entries pending (Type 1 / Hotelling T² / TOST / χ² & 2-proportion / distribution fitting; Cpm and Johnson are already live via existing entries) → registered as v2.8.0 pre-tasks; Info batch #2 deferred

### Current Baseline (already present — not rebuilt)
9 control-chart types + Nelson 8 rules · Cp/Cpk/Pp/Ppk + Box-Cox + between/within capability · Gage R&R (crossed/nested) + linearity/bias + attribute agreement Kappa · t-tests / one-&two-way ANOVA / normality / variance / 3 non-parametric · full factorial + CCD + Box-Behnken · linear/multiple regression · Weibull 2P/3P + MTBF + ALT (Arrhenius/IPL) · AQL attribute sampling (GB/T 2828.1)

### P1 Core Gaps (7 items) — ✅ engines all complete

| Area | New method | Planned location |
|------|-----------|------------------|
| MSA | **Type 1 gage study** (Cg/Cgk; single gage × reference part) | `analysis/msa/type1_study.py` |
| Capability | **True Johnson transformation** (SU/SB selection; current code is z-score standardization only, not a real transform) | rework `analysis/capability/non_normal_cap.py` |
| Capability | **Cpm** (Taguchi index; currently only a scattered calc inside time_study, not in the capability engine) | `analysis/capability/normal_cap.py` |
| SPC | **Hotelling T² multivariate chart** (joint multi-characteristic monitoring, T² + Q residual charts) | `analysis/spc/hotelling.py` |
| Hypothesis | **Equivalence testing (TOST)** (1/2-sample mean equivalence) | `analysis/hypothesis/equivalence.py` |
| Hypothesis | **Chi-square goodness/independence + 2-proportion tests** | `analysis/hypothesis/proportion.py` |
| Distribution | **General distribution fitting** (normal/lognormal/exponential/Gamma/Weibull MLE) + AD/KS/chi-square GoF | new `analysis/distribution/fitting.py` |

> UI wiring status: Cpm (auto-shown with capability results once a target is set) ✅ · Johnson (existing capability-Tab method option) ✅ · Type 1 / Hotelling T² / TOST / χ² & 2-proportion / distribution fitting → pending (v2.8.0 pre-tasks)

### P2 Important Gaps (6 items — target this release, may spill to v2.9.0)

| Area | New method | Status |
|------|-----------|--------|
| SPC | Laney P'/U' charts (over-/under-dispersed count data) | ✅ Complete |
| Capability | Non-normal percentile-method indices (transformation-free) | ✅ Complete |
| Statistics | Tolerance intervals (normal / non-parametric) | ✅ Complete |
| Hypothesis | Mood's median test + Friedman test (complete blocks) | ✅ Complete |
| Sampling | Variables sampling (GB/T 6378 / ANSI/ASQ Z1.9) | ✅ Complete |
| Sampling | C=0 sampling plans (zero-defect acceptance) | ✅ Complete |

### P3 Spillover (wrapped up in v2.9.0)
- I-MR-R/BW between-within charts · fractional factorial / Taguchi OA designs · logistic regression · regression residual diagnostic 4-plot · DOE main-effects/interaction/contour plot wiring (contour generator exists but is not wired to the DOE tab)

### Info Cleanup Batch #2 (~50 items) — deferred to the v2.8.0 cycle
- Duplicate-implementation merge + single source of truth (e.g., variance_tests/normality duplication, audit dual implementation)

### Acceptance Criteria
- All new methods pass known-value verification tests ✅
- New methods wired into existing Tabs (MSA/capability/SPC/hypothesis/sampling/chart entries — **no new Tabs**) — P2 fully wired ✅; the 5 remaining P1 entries deferred to v2.8.0 pre-tasks
- Full pytest suite passes ✅ (537+ tests)

---

## v2.8.0 — Workflow Integration ✅ Completed (2026-08-25)

> Theme: connect the FMEA→Control Plan→SPC→PPAP→8D data chain — a differentiation barrier no open-source project implements.
> Completed: shared data model + five-link integration + magic-number constants + 51 regression tests.

### Pre-Tasks (v2.7.0 leftovers) ✅
- **P1 UI wiring (5 entries)**: Type 1 gage study entry in the MSA Tab · Hotelling T² entry in the SPC Tab · TOST and χ²/2-proportion entries in the hypothesis Tab · distribution-fitting entry (chart/capability Tab extension)
- Info batch #2: magic-number constants (RPN/Cpk/MSA/OEE thresholds unified)

### Shared Data Model (foundation) ✅
- New `core/project_context.py`: `QualityCharacteristic` dataclass (characteristic ID / process step / spec limits / unit / data-source binding) + `ProjectContext` project-level context
- Replaces the tab-indexed flat `MainWindow.analyses` dict (compatibility layer for gradual migration)
- .qap serialization extended: FMEA / control plan / 8D engineering data persisted

### Five Integration Links ✅

| # | Link | Implementation | Status |
|---|------|----------------|--------|
| 1 | FMEA → Control Plan | One-click generation of CP rows from high-risk items (AP/RPN threshold): characteristic / control method / reaction plan | ✅ |
| 2 | Control Plan → SPC | CP control items generate an SPC watch list (characteristic + spec limits + chart type pre-configured) | ✅ |
| 3 | Capability/MSA → PPAP | PPAP #8 (MSA) / #11 (initial capability) auto-pull the latest analysis results, replacing manual entry | ✅ |
| 4 | FMEA → 8D D4 | Failure causes/mechanisms injected into the fishbone skeleton (replacing hardcoded 6M defaults) | ✅ |
| 5 | 8D D7 → FMEA/CP | "Standards updated" drives FMEA/CP review reminders and revision flags | ✅ |

### Info Cleanup Batch #3
- Magic-number constants ✅ (RPN_CRITICAL=200, RPN_HIGH=100, RPN_MEDIUM=50, SIGNIFICANCE_LEVEL=0.05)
- i18n consistency → deferred to v2.9.0

### Acceptance Criteria ✅
- End-to-end scenario test: import data → FMEA flags high risk → generate CP → SPC monitoring → PPAP auto-fill, one chain with no manual re-entry
- .qap save/open round-trips engineering data (incl. FMEA/CP/8D); legacy .qap files load with backward compatibility
- 51 regression tests all pass (test_project_context 20 + test_generate_cp_rows 12 + test_qap_roundtrip 6 + test_five_chain 13)

---

## v2.9.0 — Security Architecture Refactor + Offline License System (TBD)

> Theme: remove RBAC auth system → implement offline license verification → migrate build to Nuitka.
> Positioning: prepare for commercial licensing while significantly improving anti-cracking capabilities.

### Phase 1: Remove Auth System ✅ Complete

**Delete files**:
- `core/auth.py` (408 lines) — AuthManager, User, 4-tier role permissions
- `core/password_policy.py` (23 lines) — password complexity validation
- `ui/dialogs/login_dialog.py` (239 lines) — login dialog
- `ui/dialogs/user_management_dialog.py` (276 lines) — user management dialog
- `tests/test_auth_hardening.py` — auth hardening tests
- `tests/test_rbac_ui.py` — RBAC UI tests
- `tests/test_security_fixes.py` — security fix tests
- `TEMP/qa-tool-security-fix-backup/` — backup directory

**Simplify files**:
- `core/audit.py` — remove auth audit events, keep general audit
- `ui/main_window.py` — remove 28 `_check_permission` calls + role logic
- `ui/dialogs/settings_dialog.py` — remove account tab
- `ui/sidebar.py` — remove `set_permission_filter`
- `ui/welcome_page.py` — remove `set_permission_filter`
- `main.py` — remove AuthManager + LoginDialog, simplify startup

**Actual**: 15 files, deleted/simplified ~800 lines (main_window.py -192, settings_dialog.py -135, main.py -13, test files -100, 5 files fully deleted -1200)

### Phase 2: Offline License System (Standard Security) ✅ Complete

**Security layers**:

| Layer | Technology | Purpose |
|-------|-----------|---------|
| L1 | Ed25519 asymmetric signing | License unforgeable (no private key in binary) |
| L2 | Hardware fingerprint binding | License bound to specific machine (CPU+board+disk+MAC) |
| L3 | AES-256-GCM encryption | License content encrypted at rest |
| L4 | Runtime integrity checks | Multi-point SHA-256 verification against tampering |
| L5 | Anti-debugging checks | 50+ scattered detection points (sys.gettrace/process scan/timing) |
| L6 | VM/emulator detection | Prevent analysis environments |

**New files**:
- `core/license.py` — main module: hardware ID + Ed25519 verify + integrity
- `core/license_keys.py` — embedded public key (Ed25519 Raw, 32 bytes)
- `core/anti_debug.py` — scattered anti-debugging (67 check points)
- `core/integrity.py` — runtime integrity verification
- `tools/license_generator.py` — offline signing tool (developer, contains private key)
- `ui/dialogs/license_dialog.py` — activation dialog
- `tests/test_license.py` — license unit tests

**Actual**: 7 new files, +900 lines

### Phase 3: Build Migration — Nuitka + PyArmor

**Nuitka compilation**:
- Python → C → native machine code (irreversible decompilation)
- Replaces PyInstaller (.pyc trivially decompiled in seconds)
- Output: 10-50MB exe, 10-20% faster startup

**New/modified files**:
- `build_nuitka.py` — Nuitka build script (supports --onefile / --standalone)
- `requirements.txt` — added nuitka>=4.0

**Build commands**:
```bash
pip install nuitka ziglang
python build_nuitka.py --standalone   # directory mode
python build_nuitka.py --onefile      # single executable
```

**Actual**: 1 new file, +150 lines

### Acceptance Criteria
- Full pytest suite passes ✅
- Nuitka build script created, ready for C compiler setup
- License sign → activate → verify full workflow passes ✅
- Hardware fingerprint binding verified ✅
- Anti-debug checks verified (67 scattered points) ✅

---

## v3.0.0 — Stabilization Milestone (Complete)

> Theme: Info wrap-up + full regression + performance baseline + milestone release.
> Positioning: v3.0.0 closes the "deepening era" — the performance baseline established here becomes the regression gate for every subsequent release (v3.1.0+).

### Scope
- Info series cleaned up — no TODO/FIXME/HACK comments remain
- Performance baselines established and recorded (test_performance.py)
- Bilingual docs synced, version history updated to v3.0.0
- Inno Setup installer version updated to v3.0.0

### Acceptance Criteria
- All C / W / Info numbered items cleared
- Full regression passes; test count at or above the 537 baseline (never lower)
- Performance baselines met and recorded

---

## v3.1.0 ✅ Completed — DOE & Power Analysis

> Theme: complete the full experimental-design chain, benchmarked against Minitab DOE module.
> Position: first release of the v3.x continuous-small-release sequence, focused on a single statistical domain.

### Core Content
- **Screening designs**: Plackett-Burman · Definitive Screening
- **Full/fractional factorial**: 2-level full factorial · 2-level fractional (1/2, 1/4, 1/8) · Center points · Blocking
- **Taguchi designs**: L4/L8/L9/L16/L27 · Nominal-the-best / Larger-is-better / Smaller-is-better · SN ratio
- **Response surface**: Central Composite Design (CCD) · Box-Behnken · Mixture designs (Simplex Centroid/Lattice/Extreme Vertices)
- **Power & Sample Size**: Power analysis for t-test/proportion/variance/ANOVA · Sample-size calculator · OC curves
- **DOE wizard UI**: step-by-step guidance (select design → define factors → generate design table → analyze → response surface)

### Acceptance Criteria
- Plackett-Burman / CCD / Box-Behnken design generation correctness verified against Minitab output
- Power & Sample Size calculations cross-validated with Minitab
- DOE end-to-end test: design generation → data entry → analysis → response-surface visualization

---

## v3.2.0 ✅ Completed — Linux Port + Dual-System Distribution

> Theme: cross-platform port — Linux (Debian/Ubuntu family) support, Windows/Linux dual release.
> Target distros: Debian 13 / elementary OS 8.1 / Ubuntu 22.04+ | From v3.2.0 the license system was dropped; only code-level encryption retained.

### Key Deliverables
- Cross-platform font system (CJK-safe), keyring credential storage on Linux
- AppImage + .deb packaging for Debian/Ubuntu; Windows Inno Setup installer kept in sync
- Runtime/library path handling for both platforms (Nuitka + PyInstaller paths)

---

## v3.3.0 ✅ Completed — Time Series & Forecasting

> Theme: complete full time-series analysis capability, supporting trend forecasting and seasonal decomposition.

### Core Content
- **ARIMA modeling**: automatic p/d/q selection (AIC/BIC optimal) · manual parameter setting · residual diagnostics (ACF/PACF/Q-Q)
- **Exponential smoothing**: single-parameter · double-parameter (Holt linear trend) · Holt-Winters (additive/multiplicative seasonality)
- **ACF/PACF plots**: autocorrelation/partial-autocorrelation visualization · Ljung-Box test · Durbin-Watson statistic
- **Seasonal decomposition**: additive/multiplicative models · trend + seasonal + residual decomposition plots
- **Forecasting UI**: forecast-horizon selection · confidence-interval visualization · multi-model comparison (AIC/BIC ranking)

### Acceptance Criteria
- ARIMA auto-ordering cross-validated with statsmodels
- Holt-Winters forecast results compared with Minitab
- Time-series end-to-end test: data import → ACF/PACF → modeling → forecasting → visualization

---

## v3.4.0 ✅ Completed — Reliability & Survival Analysis

> Theme: complete the full reliability engineering chain, benchmarked against Minitab Reliability module.

### Core Content
- **Weibull analysis enhanced**: Weibull 3P/4P (MLE estimation) · confidence intervals · goodness-of-fit tests · probability plots
- **Survival analysis**: Kaplan-Meier survival curves · Log-rank test · Cox proportional-hazards regression
- **Accelerated Life Testing (ALT)**: Arrhenius / Power Law / Inverse Power Law · ALT test plans · lifetime prediction
- **Warranty analysis**: first-time-failure prediction · warranty-cost estimation · lifetime data regression
- **Reliability Block Diagram (RBD)**: series systems · parallel systems · mixed systems · system reliability calculation
- **MTBF/MTTF**: confidence-interval estimation · growth curves (Crow-AMSAA)

### Acceptance Criteria
- Weibull 3P/4P MLE estimates cross-validated with Minitab
- Kaplan-Meier curves compared with statsmodels
- ALT lifetime prediction validated against authoritative published values

---

## v3.5.0 ✅ Completed — MSA & Capability Deepening

> Theme: deepen measurement-system analysis and process capability to Minitab-level advanced features.

### Core Content
- **Nonparametric capability analysis**: capability assessment without distribution assumption (Edgeworth approximation / data transformation)
- **Automated capability analysis**: automatic best-fit distribution detection → optimal transformation selection → capability metrics output
- **Capability Sixpack**: six-panel chart (control chart + histogram + probability plot + statistics + defect rate + capability chart)
- **Attribute agreement analysis**: Kappa coefficient (Cohen's / Fleiss's) · effective Kappa · bias matrix
- **EMP method gage study**: Wheeler's EMP Crossed · signal criteria · discrimination-grade classification
- **Gage R&R enhanced**: variance-component chart · operator×part interaction plot · uncertainty budget

### Acceptance Criteria
- Nonparametric capability compared with Minitab Nonparametric Capability
- Capability Sixpack six-panel linkage correctness
- EMP method validated against Wheeler published values

---

## v3.6.0 ✅ Completed — Graph Builder Enhancement & Interactive Experience (code acceptance passed 2026-09-06 · release packaging pending)

> Theme: upgrade the existing chart tool to Minitab Graph Builder-level interactive experience.

### Core Content
- **Interactive chart gallery**: thumbnail preview panel (replacing pure dropdown) · category grouping (basic stats / regression / DOE / time series / reliability)
- **Chart editing enhanced**: draggable reference/target lines · data-label display · legend customization · axis formatting
- **Heatmaps & correlation plots**: correlation-matrix heatmap · scatterplot matrix · significance markers
- **Table builder**: drag-and-drop descriptive statistics table · interactive cross-tabs · grouped statistical summaries
- **One-click export**: Excel (.xlsx) · PowerPoint (.pptx) · Word (.docx) · high-resolution PNG/SVG
- **Faceting**: grouping variable → multi-chart grid layout · row/column/facet-wrap faceting
- **Help center (added 2026-09-06)**: user guide migrated from docx to offline HTML (`config/help/guide.html`, opens in browser, commercial help-page layout: fixed sidebar nav + FAQ accordion + print styles; stale content revised to current facts) ✅ · **Full menu redesign**: emoji prefixes removed, misfiled actions relocated (report template→Tools, HTML export→File>Export, template help→Help, duplicate KB search removed), view menu gains Display Mode F11 entry, Help gains User Guide (F1) ✅

### Acceptance Criteria
- Chart gallery load time < 200ms
- Exported file format compatibility verified (Excel/PPT/Word open correctly)
- Interactive edit response latency < 100ms

---

## v3.6.1 — Full Code-Quality Audit & Static-Defect Fixes (Completed · folded into the v3.6.0 release, no separate release)

> Triggered by the multi-round regressions on the v3.6.0 chart-render pipeline: full-repo ruff (F/E/B) + semantic review + serial full regression over 72 test files.

### Fix List
- 7 latent crash paths: taguchi noise inner arrays (missing PB builder + list slice on plain lists), report-template builtins scoped wrong, sampling_engine typing imports, anti_debug local import shadowing (Windows path), tpm/msa/doe undefined-name paths
- Loop-closure bindings (auto_cap / data_validator), exception chaining (secret_store / sql_loader), dead assignments removed (mixture / gage_rr / factorial / johnson / power / regression / icons / fishbone / analysis_card)
- 171 unused imports / f-strings auto-cleaned; explicit `__all__` on analysis.ie / analysis.quality
- TEMP scripts untracked + stray Windows-path junk file removed
- Full regression green: 72 pytest files (serial) + script-style integration assertions (~1300 cases)

### Carried Over (style debt, no runtime impact — ✅ all cleared 2026-09-07, see v3.7.0 prerequisites below)
- 65 unused assignments (F841) / 568 one-line multi-statements (E701/E702) / 20 late imports (E402) / 72 B-class issues — all fixed
- ruff added to dev-requirements + ruff.toml + ci.yml gate (repo-wide zero warnings)

---

## v3.7.0 — Real-Time SPC Cloud Dashboard & Data Connectors (✅ done 2026-09-08)

### Prerequisites ✅ (cleared 2026-09-07)
- F841 ×65, E701/E702 ×568 (ruff format), E402 ×20, B007×38 / B905×31 / B028×2 / B008×1 — zero remaining
- ruff gate live: ruff.toml (F,E9,B,E701,E702,E402) + dev-requirements + ci.yml; full regression passed (73 test files serial + script integration)

> Theme: upgrade ESP32/MaixCAM device framework to Minitab Real-Time SPC-level real-time monitoring capability.

### Core Content
- **Continuous data stream**: ESP32/MaixCAM continuous acquisition → real-time database (SQLite/PostgreSQL)
- **Web real-time dashboard**: FastAPI + WebSocket live control charts · shift/line/station multi-dimensional views
- **OOC/OOS alerts**: control-limit / spec-limit breach instant notification (email/webhook/desktop popup) · Nelson-rule real-time detection
- **Data connector framework (protocol-first + plugin architecture)**: OPC-UA client (covers 95% of factory PLCs) · Modbus TCP/RTU · MQTT subscription (ESP32 / Arduino Opta / Raspberry Pi unified access) · CMM DMIS · gage RS232/USB · driver plugin architecture (one plugin per hardware type, installed on demand)
- **Device abstraction layer**: `DeviceDriver` interface unified abstraction · underlying protocols replaceable · no hardware lock-in
- **Hardware recommendation docs**: Arduino Opta WiFi ($185, industrial CE/UL/DIN-rail, native MQTT/Modbus) or ESP32 ($10-20, prototype validation)
- **Line visualization**: line topology map · station status lights (green/yellow/red) · real-time OEE dashboard

### Acceptance Criteria
- Data-stream latency < 500ms (device → control chart)
- WebSocket concurrency of 50 connections without performance degradation
- PLC/gage connector mock tests pass

## v3.7.2 ✅ Done — Realtime monitoring benchmark polish (2026-09-10)

> From the 2026-09-08 competitor benchmark (9 items). Items **1-8 shipped in
> v3.7.2**; item 9 (multi-site / i18n) stays on the backlog for v3.8.0+.
> Every item landed with regression tests and a 4-way consistent version bump.

> Sources (official pages fetched 2026-09-08):
> [Minitab Real-Time SPC](https://www.minitab.com/en-us/products/real-time-spc/) ·
> [WinSPC (Advantive)](https://www.advantive.com/products/winspc/) ·
> [InfinityQS Enact](https://www.advantive.com/products/infinity-qs-enact/) ·
> [DataLyzer](https://datalyzer.com/) (Minitab first URL 404; used /en-us/products/real-time-spc/)

### Gap matrix (competitor vs QA-Tool v3.7.0)

| Capability | Minitab RTSPC | WinSPC | Enact | DataLyzer | QA-Tool now |
|---|---|---|---|---|---|
| Realtime charts | I-MR/Xbar-R/S/I-MR-R/S/EWMA/P·NP·Laney/C·U·Laney | full set | ✓ | ✓ | live I-MR/XBar-R only |
| Dashboard | cloud auto-update | Plant monitor single view | role dashboards | dashboards/reports | browser dashboard (WS) |
| Data sources | full chain | RS232/USB/files/CSV/Excel/ODBC/OPC/DDE/API 500+ | machines/devices/operators | devices/CMM/DB/PLC auto | plugins Modbus/MQTT/OPC-UA/DMIS/gage |
| Alerts | email/text custom | email/custom programs/machine stop/bidi | email/text/in-app+auto workflows | early warnings | email/webhook/desktop (debounce+cooldown), no ack/actions/SMS |
| Config | **Autoconfigure spreadsheet** | 3-step connect wizard | wizard | modular | hand-edited data/plant.json |
| Roles/permissions | per-role | multi-user | role dashboards | users+site licenses | none |
| Cost/benefit | case studies | **Cost Inspector** ($/unit) | net-content MAV/TNE | ~9% cost cut | none |
| Integrations | SAP DM etc. | MES/ERP/HMI/LIMS API | multi-site cloud | OEE/LIMS/API/DLL/Python | self-host WS/HTTP |

### v3.7.2 delivery list (items 1-8)
1. ✅ Chart upgrade: `LiveSPC.spec_limits()` + `chart_engine._draw_spec_lines` (magenta dotted USL/LSL on I-MR/XBar/P·NP·C·U); dashboard wheel-zoom / drag-pan / double-click reset with OOS points highlighted; desktop `ui/widgets/chart_zoom.py` for live charts reading specs from plant.json
2. ✅ plant.json visual config: `ui/dialogs/plant_config_dialog.py` table editor (rows, USL/LSL, takt, costs, shift) + Excel/CSV template import/export; `plant_to_rows` / `rows_to_plant` / `rows_from_excel` / in-place `reload()` so dashboard & OEE pick up changes live
3. ✅ Alerts: `info/warning/critical` levels (rule override, auto by kind & overshoot) + `alert_journal.py` JSONL retention with ack/ack_by/note + `alert_fired`/`alert_ack` audit + alert-center dialog (level filter, unacked only, ack, CSV export) + linked actions disabled by default; **also fixed** a v3.7.0 defect where email/webhook handlers (plain functions) were called as `h.notify`, silently failing inside the engine
4. ✅ Cost analysis: `core/streaming/cost.py` OOS count × per-unit loss (scrap cost, falling back to unit cost) + downtime minutes × rate; `/api/cost` and a dashboard cost card
5. ✅ Real OEE: takt fields in `core/plant.py` (station wins, line fallback, bottleneck max), shift calendar (`parse_shift` / `shift_seconds_in_window`, midnight-crossing), `core/streaming/downtime.py` reason-code tracking; snapshot now exposes real A/P/Q plus defects / downtime_s / run_time_s / reason, backward compatible (P=1.0 and sample-based A when unconfigured)
6. ✅ Retention & downsampling: `measurements_1m` minute rollups (avg/min/max/count, idempotent recompute), `maintain()` tiered retention, periodic runner maintenance, `/api/history?agg=1m`
7. ✅ Connector health page + auto-reconnect: `connectors/health.py` state machine + exponential backoff (base×2ⁿ capped) + runner backoff skip and timed reconnect + health dialog (runtime status, plugin availability, manual reconnect) + `specs_from_settings` / `create_drivers` wiring user_config.connectors into the StreamBus
8. ✅ Dashboard auth: API token (`Authorization: Bearer` or `?token=`, enforced for HTTP and WS), `dashboard_config()` host binding (non-loopback without a token falls back to loopback unless explicitly allowed), token passthrough in the dashboard page, CLI `--token`
9. ⏳ Multi-site topology view + i18n UI (Enact multi-site / DataLyzer 11 languages) — deferred

> Priority rule: P0(already fixed this round) > 1-5 (functional gaps) > 6-9 (scale gaps);
> compatible with v3.8.0 AI Agent (link items 1/3 into conversational analysis).


---

## v3.8.0 ✅ Released — Industrial AI Agent (QAM Harness + Plugin API) (2026-09-12)

> Theme: build an industrial-grade AI Agent platform, integrating LLM intelligent analysis + vision motion recognition, BYOK model, proactive-suggestion type.
> v3.8.0 Video Time Study has been merged into this version, Vision AI as one of Agent's core capabilities.

### Architecture Design

```
QA-Tool v3.7.0 Industrial AI Agent
    |
    ├── Core Agent Layer
    │   ├── LLM Client (Ollama/OpenAI/DeepSeek)  [existing]
    │   ├── Knowledge Base (TF-IDF RAG)           [existing]
    │   ├── Conversation Manager (multi-turn)
    │   └── Tool Registry
    |
    ├── Vision Capabilities
    │   ├── Camera Input (USB/IP/RTSP/MJPEG)
    │   ├── Frame Processor (OpenCV)
    │   ├── Pose Estimation (MediaPipe)
    │   └── Action Classifier (working/idle/walking/carrying)
    |
    ├── Analysis Tools (Agent-callable)
    │   ├── Quality Analysis (SPC/Capability/MSA)
    │   ├── Time Study (manual+vision)
    │   ├── IE Tools (OEE/SMED/TPM)
    │   └── Root Cause (SHAP) [existing]
    |
    └── Output Layer
        ├── Natural Language Response
        ├── Chart Generation
        └── Report Export
```

### Core Content

**Phase 1: Agent Core (Day 1-2)**
- `core/agent/engine.py` — Agent main loop (LLM invocation + tool dispatch)
- `core/agent/tools.py` — Tool registration and dispatch framework
- `core/agent/conversation.py` — Multi-turn conversation management + context persistence
- `ui/dialogs/agent_dialog.py` — Agent conversation UI

**Phase 2: Vision Infrastructure (Day 3-4)**
- `analysis/vision/camera.py` — Camera input abstraction (USB/IP/RTSP/MJPEG)
- `analysis/vision/processor.py` — Frame processing pipeline
- `analysis/vision/pose.py` — MediaPipe pose estimation (33 landmarks)
- `analysis/vision/action.py` — Action classification (working/idle/walking/carrying)

**Phase 3: Integration (Day 5-6)**
- Agent invokes Vision capabilities (video time study)
- Agent invokes Quality/IE tools
- Natural language response generation (stats-in-plain-English)

**Phase 4: Testing & Polish (Day 7)**
- E2E test: Agent conversation → tool invocation → result return
- Performance optimization: frame processing latency < 100ms
- Documentation update

### BYOK Architecture
- Users configure their own API keys in settings (OpenAI / Anthropic / Google / DeepSeek / Z.ai / KIMI)
- Encrypted key storage (cross-platform secret store)
- Connectivity test

### Knowledge-base RAG
- Built-in quality engineering knowledge base (IE/quality engineering/lean methodology)
- User-extensible
- TF-IDF retrieval (upgradeable to vector search)

### Data Privacy
- First cloud API call triggers privacy dialog (explicitly states data sent to provider)
- User confirmation persisted

### Acceptance Criteria
- 6-provider API key configuration + connectivity test full flow
- Agent conversation: natural language Q&A → tool invocation → result return
- Vision AI: camera preview ≥ 15 FPS, action classification accuracy ≥ 85%
- Proactive suggestion accuracy human review (engineer rating ≥ 3.5/5)
- Data privacy dialog block rate 100%
- Stats-in-plain-English (P-values / Cp / Cpk auto-interpretation)

---

## v3.9.0 — Merged into v3.8.0

> ⚠️ This version has been merged into v3.7.0 Industrial AI Agent.
> Video Time Study (Vision AI) is implemented as Agent core capability in v3.7.0 Phase 2.

---

## v3.9.0 — Predictive Analytics & Machine Learning (TBD)

> Theme: complete Minitab Predictive Analytics-level machine learning capability.

### Core Content
- **CART classification & regression trees**: tree building · pruning (pre/post) · confusion matrix · ROC curve
- **Random Forests**: Bagging + feature randomness · OOB error estimation · feature-importance ranking
- **Gradient Boosting (XGBoost)**: boosting iterations · learning-rate / depth tuning · SHAP feature explanation
- **MARS (Multivariate Adaptive Regression Splines)**: piecewise-linear regression · basis-function selection · interaction detection
- **AutoML model selection**: automatic algorithm trial · AIC/BIC/AUC ranking · optimal model recommendation
- **Feature engineering**: missing-value imputation · binning · encoding · feature crossing · standardization/normalization
- **Model evaluation**: cross-validation · learning curves · overfitting diagnosis · residual analysis

### Acceptance Criteria
- CART/Random Forests cross-validated with scikit-learn
- AutoML automatic model selection consistent with manual selection
- Predictive analytics end-to-end test: data prep → feature engineering → modeling → evaluation → visualization

---

## v4.0.0 — TBD

> Theme: defined based on v3.x actual progress and market feedback.
> Candidate directions: video time study deepening · digital-twin layout simulation · supply-chain quality collaboration · additional hardware integration

---

## Version History

| Date | Version | Content |
|------|---------|---------|
| 09-12 | v3.8.0-release | **Release wrap-up**: Hotelling T² control-limit fix (individual-observation UCL was 0 → Montgomery individual-observation limit; subgroup limit now uses the Tracy-Young-Mason Phase I formula: over-flagging 30% → 0.06% in simulation); dashboard-auth tests switched to ephemeral ports; **packaging smoke caught and fixed a PyInstaller `unittest` exclusion that made the bundle crash on startup** (matplotlib → pyparsing≥3.3 depends on it; regression guard added); version bumped 3.7.2 → 3.8.0 across settings / version_info / Inno / README·INSTALL·ROADMAP·guide; full per-file regression **108 files / 1567 passed / 2 skipped / 0 failed**, ruff clean, PyInstaller onedir build + 25s offscreen launch smoke passed |
| 09-10 | v3.7.2 | Realtime-monitoring benchmark polish (8 items): live chart spec limits + zoom, plant.json visual editor with hot reload, alert levels/ack/journal/actions (plus email-webhook dispatch defect fix), cost-loss estimation, OEE takt-based P with downtime codes & shift calendar, minute downsampling + tiered retention, connector health page with backoff auto-reconnect, optional dashboard token auth. 8 new test files, ruff clean, full per-file regression green |
| 09-10 | v3.7.1 | Defect fixes & hardening: **five-chain bridge fixes** (FMEA→CP index mismatch silently no-op / CP→SPC lazy-load ordering + monitoring list had no UI consumer / 8D read internal tab cache) + ProjectContext as the single source of truth; **data-semantics fixes** (measurement-keyword columns missing from numeric_columns → false import warnings & empty DOE factors; "time"-keyword duration columns mis-typed as timestamp; post-clean numeric_columns always empty via select_dtypes) + new DataParser.refresh_info API; **engineering consistency** (build no longer bundles local user_config.json — ships user_config.default.json and stores secrets as `<key>_enc`; APP_VERSION single source + tools/check_version.py in CI; unified shutdown of alert engine/dashboard thread/stream subscriptions; explicit no-keyring notice on Linux); **structural cleanup** (removed ~950 lines of dead modules anti_debug/integrity/license_keys/license_generator/license_dialog, kept core/license.py shim; font utils moved to core/fonts.py with layering guard test; plugin sidebar shows IPlugin.name; test_integration converted to real pytest cases, run_all_tests moved to tools/) |
| 09-06 | v3.6.0 (addendum) | Help center added: user guide migrated from docx to offline HTML (browser-open, commercial help layout, content revised to current facts) + full menubar redesign (emoji removed, AI/Tools/Help regrouping, F1 guide, F11 display-mode entry) |
| 09-07 | v3.7.0-prereq | Style debt fully cleared (F841 ×65 / E701·E702 ×568 / E402 ×20 / B-class ×72); ruff gate live via ruff.toml + dev-requirements + ci.yml; build chain switched Nuitka → PyInstaller (onedir), Inno/AppImage/.deb kept; 73 test files green |
| 09-06 | v3.6.0 | Graph Builder completed & code-accepted: chart editor architecture / real-time interaction / heatmap·scatter matrix / faceting / export enhancements / help center (guide.html) + full menubar redesign; full quality pass folded in (7 latent crash fixes + ruff cleanup); 73 test files all green; version unified to 3.6.0; release packaging pending |
| 09-06 | v3.6.1 | Full code-quality audit & fixes: 7 latent crash paths (taguchi noise arrays, report templates builtin scope, sampling_engine typing imports, anti_debug local import shadowing, tpm/msa/doe undefined names) + loop-closure bindings + exception chaining + 171 unused imports cleaned + TEMP dir untracked + 72-file serial regression all green |
| 09-06 | v3.6.0 (code) | Graph Builder completed: chart option editor (live params / persistent options) + pie·pareto real-time interaction + heatmap/scatter-matrix + faceting small multiples + PPTX/hi-res PNG/SVG export + thumbnail chart gallery + render-pipeline hardening (canvas swap / hidden toolbar / scroll stability) + integration test suite. Pending manual acceptance before release |
| 09-05 | v3.5.0 | MSA & Capability Deepening completed: Attribute Agreement Enhancement (Fleiss's Kappa + Effective Kappa + Bias Matrix) + EMP Method Gauge Study + Gage R&R Enhancement (Variance Component Chart + Interaction Chart + Uncertainty Budget) + Capability Sixpack + Auto Capability Analysis + Edgeworth Approximation + 100+ tests |
| 09-04 | v3.7.0-planning | Architecture adjustment: v3.7.0 + v3.8.0 merged into Industrial AI Agent (AI + Vision Integration); v3.8.0 Video Time Study as Agent Vision capability implemented in v3.7.0 Phase 2 |
| 09-04 | v3.4.0 | Reliability & Survival Analysis completed: Weibull 2P/3P/4P + CI + KM + Cox + ALT + RBD + Crow-AMSAA + Warranty Analysis + 72 reliability tests |
| 09-01 | v3.3.0 | Time Series & Forecasting completed: ARIMA auto-ordering + Exponential Smoothing + Seasonal Decomposition + Forecasting + E2E tests |
| 09-01 | v3.2.0 | Linux Port completed: cross-platform font system + keyring credential storage + AppImage packaging + dual-system release |
| 08-24 | v3.x-planning | Strategic repositioning: shifted from enterprise multi-company platform to personal subscription quality engineering tool (Minitab-like); deleted old v3.1~v3.6 (enterprise RBAC/cross-platform/HA/security compliance/two-tier governance); re-designed v3.1~v4.0 roadmap (DOE→time series→reliability→MSA→Graph Builder→real-time SPC→QAM Harness→video study→predictive analytics); core competitiveness pillars reduced from 6 to 5 (workflow integration / real-time factory / IE tool suite / QAM Harness / Chinese localization) |
| 08-24 | v3.x-AI-arch | AI architecture decision: pillar 4 redefined from "local LLM" to "AI assistant (cloud API + local model tiered)"; v3.1.0 adds AI API management panel (6-provider GUI config + data privacy prompt); v3.2.0 server adds AI proxy forwarding; v4.0.0 local LLM positioned as enterprise-exclusive |
| 08-23 | v2.7.0 | Completed: P1 phase (7 core features + 4 performance optimizations) + P2 phase (6 items) + Code quality review (9 fixes) + UI integration (4 Tabs: SPC/capability/hypothesis/sampling) · 537+ tests |
| 08-23 | v2.6.5 | Completed: W-series numbered-defect cleanup (W49/W50/W51/W69/W72/W73/W74/W86/W99/W106) + Info batch #1 (dead code/unused imports/state-drift bug fixes) · 450+ tests |
| 08-22 | v2.6.5-planning | Roadmap rework: v2.6.5~v3.0.0 shifted from "feature expansion" to "deepening existing capabilities" (defect cleanup → stats-engine deepening → workflow integration → integration deepening → stabilization); legacy feature items P2-3/P2-4/P2-5/P3-1~P3-5 shelved until after 3.0.0; core competitive positioning established from the open-source landscape survey |
| 08-21 | v2.6.2 | Completed: RBAC permission matrix (guards/menu greying/sidebar/welcome filtering) + auth hardening (login lockout + forced password change) + security fixes W01-W17 + device link C04/C05/C06/C19/W87-W100 + esp32_out real-device verification (COM3, LED/relay/servo ACK) + MaixCAM network integration (TCP :9000 end-to-end) · 296 tests |
| 08-19 | v2.6.1-review | Code review fixes (12 Critical): auth privilege escalation C01/C02/C03/C13/C14 + nav_buttons C08 + functional/crash C07/C09/C10/C11/C12/C17 + synthetic test data C18 · 289 pytest · 44/45 smoke |
| 08-19 | v2.6.1 | Security validation: password policy (≥8 chars + letters/digits, wired in 3 auth paths) + audit logging (core/audit.py public entry + 9 business events) + secret store (DPAPI encryption + SQL connection-string masking) · 282 tests |
| 08-18 | v2.6.0 | Released: ESP32-IN deployment (FW 1.1.0 verified on hardware) + Device Monitoring Tab 35 (stop/resume, 20-row preview, data import) + ESP-32 config gating + PyInstaller onedir + Inno Setup installer · 278 tests |
| 08-18 | v2.5-dev | H2 firmware v1.1.0 live on ESP32 (MicroPython v1.20 + UART1 remap, 7 channels) · H3 esp32_in verified end-to-end on COM3 (discovery→META→DATA→import) · host discovery/monitor now reset-pulse aware · 270+ tests |
| 08-17 | v2.5-dev | Hardware expansion: ESP32 device framework restored (core/devices + DeviceTab 35 + 21 tests) · QMenu GC crash fix re-applied · memory-leak audit (threads clean) · 264 tests |
| 08-15 | v2.4.1 | Released: adaptive dashboard cards + animations (fade/count-up/cross-fade) + display-mode aspect & readability fixes · 215 tests |
| 08-13 | v2.4 | Released: Dashboard E4 complete — KPI extractor / real-time refresh / card layout / formula editor / shop floor display · 136 tests |
| 08-13 | v2.3.1 | Released: UI text display fixes — table headers / status bar elide / welcome cards / menu i18n |
| 08-13 | v2.4-dev | Dashboard Phase 1 done (KPI extractor + real-time refresh + card layout) · Phase 2 done (formula editor + display mode) |
| 08-12 | v2.3 | Released: Report template engine + dialog + HTML export + menu restructure |
| 08-10 | v2.3-dev | Phase B: Report template engine + dialog + HTML self-contained export |
| 08-10 | v2.3-dev | Phase A: 8D fishbone embed + PPAP real-time refresh + engine package exports |
| 08-10 | v2.2 | Released: 32 tabs · SMED/8D/TPM/PPAP · 87 tests · lint-clean |
| 08-10 | v2.2-dev | Review fixes: 3 Critical + 7 Warning (TPM property / animation / chart tab) |
| 08-10 | v2.1 | Released: 87 tests · AI enhanced · Lazy loading · One-click analysis · Column selector fix |
| 08-10 | v2.1-dev | Code audit: 5 bugs · 200+ imports · 60+ dead code · 15 duplicate groups |
| 08-04 | v2.0 | Initial release: 28 tabs · 65 tests · AI assistant · Plugin system |

---

## Sidebar Evolution

> **Note**: no new Tabs during the v2.6.5 ~ v3.0.0 rework period (focus on deepening existing features); the 35-Tab + plugin structure stays unchanged.
> v3.0.0+ new capabilities are preferentially added as entries/modes inside existing Tabs; genuinely new Tabs are defined explicitly in their own version plan.
> v3.7.0 Industrial AI Agent uses conversation-based interaction, no new independent Tab.

```
v2.0 (28)     v2.1 (28)     v2.2 (32)       v2.4 (34)     v2.5/2.6 (35)   v3.0.0 (35)      v3.7.0 (35+Agent)
 Home (0)       Same           Same             Same           Same             Same                Same
 Quality (1-6)  Same           Same             Same           Same             Same                Same
 IE (7-11,21-22) Same          +SMED(29)+TPM(31)  Same         Same             Same                Same
 Charts (12,18-20) Same        Same             Same           Same             Same                Same
 Eng (13-17)     Same         +8D(30)+PPAP(32)   Same           Same             Same                Same
 Worksheet (23-25) Same        Same             Same           Same             Same                Same
 Sampling (26)   Same          Same             Same           Same             Same                Same
 Report (27)     Same          Same             Same           Same             Same                Same
 Data (28)       Same          Same             Same           Same             Same                Same
 —               —             —                Live Monitor (33) Same             Same                Same
 —               —             —                Multi-Plant (34)   Same             Same                Same
 —               —             —                —                 Device (35)      Same                Same
 Plugins (dynamic) Same        Same             Same           Same             Same                Same
 —               —             —                —                 —                Agent Dialog (new)
```
