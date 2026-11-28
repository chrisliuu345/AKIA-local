# AKIA Roadmap

[中文](ROADMAP.md) | [English](ROADMAP.en.md) | [Project Home](README.en.md) | [Releases](https://github.com/chrisliuu345/AKIA-local/releases)

**Status**: Current version is v4.7.0, credible industrial-engineering methods. The v4.6.x security and correctness maintenance is done.
**Last updated**: 2026-11-28

## Direction

AKIA is an open-source desktop application for personal industrial engineering and quality analysis. The project focuses on an offline-capable analysis workspace with reproducible results and user-controlled data, while interoperating with other tools through standard formats, interfaces, and plugins.

## Design Principles

1. **Correctness first**: statistical methods are continuously checked against known values, standards, and boundary conditions.
2. **Local first**: core analysis does not require an account or cloud service, and data is stored on the user's device by default.
3. **Reproducible results**: parameters, data versions, sampling decisions, and judgement evidence should be traceable.
4. **Open interoperability**: prefer common file formats and public interfaces over vendor lock-in.
5. **Incremental delivery**: each release focuses on a small set of verifiable improvements while preserving existing workflows.
6. **Contributor friendly**: documentation, tests, and code structure should be approachable and maintainable.

## Current Capabilities

- Statistics: SPC, process capability, MSA, hypothesis testing, DOE, reliability, and time series.
- IE methods: time study, OEE, SMED, TPM, line balancing, value-stream mapping, and skill-constrained scheduling.
- Quality workflow: FMEA, control plans, PPAP, 8D, and improvement cases.
- Traceability: standard versioning, evidence ledgers, conclusion credentials, and evidence-pack verification.
- Data access: file import, SQL sources, industrial connectors, and live dashboards.
- Extensibility: plugin API, optional AI assistant, and multiple report formats.
- Open interfaces: headless CLI/SDK, a local MCP service, versioned rule packs, a plugin scaffold, and static contract checks.
- Release security: archive resource limits, hashed dependency locks, third-party license notices, vulnerability auditing, and provenance.

## Release Sequence

The following releases are ordered by dependency. Each minor release focuses on one primary theme and must meet its completion criteria before the next phase begins. v4.6.4 closes the v4.6.0 bar for human confirmation, path boundaries, and model HMAC, together with the connector and dashboard fixes in that maintenance release. The current version is v4.7.0. Unreleased themes still follow the dependency of shop-floor judgement: make existing IE methods and quality characteristics reviewable first, then bring video cycles and live measurements into that same evidence chain, and finish full localisation last so the interface is not translated twice while it is still moving. From v4.7.0, new and touched interface strings go through `i18n.tr`, and the main window is split, so v4.11.0 does not rewrite the v4.7.0–v4.10.0 text. Releases after v4.11.0 follow the same dependency order: method depth and current standards first, then the data table and interaction, then more IE methods, and finally reproducible validation and release services. Interface strings added in these releases ship with Chinese and English resources from the start.

| Version | Theme | Primary goals |
|---------|-------|---------------|
| v4.5.0 | Open interfaces and release hardening | CLI, SDK, MCP, plugin and rule-pack interfaces; external-input safeguards and release provenance |
| v4.6.0 | Optional intelligent assistance and local data assets | Model-call auditing, user-enabled assistance, and an extensible local data-asset format |
| v4.6.x | Maintenance patch (not a new theme) | Confirmation, path boundaries, and model-file HMAC for assistance; a real OPC UA connection; dashboard origin, token, and escaping; secrets and atomic writes; MQTT, history order, and live-SPC resubscribe that the lot view depends on |
| v4.7.0 | Credible industrial-engineering methods | Known values for time study, line balance, OEE, and work sampling; an evidence chain from standard time through line balance to improvement cases; UI-thread work, read performance, the main-window split, and `i18n.tr` groundwork |
| v4.8.0 | Characteristic and lot judgement loop | Bind specifications, control limits, and GR&R to a characteristic; gauge gating; a lot or shift view; a full sampling-standard review |
| v4.9.0 | Video time-study research and deepening | Industry capability research, a visual-cycle event contract, review, and traceable time-study workflows |
| v4.10.0 | Real-time acquisition and embedded interfaces | A unified acquisition-adapter contract, more industrial/embedded protocols, health diagnostics, and conformance tests; an origin, authentication, and injection review before more protocols |
| v4.11.0 | Bilingual interface and report localisation | Runtime language switching, complete Chinese/English resources, and localised reports and charts |
| v4.12.0 | Statistical method depth | Regression family and diagnostics, post-hoc comparisons, general linear models, multivariate analysis, DOE response optimisation, short-run and attribute capability |
| v4.13.0 | Current manufacturing standards and measurement-data exchange | AIAG-VDA action priority, VDA 5 / ISO 22514-7, AQDEF exchange, variables sampling |
| v4.14.0 | Data table and interaction | Editable large data table, undo/redo, linked charts, guided analysis, light and high-contrast themes |
| v4.15.0 | IE method expansion | Predetermined motion times, ergonomic assessment, mixed-model line balancing, kanban sizing, light simulation, work instructions |
| v4.16.0 | Reproducibility and validation | Operation recording to scripts, replayable analysis flows, generated software validation report |
| v4.17.0 | Release, documentation, and community services | macOS build, code signing, optional update check, bilingual documentation site and examples, community files, diagnostics bundle, SBOM |

## Near-Term Milestones

### v4.5.0 — Open Interfaces and Release Hardening

- Provide a headless CLI and SDK so core analysis can be used from scripts and automated workflows.
- Provide an MCP service for controlled access to local analysis capabilities by external AI tools.
- Improve the plugin scaffold, capability declarations, and compatibility test tools.
- Add a versioned rule-pack interface for sharing sampling, judgement, and quality rules.
- Add entry-count, uncompressed-size, and path-safety limits to project, evidence-pack, and share-pack readers.
- Consolidate a reproducible dependency lockfile, separate core and optional connector dependencies, and record dependency sources and hashes.
- Include third-party license texts and attribution with distributions, define the supported Python version matrix, and add dependency-vulnerability and supply-chain scans to CI.
- Establish release provenance across the version, tag, commit, build artifact, and hash; complete an independent verification record for sampling-standard data.
- Complete interface documentation, examples, and automated tests.

Completion criteria: the CLI/SDK runs without a GUI; external inputs have resource and path boundaries; examples and API documentation are reproducible; existing plugins and project files remain compatible; distributions include license and third-party attribution information; every release artifact traces to one commit through its tag and hash.

### v4.6.0 — Optional Intelligent Assistance and Local Data Assets

- Add model configuration, run records, and an explainable call audit. Audit records stay on the machine.
- Support explicitly user-enabled online scoring and anomaly assistance without changing default offline behaviour.
- Provide an exportable, portable local data-asset format. The format is versioned and can later absorb characteristic, lot, and standard-time records without introducing a second file type.

Completion criteria: all intelligent features can be disabled; core offline analysis has no external-model dependency; intelligent assistance cannot bypass statistical decisions or human confirmation; results retain traceable inputs, models, configuration, and audit records; existing projects remain readable.

The requirement that intelligent assistance cannot bypass statistical decisions or human confirmation is closed in v4.6.4.

### v4.6.x — Security and Correctness Maintenance

This is not a new minor theme. The in-app assistant runs tool calls with no confirmation and can reach pickle through `joblib.load`, so the v4.6.0 completion bar is still open. This patch only covers security and correctness, and it includes the connector defects the v4.8.0 lot view depends on, rather than leaving them until v4.10.0.

- Reject path parameters supplied by the model, and verify a model file's HMAC before `joblib.load`. The model cannot choose a path; a person selects the file in the interface.
- Do not run a model-initiated tool call until a person confirms it.
- Make OPC UA actually connect, and surface connection and read errors.
- Check Origin on the live dashboard, issue a random token by default, escape untrusted fields, and do not leave the access token in the URL.
- Do not fall back to a plaintext secret when encryption fails; write config and project files atomically.
- Lock MQTT subscription state and use the paho v2 API; return the newest history rows when no start time is given; resubscribe live SPC when the device changes.

Completion criteria: regression shows that a model-supplied path is rejected, a person-selected model file still loads, and a failed HMAC check never calls `joblib.load`; a model-initiated tool call does not run without human confirmation; OPC UA reports an error for an unreachable endpoint, and a loopback test reads a node value; the dashboard rejects a non-local Origin, uses a random token even on loopback only, renders untrusted fields as text, and does not keep the token in the address; failed encryption does not write a plaintext secret, and config and project writes replace the file atomically; MQTT updates its latest values under a lock and uses the paho v2 callback API; a history query without `since` returns the newest rows; live SPC resubscribes after a device change and keeps plotting points; no new analysis methods or protocols are added, and existing projects remain readable.

### v4.7.0 — Credible Industrial-Engineering Methods

- Add known-value cases, with sources and tolerances, for standard time (observed time, rating factor, and allowance), line-balance rate, OEE weighted availability, performance, and quality, and work-sampling sample size. Prefer textbooks, standards, or publicly reviewable worked examples.
- When an implementation disagrees with a known value, correct that engine and state the effect on existing project results in the release notes.
- Provide one reproducible path: a confirmed standard time feeds line balancing, the balance result can be the baseline and remeasure of an improvement case, and the evidence ledger records the step.
- Do not add new IE method families in this release. Change SMED, value-stream mapping, and TPM only when a known value or this path exposes a defect.
- Move import, export, project I/O, and tab analysis off the GUI thread through one `run_in_worker`.
- Extract the repeated `run_and_display` template and split `ui/main_window.py`.
- Prefer calamine for xlsx, and cache numeric columns after one conversion.
- Make benefit-ledger lookup O(1) and tighten that benchmark.
- Move the LLM availability probe off the UI thread, set a database connect timeout, and cap rows on SQL loads.
- Pass only new and touched interface strings through `i18n.tr`. Full translation stays in v4.11.0. The main-window split lands in this release so v4.11.0 does not rewrite v4.7.0–v4.10.0 strings.

Completion criteria: each of the four calculations has at least one known-value case in the per-file regression; the path from time study through line balance to case remeasure runs without a model or a network; the evidence record can restore the input parameters and the standard version used; import, export, project I/O, and tab analysis do not run on the UI thread; benefit-ledger lookup is O(1) and its benchmark stays within the ×1.5 tolerance; new and touched interface strings go through `i18n.tr`, and full translation remains in v4.11.0.

### v4.8.0 — Characteristic and Lot Judgement Loop

- Treat the quality characteristic as the unit of work, and bind each control-plan row to its specification limits, control limits, and latest MSA/GR&R conclusion.
- Show gauge status on SPC and process capability for that characteristic. When the gauge conclusion misses the agreed threshold, the capability figure remains computable and reviewable, but it must not be used as a release basis; the evidence record states why it was downgraded. The threshold is configurable and does not rewrite existing offline results by default.
- Provide a lot or shift view that brings together the sampling decision, measurement events, control-chart points, and open improvement cases in that scope.
- In an environment that holds a licensed copy of ISO 2859-1 / GB/T 2828.1, review the full AQL columns, special inspection levels, and switching rules, and record the reviewer, standard revision, and date. The independent cross-check completed in v4.5.0 remains in place.

Completion criteria: a characteristic shows its specification, control limits, and gauge conclusion from the control plan; a failed gauge cannot be treated as a release basis for capability; one lot or shift view shows the sampling decision, measurements, and open cases together; the sampling review record is in the repository and the automated gate still passes; older `.qap` files remain readable.

### v4.9.0 — Video Time-Study Research and Deepening

- Start with public-source and representative-scenario research covering cycle segmentation, multiple operators and stations, occlusion handling, exception review, offline privacy, file interoperability, licensing, and deployment cost.
- Convert the research into an acceptance-driven feature list, then deepen the event contract between visual plugins such as `AKIA-Vision-expansion` and the main application.
- Carry video sessions, cycle boundaries, confidence, manual corrections, and review records through a traceable workflow. Confirmed cycles enter the v4.7.0 time-study and evidence path, rather than a second time-calculation engine.
- Improve batch/multi-station analysis, exception-cycle review, task decomposition, baseline/remeasure comparison, and streaming usability for long videos.
- Keep raw video and frames local by default; exclude them from measurement events, evidence packs, and share packs, retaining only controlled references and necessary statistical summaries.

Completion criteria: research findings include explicit priorities and acceptance measures; at least one end-to-end scenario from video to cycles, time study, and evidence passes; manual corrections are traceable and parameters are reproducible; the plugin event contract has version-compatibility tests; the privacy boundary and raw-video retention policy pass a security review.

### v4.10.0 — Real-Time Acquisition and Embedded Interface Expansion

- Define a unified real-time acquisition adapter contract covering capabilities, discovery, configuration validation, timestamps/units/quality flags, reconnection, buffering and backpressure, and health diagnostics.
- On top of the existing OPC UA, Modbus TCP, MQTT, serial-gauge, and CMM DMIS support, add at least two industrial or embedded interface families prioritised through community demand.
- Provide connection profiles, secure credential storage, data-mapping templates, simulators, and conformance tools to reduce the cost of adding devices.
- Add offline buffering, out-of-order and duplicate detection, device-clock-skew warnings, and resource bounds for long-running acquisition.
- Feed measurements from new interfaces into the unified measurement event, and make them visible in the v4.8.0 characteristic and lot views.
- Keep connector dependencies optional, provide clear installation guidance when unavailable, and avoid mandatory lock-in to a single device or commercial platform.
- Before further protocols widen network exposure, the live dashboard and new connectors pass a security review of origin, authentication, and injection. OPC UA and MQTT correctness is a v4.6.x prerequisite, not new scope for this release.

Completion criteria: at least two new interface families complete end-to-end acquisition through simulators or real hardware; data enters the unified MeasurementEvent, the real-time analysis path, and the characteristic and lot views; disconnection, reconnection, ordering, and resource-bound tests pass; existing connectors and project formats remain compatible; third parties can independently implement and validate adapters from the documentation; the live dashboard and new connectors pass a security review of origin, authentication, and injection before more protocols widen network exposure; OPC UA and MQTT correctness is not new scope for this release.

### v4.11.0 — Bilingual Interface and Report Localisation

- Build a Qt-independent localisation layer with Chinese and English resource parity, missing-key fallback, and plugin text extension.
- Support runtime language switching and persist the user's choice, updating menus, tabs, dialogs, status messages, and errors without a restart.
- Apply the selected language to PDF, Word, Excel, PowerPoint, HTML reports, and charts, with consistent date, number, unit, and font-fallback rules.
- Cover interface and report text added in v4.7.0 through v4.10.0.
- From v4.7.0, new and touched interface strings already go through `i18n.tr`, and the main window is already split. This release finishes the remaining translation and does not rewrite those strings.
- Record the generation language in report metadata and evidence traces so outputs remain reproducible and reviewable across languages.
- Add regression coverage for long-text layout, shortcuts, accessible names, and Chinese/English help entry points.

Completion criteria: switching language while the application is running updates open views and all subsequent exports; Chinese and English resource keys match and no primary interface text remains untranslated; report, chart, date, and number formats follow the selected language; switching language does not change analysis results or project-file semantics; v4.7.0–v4.10.0 strings already passed through `i18n.tr` keep their keys and are not rewritten wholesale in this release.

### v4.12.0 — Statistical Method Depth

- Regression: multiple-regression diagnostics (variance inflation, residual plots, leverage and influence), stepwise and best-subset selection, binary/ordinal/nominal logistic regression, Poisson regression, and nonlinear regression.
- Analysis of variance: post-hoc multiple comparisons (Tukey, Dunnett, Games-Howell, and others), general linear models, random factors, and simple mixed models.
- Multivariate analysis: principal components, clustering, and discriminant analysis; factor analysis only if publicly reviewable known values are available.
- DOE: add a multi-response desirability optimiser on top of the existing response-surface support, and state the constraints and weights used.
- Other: short-run SPC, pre-control, binomial and Poisson attribute capability, and tolerance stack-up with Monte Carlo simulation (random seed fixed and recorded).
- All methods live under `analysis/` without a Qt dependency, and are wired into the tab registry, the CLI/SDK tool list, and report export.

Completion criteria: each method has at least one known-value case with a stated source and tolerance in the per-file regression, and `KNOWN_VALUES.md` is updated; singular design matrices, complete separation, and too-small samples return explicit errors rather than silent numbers; every new method has an entry in the interface, the CLI/SDK, and reports; new interface strings ship with Chinese and English resources.

### v4.13.0 — Current Manufacturing Standards and Measurement-Data Exchange

- Add the AIAG-VDA (2019) action-priority (AP) method to FMEA alongside RPN; existing projects keep using RPN and their results do not change.
- Add VDA 5 / ISO 22514-7 measurement-process capability next to Type 1 and GR&R, connected to the v4.8.0 gauge gate.
- Provide AQDEF (`.dfq`) import and export, with data entering the unified MeasurementEvent. The parser reuses the entry-count, size, and path limits of the archive readers and reports malformed input explicitly.
- Provide ISO 3951 / GB/T 6378 variables sampling as a rule pack, reviewed in an environment that holds a licensed copy, with the reviewer, standard revision, and date recorded. Unreviewed tables are labelled "not checked against the standard text" in the interface and the evidence record.
- Exchange samples in the repository are synthetic; no real production data.

Completion criteria: the review record of the AP table against the published standard is in the repository, and unreviewed parts are labelled in the interface; VDA 5 and variables sampling each have known-value cases; an AQDEF round trip preserves characteristics, specifications, and measured values, and malformed or oversized input is rejected; older `.qap` files remain readable and existing RPN results do not change.

### v4.14.0 — Data Table and Interaction

- An editable large data table built on a data model: column types, formula columns, stack and unstack, subsets, and recoding.
- Project-level undo/redo covering data edits and analysis parameters. Undo history is not written to `.qap` by default.
- Linked brushing between charts and the data table; points selected in one chart are highlighted in other charts and the table.
- Guided analysis: choose a method from the question, check assumptions such as sample size, normality, and stability, and explain the reading through a result card. A result card must not replace a statistical decision or human confirmation.
- Light and high-contrast themes, high-DPI support, and accessible names.
- Import open formats such as Parquet. Proprietary formats are considered only when the format is public and the license allows it.
- Depends on the v4.7.0 `run_in_worker` and the main-window split, so long operations stay off the UI thread.

Completion criteria: scrolling, sorting, and editing in the table stay within a recorded benchmark, and no performance gain is claimed without baseline evidence; undo/redo round-trips data edits and analysis parameters; linked brushing works in at least three chart types; the assumption checks of guided analysis have known-value or boundary cases; the main interface has no unreadable text in either theme; older projects remain readable.

### v4.15.0 — IE Method Expansion

- Predetermined motion times: first research the data-table licensing of systems such as MTM, MOST, and MODAPTS. Implement only what can be published lawfully, or let users import tables they hold; do not ship copyrighted time-value tables in the repository.
- Ergonomic assessment: RULA, REBA, and the NIOSH lifting equation, using published formulas with known values taken from the original literature.
- Mixed-model and U-shaped line balancing, kanban quantity calculation, and spaghetti diagrams.
- Light discrete-event simulation to check line-balance proposals; the random seed is fixed and recorded, and results go into the evidence ledger.
- Generate work instructions from standard-work combination sheets and time studies.
- All of the above enter the standard-time, line-balance, and improvement-case evidence chain from v4.7.0. Cycles confirmed in v4.9.0 can feed predetermined-motion analysis, without a second time-calculation engine.

Completion criteria: each new method has at least one known-value case with a source; the licensing conclusion for predetermined motion times is documented; mixed-model balancing and simulation scenarios run without a model or a network; the evidence record can restore the input parameters of each new result; older projects remain readable.

### v4.16.0 — Reproducibility and Validation

- Operation recording: export analysis operations performed in the interface as an SDK script that reproduces the same result from the same data and parameters, within the agreed tolerance.
- Save replayable analysis flows in a project, with a version field; report clearly when a plugin is missing or a method version has changed.
- Generate a software validation report that summarises the version, dependency locks, known-value regression results, and the evidence ledger, and states its scope. The report does not claim any compliance certification.
- Flag conclusions as stale when the input data they depend on has changed.

Completion criteria: a recorded script replays headlessly with results matching the interface; the validation report can be reproduced independently from release artifacts and its hashes match `release-manifest.json`; the stale flag does not rewrite existing conclusions; older projects remain readable and projects without flows behave unchanged.

### v4.17.0 — Release, Documentation, and Community Services

- Add a macOS (Apple silicon) package and include it in release smoke tests.
- Sign the Windows installer once a certificate is available, with the signature consistent with the release manifest.
- A user-enabled update check: off by default, requesting only GitHub Releases, uploading no data, and verifying SHA256 after download.
- A searchable Chinese/English documentation site generated from repository documents and released with each version. Each method states its principle, formula, assumptions, interpretation, and known-value source; each module has synthetic example data and a tutorial.
- Add `SECURITY.md`, `CONTRIBUTING.md`, issue templates, and a discussion forum, and set up a plugin index.
- A local diagnostics bundle (logs, environment, version) that the user inspects and attaches to an issue themselves; the application never uploads it.
- Publish a CycloneDX SBOM and add reproducible-build notes.
- If SDK/API breaking changes have accumulated by then, move to v5.0.0 in this release and list each change in the release notes.

Completion criteria: every release tag carries installers, hash files, and `release-manifest.json`; the packages for all three platforms pass smoke tests; with the update check off there are no network requests; the documentation site covers every registered tab; example data passes validation and contains no real production data.

## Later Exploration

- More report templates, statistical methods, and community-driven connectors.
- Optional local analysis such as process windows and edge anomaly detection. These capabilities must not bypass statistical decisions or human confirmation.
- Advanced video time-study model evaluation, edge-device collaboration, and large-scale line deployment.
- Tighten the performance-baseline gate (tolerance from ×3 to ×1.5).
- Consider new machine-learning model families only after v4.7.0 and v4.8.0 are accepted.

## Non-Goals

- Accounts, subscriptions, trial limits, or online activation.
- Analysis workflows that are only available through a cloud service.
- Enterprise multi-tenancy, organisational permissions, or a central management platform.
- Closed or non-portable proprietary data formats.
- Mandatory integrations with a single commercial vendor.

## Prioritisation

Priorities are, in order: data correctness and security, regression and compatibility, reproducibility, open interoperability, and user experience. Community feedback is collected through GitHub Issues. Proposals that affect the data model or public interfaces should be discussed before implementation.

## Releases and Compatibility

- Version numbers follow semantic-versioning principles; breaking interface changes are called out in release notes.
- `.qap` project files remain backward-readable, with new fields added incrementally.
- Freeze public interfaces and data contracts before implementing features in each minor release; new capabilities must provide a disable or fallback path.
- Release tags, version numbers, source commits, dependency lockfiles, installers, and hashes must form one verifiable correspondence.
- Releases pass static checks, version consistency, per-file tests, performance baselines, and packaging smoke tests.
- Performance-baseline tolerance is ×1.5. The previous ×3 tolerance let through a benefit-ledger regression of about 2.2×; that correction is in v4.7.0.
- mypy is ratcheted directory by directory, and coverage has a per-directory floor, in the same style as the ruff ratchet: each directory starts from its current level and only tightens.
- From v4.6.0 onward, a release tag also runs Windows installer smoke alongside the Linux AppImage, and checks that the program entry point, project license, and third-party notices are packaged.
- From v4.6.0 onward, the sidebar, analysis menu, and command palette use the tab registry as their only entry list. A registered page missing any of those entries is a release defect.
- Every release tag must carry installers, hash files, and `release-manifest.json`; a missing item is a release defect.
- Tags and release notes live in GitHub Releases; this roadmap keeps only current status and future plans.

## Contributing

Bug reports, use cases, design proposals, and pull requests are welcome. See the [README](README.en.md) for development and testing instructions. Report security issues through GitHub's private vulnerability reporting feature.
