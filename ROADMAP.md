# QA-Tool Roadmap

> Current: v2.4 | Tests: 136/136 | 32 Tabs + Plugins | Updated: 2026-08-13

---

## Version Roadmap Overview

```
v2.0 ──→ v2.1 ✅ ──→ v2.2 ✅ ──→ v2.3 ✅ ──→ v2.4 ──→ v2.5
 Release   Code+AI    Eng Tools   Reports     Live       Long-term
           (Done)     (Done)      (Done)      (3 days)   (TBD)
```

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

## v2.4 — Real-Time Monitoring & Integration (Direction E)

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

Dashboard interface and control optimization, merged from long-term planning items. **Completed.**

**Phase 1:**
- F0: Unified KPI extractor `core/kpi_extractor.py` — fixes 3 broken card metrics (OEE / %GRR / SPC violations had wrong key paths), provides variable namespace for the formula engine
- F1: Real-time refresh — signal-driven (`analysis_completed` → `_notify_dashboard`) + QTimer(5s) polling fallback + auto-refresh toggle
- F2: Custom card layout — show/hide + reorder dialog (`ui/dialogs/layout_dialog.py`), QSettings persistence

**Phase 2:**
- F3: Low-code formula editor (P2-1) — `core/kpi_formula.py` AST whitelist parser (23 attack cases rejected, length/depth guards) + `ui/dialogs/formula_dialog.py`, custom KPI cards with live evaluation
- F4: Shop floor display mode (P2-2) — full-screen dashboard `ui/dialogs/display_mode.py`, big-number KPI tiles (FONT_36B), chart carousel (QTimer 8s), ESC/arrow keys, F11 shortcut

**Status**: Direction E fully implemented — E1/E2/E3 completed (Tabs 33-34, alert system, 182 tests).

**Estimate**: 6 days total (E1 1.5 + E2 1 + E3 0.5 + E4 3) | New Tabs 33-34 | Sidebar 32→34

---

## v2.5 — Long-Term Planning (P2/P3)

| Priority | Feature | Description |
|:--:|------|------|
| P2-3 | Video Time Study | Frame-level timing · AI motion recognition (OpenCV+MediaPipe) |
| P2-4 | Batch Macro Record/Replay | Record operation sequence → save as macro → one-click replay |
| P2-5 | Custom Control Chart Templates | User save/load chart configs (JSON) |
| P3-1 | Supply Chain Quality Collaboration | P2P supplier data sharing · CPK drill-through · Part number mapping |
| P3-2 | Digital Twin Layout | Drag-and-drop workstation simulation · 2D Canvas line layout |
| P3-3 | REST API Service | FastAPI wrapping core analysis → for MES/ERP consumption |
| P3-4 | Web Frontend Migration | Gradual migration from PySide6 to FastAPI+React |
| P3-5 | Mobile App | Flutter/React Native for report viewing + alert push |

> **Note**: P2-1 (Low-code Formula Editor) and P2-2 (Shop Floor Display Mode) were moved up to v2.4 E4 (Dashboard UI & Control Enhancement).

---

## Sidebar Evolution

```
v2.0 (28)     v2.1 (28)     v2.2 (32)       v2.4 (34)
 Home (0)       Same           Same             Same
 Quality (1-6)  Same           Same             Same
 IE (7-11,21-22) Same          +SMED(29)+TPM(31)  Same
 Charts (12,18-20) Same        Same             Same
 Eng (13-17)     Same         +8D(30)+PPAP(32)   Same
 Worksheet (23-25) Same        Same             Same
 Sampling (26)   Same          Same             Same
 Report (27)     Same          Same             Same
 Data (28)       Same          Same             Same
 —               —             —                Live Monitor (33)
 —               —             —                Multi-Plant (34)
 Plugins (dynamic) Same        Same             Same
```

---

## Version History

| Date | Version | Content |
|------|---------|---------|
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
