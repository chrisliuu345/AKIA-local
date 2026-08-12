# QA-Tool Roadmap

> Current: v2.3 | Tests: 87/87 | 32 Tabs + Plugins | Updated: 2026-08-12

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

### E1. File Watcher Real-Time SPC (1.5 days)
- QFileSystemWatcher monitoring folder
- New file / change → auto import → update control chart → out-of-spec alert
- New: `core/file_watcher.py`, `ui/tabs/monitor_tab.py` (index 33)

### E2. Multi-Plant / Multi-Line Comparison (1 day)
- Same metric multi-line side-by-side · Cp/Cpk radar chart · OEE multi-bar · Defect rate overlay trend
- New: `ui/tabs/multi_plant_tab.py` (index 34)

### E3. Alert Notification System (0.5 days)
- Multi-channel alerts (popup / sound / log) · Configurable rules · Alert aggregation / dedup

### E4. Dashboard Enhancement (0.5 days)
- Real-time refresh Dashboard (tab 27, QTimer polling)
- Custom KPI card layout

**Estimate**: 3 days | New Tabs 33-34 | Sidebar 32→34

---

## v2.5 — Long-Term Planning (P2/P3)

| Priority | Feature | Description |
|:--:|------|------|
| P2-1 | Low-code Formula Editor | User-defined KPI formulas (similar to JMP Formula Editor) |
| P2-2 | Shop Floor Display Mode | Full-screen dashboard · Auto-rotate · 1920×1080 optimized |
| P2-3 | Video Time Study | Frame-level timing · AI motion recognition (OpenCV+MediaPipe) |
| P2-4 | Batch Macro Record/Replay | Record operation sequence → save as macro → one-click replay |
| P2-5 | Custom Control Chart Templates | User save/load chart configs (JSON) |
| P3-1 | Supply Chain Quality Collaboration | P2P supplier data sharing · CPK drill-through · Part number mapping |
| P3-2 | Digital Twin Layout | Drag-and-drop workstation simulation · 2D Canvas line layout |
| P3-3 | REST API Service | FastAPI wrapping core analysis → for MES/ERP consumption |
| P3-4 | Web Frontend Migration | Gradual migration from PySide6 to FastAPI+React |
| P3-5 | Mobile App | Flutter/React Native for report viewing + alert push |

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
| 08-12 | v2.3 | Released: Report template engine + dialog + HTML export + menu restructure |
| 08-10 | v2.3-dev | Phase B: Report template engine + dialog + HTML self-contained export |
| 08-10 | v2.3-dev | Phase A: 8D fishbone embed + PPAP real-time refresh + engine package exports |
| 08-10 | v2.2 | Released: 32 tabs · SMED/8D/TPM/PPAP · 87 tests · lint-clean |
| 08-10 | v2.2-dev | Review fixes: 3 Critical + 7 Warning (TPM property / animation / chart tab) |
| 08-10 | v2.1 | Released: 87 tests · AI enhanced · Lazy loading · One-click analysis · Column selector fix |
| 08-10 | v2.1-dev | Code audit: 5 bugs · 200+ imports · 60+ dead code · 15 duplicate groups |
| 08-04 | v2.0 | Initial release: 28 tabs · 65 tests · AI assistant · Plugin system |
