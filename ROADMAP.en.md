# QA-Tool Roadmap

> [中文](ROADMAP.md) | [English](ROADMAP.en.md)

> Current: v2.6.5 Numbered-Defect Cleanup + Info Batch #1 | Tests: 450+ pytest · 35 Tabs + Plugins | Updated: 2026-08-23

---

## Version Roadmap Overview

> **Roadmap Rework (2026-08-22)**: everything from v2.6.5 onward has been re-planned — shifting from "adding features" to "deepening existing capabilities", organized around core competitive strengths with numbered-defect fixes first. See [Core Competitive Positioning](#core-competitive-positioning-2026-08-rework).

```
v2.0 ──→ v2.1 ✅ ──→ v2.2 ✅ ──→ v2.3 ✅ ──→ v2.4 ✅ ──→ v2.4.1 ✅ ──→ v2.5 ✅ ──→ v2.6.0 ✅ ──→ v2.6.1 ✅ ──→ v2.6.2 ✅ ──→ v2.6.3 ✅ ──→ v2.6.4 ✅ ──→ v2.6.5 ✅ ──→ v2.7.0 ──→ v2.8.0 ──→ v2.9.0 ──→ v3.0.0
```

| Stage | Version | Theme |
|-------|---------|-------|
| Done | v2.0 ~ v2.6.5 | Release → Code+AI → Eng Tools → Reports → Live Monitoring → UX+Anim → HW Expansion → ESP32 Deploy → Security → RBAC+Auth → Stats Hardening → UI Robustness → Defect Cleanup |
| TBD | v2.6.5 | Numbered-defect cleanup + Info batch #1 |
| TBD | v2.7.0 | Statistical engine deepening + Info batch #2 |
| TBD | v2.8.0 | Workflow integration (differentiation core) + Info batch #3 |
| TBD | v2.9.0 | Integration deepening & report pipeline |
| TBD | v3.0.0 | Stabilization milestone + Info wrap-up |

---

## Core Competitive Positioning (2026-08 Rework)

> Based on the 2026-08 open-source landscape survey (JASP / Jamovi / Cassini / SigmaExacta / Point85 OEE / pyDOE / R ecosystem qcc·FrF2·gageRR, etc.): **no open-source project simultaneously covers SPC + capability + MSA + hypothesis testing + DOE + IE tools + FMEA/8D/PPAP + AI + hardware + Chinese in one desktop application.** Closest competitors and their gaps: Cassini (SPC platform) lacks IE/FMEA/PPAP/Chinese; JASP lacks IE/FMEA/hardware/Chinese; SigmaExacta covers only FMEA/8D/PPAP (web PWA); the only near-complete coverage is the commercial package Datalyzer.

### Differentiation Pillars (by uniqueness)

| # | Pillar | Open-source landscape | Deepening track |
|---|--------|----------------------|-----------------|
| 1 | **Quality workflow integration** (FMEA→Control Plan→SPC→PPAP→8D data chain) | Blank: SigmaExacta's three tools are disconnected; no characteristic-level data model exists | **v2.8.0 (differentiation core)** |
| 2 | **Statistical engine depth on par with Minitab** | Fragmented: R packages complete but no GUI; JASP QC coverage narrow | **v2.7.0 (core value)** |
| 3 | **Chinese-first + offline desktop** (factory-floor scenarios) | Blank: no open-source QE tool offers a native Chinese UI | Ongoing guarantee |
| 4 | **Local LLM AI** (Ollama + RAG, offline & auditable) | Competitor AI is all cloud-dependent or prototype-stage | Post-v3.0.0 |
| 5 | **ESP32 hardware integration** (gage/sensor acquisition → SPC) | Nearly blank (only Cassini MQTT / Point85 OPC-UA, both in paid tiers) | Post-v3.0.0 |

### Planning Principles

1. **Numbered-defect fixes first** — major-version iteration starts only after the full W-series cleanup (v2.6.5)
2. **Deepen, don't expand** — v2.6.5~v3.0.0 adds no new Tabs and no standalone feature modules; all effort goes into correctness, depth, and integration of existing capabilities
3. **Statistical correctness verified against known values** — every new statistical method must ship unit tests validated on NIST / authoritative published datasets
4. **Info debt paid in batches** — 151 tech-debt items spread across four batches (v2.6.5 / v2.7.0 / v2.8.0 / v3.0.0) without blocking the main line
5. **Test baseline never shrinks** — 289+ is the floor; full regression every release

---

## v2.1 ✅ Completed — Code Quality & AI Enhancement

### Direction A: Code Quality & Architecture Optimization
- 5 P0 bug fixes (p_chart data swap / PDF watermark / NameError ×3)
- 12 bare-except eliminations, 2 iterrows vectorizations
- Tab lazy loading (TAB_REGISTRY 32 entries + importlib on-demand), startup time halved
- 200+ unused imports cleaned, 60+ dead code removed
- welcome_page 4 dead features fixed, diagnostics apply_all fix
- Tests: 65 → 87 (+22)
- Key fixes: `pd.to_numeric` replaces `select_dtypes`, `removeWidget` prevents Stack index shift, `iloc` for duplicate column safety

### Direction C: AI Intelligence Enhancement
- Knowledge base 99 → 124 entries (+25: SMED/8D/TPM/PPAP/AQL/Weibull/ALT/non-parametric)
- Hybrid search: TF-IDF (0.5) + keyword (0.3) + title (0.2)
- AI Chat V2: 8 preset templates + 20-round history + MD export + QSettings persistence + streaming refresh
- One-click analysis: Profile → Recommend → Execute → AI write-up → PDF/MD
- LLM thread management (closeEvent quit+wait)

### UX Improvements
- Import sheet → auto-route to 21 non-IE tools (sheet_map 22 entries)
- Welcome page dual entry (Sheet / IE Data)
- IE recognition 100+ alias expansion; near-constant column silent suppression
- Version → 2.1, Build exe (36.8MB) with logo + knowledge base

---

## v2.2 ✅ Completed — Engineering Tools Extension

### Phase A: v2.1 Legacy Fixes (9 items)
Plugin index 33, LLM streaming refresh, validate_params complete, animation cleanup, welcome page recent projects, diagnostics apply_all, Chart Tab widget cleanup, data validation, profile_result

### Phase B: New Engineering Tools (4 modules)

| Index | Module | Engine | Tab |
|:--:|------|------|------|
| 29 | SMED | `analysis/ie/smed.py` | `ui/tabs/smed_tab.py` |
| 30 | 8D Problem Solving | `analysis/quality/eight_d_engine.py` | `ui/tabs/eight_d_tab.py` |
| 31 | TPM | `analysis/ie/tpm.py` | `ui/tabs/tpm_tab.py` |
| 32 | PPAP | `analysis/quality/ppap_engine.py` | `ui/tabs/ppap_tab.py` |

**Sidebar**: 32 Tabs (+4 new) · Plugin start index 33

---

## v2.3 ✅ Completed — Report Enhancement

### Phase A: v2.2 Legacy Fixes (4 items)
- A1: 8D D4 page embedded FishboneCanvas (6M skeleton, render_fishbone)
- A2: PPAP status change real-time completion refresh
- A3: PPAP completion unified to engine `completion_pct` (submission-level based)
- A4: `analysis/ie/__init__.py` and `analysis/quality/__init__.py` export new modules

### Phase B: Report System (4 items)

| # | Module | File | Description |
|:--:|------|------|------|
| D1 | Template Engine | `core/report_templates.py` | string.Template, 5 built-in HTML templates |
| D2 | Template Dialog | `ui/dialogs/template_dialog.py` | Select → Preview → Export PDF/Word/HTML |
| D3 | Compliance Report | `output/compliance_report.py` | Framework with IATF/ISO clause references |
| D4 | HTML Export | `output/html_export.py` | matplotlib→base64 inline, self-contained offline HTML |

### Menu Restructure
6 menus: File | Analysis | AI | Tools | View | Help — with categorized submenus covering all 32 tabs

---

## v2.4 ✅ Completed — Real-Time Monitoring & Integration (Direction E)

### E1. File Watcher Real-Time SPC ✅ (1.5 days)
- File change → auto import → update control chart → out-of-spec alert
- Implemented: `core/file_watcher.py` (polling FileMonitor daemon thread + stable-state confirm, Qt-free), `ui/tabs/monitor_tab.py` (index 33)

### E2. Multi-Plant / Multi-Line Comparison ✅ (1 day)
- Same metric multi-line side-by-side · Cp/Cpk comparison · Violation summary
- Implemented: `core/plant_compare.py` (summarize_plant / build_comparison), `ui/tabs/multi_plant_tab.py` (index 34)

### E3. Alert Notification System ✅ (0.5 days)
- Multi-channel alerts (popup / sound / log) · Configurable rules · Alert aggregation / dedup
- Implemented: `core/alert_rules.py` (AlertTracker NEW/ONGOING/CLEARED state machine + AlertLog ring buffer + configurable rules via user_config), MonitorTab alert banner + popup + beep + log panel

### E4. Dashboard UI & Control Enhancement ✅ (3 days) — P2-1/P2-2 moved up from v2.5

**Phase 1:**
- F0: Unified KPI extractor `core/kpi_extractor.py` — fixes 3 broken card metrics (OEE / %GRR / SPC violations had wrong key paths), provides variable namespace for the formula engine
- F1: Real-time refresh — signal-driven (`analysis_completed` → `_notify_dashboard`) + QTimer(5s) polling fallback + auto-refresh toggle
- F2: Custom card layout — show/hide + reorder dialog (`ui/dialogs/layout_dialog.py`), QSettings persistence

**Phase 2:**
- F3: Low-code formula editor (P2-1) — `core/kpi_formula.py` AST whitelist parser (23 attack cases rejected, length/depth guards) + `ui/dialogs/formula_dialog.py`, custom KPI cards with live evaluation
- F4: Shop floor display mode (P2-2) — full-screen dashboard `ui/dialogs/display_mode.py`, big-number KPI tiles (FONT_36B), chart carousel (QTimer 8s), ESC/arrow keys, F11 shortcut

**Status**: Direction E fully implemented — E1/E2/E3 completed (Tabs 33-34, alert system, 215 tests).

**Estimate**: 6 days total (E1 1.5 + E2 1 + E3 0.5 + E4 3) | New Tabs 33-34 | Sidebar 32→34

---

## v2.4.1 ✅ Completed — Dashboard & Display-Mode Visual Enhancement

- **Adaptive card grid**: ≤3 cards → 1 column (560×260) / ≤6 → 2 columns (330×220) / more → 3 columns (240×170); scrollable overflow preserved for many cards
- **Card details**: update timestamp (HH:MM), status color dot (Cpk/OEE/GRR/violations graded red/orange/green), dynamic font sizes per column count
- **Animation infrastructure** `ui/widgets/animate.py`: fade_in / count_up / cross_fade (QPropertyAnimation/QVariantAnimation, InOutCubic), settings toggle (default on, user_config.json)
- **Big-screen**: KPI number count-up + tile fade-in + carousel cross-fade
- **Big-screen chart rendering**: charts rendered at chart-area aspect ratio (deepcopy + set_size_inches, 300ms resize debounce re-render) — fixes stretched/compressed charts with no distortion or clipping
- **Big-screen readability**: chart PNG white background (was dark background with black text)
- **Fixes**: F5 batch analysis DataFrame truth-value ambiguity; skip non-runnable tabs (Dashboard etc.) in batch analysis; duplicate display-mode window guard
- Tests: 201 → 215

---

## v2.5 ✅ Completed — Hardware Expansion (ESP32)

### H1. ESP32 Device Framework ✅ (core/devices + Tab 35)
- JSON-lines serial protocol (utf-8, `\n`-terminated): HELLO→ACK→READY handshake · PING/PONG heartbeat (3s/9s) · DATA/COMMAND/RECOGNITION messages
- `core/devices/`: protocol.py (encode/decode/HandshakeProtocol/Heartbeat), transport.py (SerialTransport daemon read thread), discovery.py (comport scan + HELLO probe), registry.py (state machine + user_config.json persistence), device.py (Device / Esp32InputDevice / Esp32OutputDevice / MaixcamVisionDevice)
- `ui/tabs/device_tab.py` (index 35): device cards + detail tabs (events / data preview / output console / recognition records) + auto-discovery (3s) + import device data to analysis
- Sidebar "监控" group: Live Monitor (33) / Multi-Plant (34) / Device Monitor (35) · Plugin start index 36
- Tests: test_devices.py 30 (all mocked, no hardware)

### H2. MicroPython Firmware ✅ (firmware/esp32_in.py + esp32_out.py, v1.1.0)
- MicroPython **v1.20.0** on-board (official v1.21+ broke `machine.UART(0)`: REPL UART driver never installed → `ESP_ERR_INVALID_STATE`/128B-TX-FIFO stall)
- Both firmware files use **UART1 remapped to the onboard bridge** (`machine.UART(1, tx=1, rx=3)`, 115200) + boot self-announce (HELLO + META) so PC auto-discovery can find the board
- `esp32_in.py`: 7 configurable channels (DS18B20 temp on GPIO4 + 6× ADC 32/33/34/35/36/39, ATTN_11DB) → DATA every 1s · answers HELLO/PING
- `esp32_out.py`: COMMAND `<name>:on/off|duty>` grammar (led GPIO2 / relay GPIO25 digital, servo GPIO13 PWM) → ACK reply
- REPL escape hatch: hold BOOT (GPIO0 low) at power-on → firmware exits, REPL stays available (maintenance path)
- Protocol simulation test (`TEMP/fw_proto_test.py`, fake machine + UART pipe): boot announce / META / HELLO reply / PONG / DATA / COMMAND+ACK all pass
- Flash: copy to board as `main.py` (esptool.py installs MicroPython image only; board: ESP32-D0WD-V3, 4MB, no SPIRAM, no auto-reset quirks — DTR/RTS pulse handled by host code)

### H3. Real-Device Verification (Partially Complete)
- ✅ **esp32_in live on COM3** (`esp32_in_6cc84055ec48`, FW 1.1.0): auto-discovery (HELLO probe + boot announce) → ONLINE → META 7 channels → DATA every 1s · end-to-end verified via `TEMP/e2e_hw_check.py` (hello+pong+meta+data PASS) and device-tab smoke (preview table with channel names/units, one-click import → multi-column DataFrame)
- ⏳ **esp32_out**: firmware + simulated protocol tests pass; flash second board and verify COMMAND→ACK on real actuator pins → **moved to v2.6.1**
- ⏳ **MaixCAM**: network transport (TCP/SSH, no serial) → **moved to v2.6.1**

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
- Branding: `assets/logo.ico` (7 sizes) + `version_info.txt` (2.6.0, Chinese description)
- PyInstaller **onedir**: QA-Tool.exe (38MB) + `_internal/` (454MB total), GUI subsystem (no console)
- **Inno Setup installer** (135MB): Chinese UI, admin install to Program Files, "ESP-32 硬件拓展" component page (writes the install-time switch), desktop/start-menu shortcuts, uninstall support
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

## v2.7.0 — Statistical Engine Deepening (TBD)

> Theme: close the statistical gaps versus Minitab — reinforcing the core value of a quality-analysis tool. The gap list comes from a 2026-08 code-level audit (not guesswork).
> **Quality rule: every new method ships unit tests validated against NIST StRD / AIAG handbook / authoritative published known-value datasets.**

### Current Baseline (already present — not rebuilt)
9 control-chart types + Nelson 8 rules · Cp/Cpk/Pp/Ppk + Box-Cox + between/within capability · Gage R&R (crossed/nested) + linearity/bias + attribute agreement Kappa · t-tests / one-&two-way ANOVA / normality / variance / 3 non-parametric · full factorial + CCD + Box-Behnken · linear/multiple regression · Weibull 2P/3P + MTBF + ALT (Arrhenius/IPL) · AQL attribute sampling (GB/T 2828.1)

### P1 Core Gaps (7 items — mandatory this release)

| Area | New method | Planned location |
|------|-----------|------------------|
| MSA | **Type 1 gage study** (Cg/Cgk; single gage × reference part) | `analysis/msa/type1_study.py` |
| Capability | **True Johnson transformation** (SU/SB selection; current code is z-score standardization only, not a real transform) | rework `analysis/capability/non_normal_cap.py` |
| Capability | **Cpm** (Taguchi index; currently only a scattered calc inside time_study, not in the capability engine) | `analysis/capability/normal_cap.py` |
| SPC | **Hotelling T² multivariate chart** (joint multi-characteristic monitoring, T² + Q residual charts) | `analysis/spc/hotelling.py` |
| Hypothesis | **Equivalence testing (TOST)** (1/2-sample mean equivalence) | `analysis/hypothesis/equivalence.py` |
| Hypothesis | **Chi-square goodness/independence + 2-proportion tests** | `analysis/hypothesis/proportion.py` |
| Distribution | **General distribution fitting** (normal/lognormal/exponential/Gamma/Weibull MLE) + AD/KS/chi-square GoF | new `analysis/distribution/fitting.py` |

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

### Info Cleanup Batch #2 (~50 items)
- Duplicate-implementation merge + single source of truth (e.g., variance_tests/normality duplication, audit dual implementation)

### Acceptance Criteria
- All new methods pass known-value verification tests
- New methods wired into existing Tabs (MSA/capability/SPC/hypothesis/sampling/chart entries — **no new Tabs**)
- Full pytest suite passes

---

## v2.8.0 — Workflow Integration (TBD — Differentiation Core)

> Theme: connect the FMEA→Control Plan→SPC→PPAP→8D data chain — a differentiation barrier no open-source project implements.
> Current state (2026-08 audit): the five engineering Tabs are fully siloed — no shared characteristic-ID data model; PPAP's Cp/Cpk parses manually typed text instead of calling the capability engine; FMEA/CP/8D data is not serialized into .qap (only statistical Tab 1-6 results are); report templates cannot auto-pull analysis results.

### Shared Data Model (foundation)
- New `core/project_context.py`: `QualityCharacteristic` dataclass (characteristic ID / process step / spec limits / unit / data-source binding) + `ProjectContext` project-level context
- Replaces the tab-indexed flat `MainWindow.analyses` dict (compatibility layer for gradual migration)
- .qap serialization extended: FMEA / control plan / 8D engineering data persisted

### Five Integration Links

| # | Link | Implementation |
|---|------|----------------|
| 1 | FMEA → Control Plan | One-click generation of CP rows from high-risk items (AP/RPN threshold): characteristic / control method / reaction plan |
| 2 | Control Plan → SPC | CP control items generate an SPC watch list (characteristic + spec limits + chart type pre-configured) |
| 3 | Capability/MSA → PPAP | PPAP #8 (MSA) / #11 (initial capability) auto-pull the latest analysis results, replacing manual entry |
| 4 | FMEA → 8D D4 | Failure causes/mechanisms injected into the fishbone skeleton (replacing hardcoded 6M defaults) |
| 5 | 8D D7 → FMEA/CP | "Standards updated" drives FMEA/CP review reminders and revision flags |

### Info Cleanup Batch #3 (~51 items)
- i18n consistency + magic-number constants + private-API replacement

### Acceptance Criteria
- End-to-end scenario test: import data → FMEA flags high risk → generate CP → SPC monitoring → PPAP auto-fill, one chain with no manual re-entry
- .qap save/open round-trips engineering data (incl. FMEA/CP/8D); legacy .qap files load with backward compatibility

---

## v2.9.0 — Integration Deepening & Report Pipeline (TBD)

> Theme: cross-module result reuse + report auto-aggregation + v2.7.0 P3 spillover wrap-up.

### Report Pipeline
- Report template auto-aggregation: one-click pull of latest Cpk / %GRR / SPC violations / 8D status / PPAP completion into the template context (currently callers must build the context dict manually)

### Cross-Tab Result Reuse
- SPC ↔ capability share σ (one computation per dataset; control-state vs summary-state unified)
- MSA measurement error injected into capability analysis (measurement-uncertainty-corrected Cpk, optional toggle)

### v2.7.0 P3 Wrap-up
- I-MR-R/BW charts · fractional factorial / Taguchi designs · logistic regression · residual diagnostic 4-plot

### Acceptance Criteria
- Integration tests cover all integration links (v2.8.0's five links + report aggregation)
- Full pytest suite passes

---

## v3.0.0 — Stabilization Milestone (TBD)

> Theme: Info wrap-up + full regression + performance baseline + milestone release.

### Scope
- Info-series cleanup wrap-up (remaining items) + full regression verification
- Performance baselines and regression gates: startup time / large-file (100k-row) import time / peak memory
- Bilingual doc sync (README / ROADMAP / CONTRIBUTING) + version-history table archived
- PyInstaller + Inno Setup installer release

### Acceptance Criteria
- All C / W / Info numbered items cleared
- Full regression passes; test count at or above the 289 baseline (never lower)
- Performance baselines met and recorded

---

## Post-3.0.0 Backlog (registered only — not scheduled)

### Core-Competitiveness Extensions (evaluate after 3.0.0)
- **AI deepening**: upgrade the local LLM from "chat assistant" to "whole-analysis interpretation engine" — auto-generated engineering interpretation for every analysis result, anomaly diagnosis suggestions, knowledge-base linkage (staying offline & auditable)
- **Hardware deepening**: ESP32 device acquisition → real-time SPC closed loop (acquire → control chart → alert → COMMAND feedback), wireless gage acquisition, more sensor types

### Shelved Legacy Plan Items (2026-08-22 rework decision)
- P2-3 Video time study (MediaPipe/OpenCV pose estimation)
- P2-4 Batch macro record/replay
- P2-5 Custom control-chart templates (note: v2.8.0's "CP→SPC pre-configuration" link covers its core scenario)
- P3-1 Supply-chain quality collaboration · P3-2 Digital twin layout simulation · P3-3 REST API service · P3-4 Web frontend · P3-5 Mobile app

---

## Sidebar Evolution

> **Note**: no new Tabs during the v2.6.5 ~ v3.0.0 rework period (focus on deepening existing features); the 35-Tab + plugin structure stays unchanged.

```
v2.0 (28)     v2.1 (28)     v2.2 (32)       v2.4 (34)     v2.5/2.6 (35)   v2.6.5~3.0.0 (35)
 Home (0)       Same           Same             Same           Same
 Quality (1-6)  Same           Same             Same           Same
 IE (7-11,21-22) Same          +SMED(29)+TPM(31)  Same         Same
 Charts (12,18-20) Same        Same             Same           Same
 Eng (13-17)     Same         +8D(30)+PPAP(32)   Same           Same
 Worksheet (23-25) Same        Same             Same           Same
 Sampling (26)   Same          Same             Same           Same
 Report (27)     Same          Same             Same           Same
 Data (28)       Same          Same             Same           Same
 —               —             —                Live Monitor (33) Same
 —               —             —                Multi-Plant (34)   Same
 —               —             —                —                 Device (35)
 Plugins (dynamic) Same        Same             Same             Same
```

---

## Version History

| Date | Version | Content |
|------|---------|---------|
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
