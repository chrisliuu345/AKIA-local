# AKIA Roadmap

[中文](ROADMAP.md) | [English](ROADMAP.en.md) | [Project Home](README.en.md) | [Releases](https://github.com/chrisliuu345/AKIA-local/releases)

**Status**: v4.5.0 development and local quality gates are complete, pending commit and version tagging; v4.4.x is the previous stable line.
**Last updated**: 2026-10-19

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

The following releases are ordered by dependency. Each minor release focuses on one primary theme and must meet its completion criteria before the next phase begins.

| Version | Theme | Primary goals |
|---------|-------|---------------|
| v4.5.0 | Open interfaces and release hardening | CLI, SDK, MCP, plugin and rule-pack interfaces; external-input safeguards and release provenance |
| v4.6.0 | Optional intelligent assistance and local data assets | Model-call auditing, user-enabled assistance, and portable local data assets |
| v4.7.0 | Bilingual interface and report localisation | Runtime language switching, complete Chinese/English resources, and localised reports and charts |
| v4.8.0 | Video time-study research and deepening | Industry capability research, a visual-cycle event contract, review, and traceable time-study workflows |
| v4.9.0 | Real-time acquisition and embedded interfaces | A unified acquisition-adapter contract, more industrial/embedded protocols, health diagnostics, and conformance tests |

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

- Add model configuration, run records, and an explainable call audit.
- Support user-enabled scoring and anomaly assistance without changing default offline behaviour.
- Explore process-window recommendations, IE evidence chains, and edge anomaly detection.
- Provide exportable and portable formats for local data assets.

Completion criteria: all intelligent features can be disabled; core offline analysis has no external-model dependency; intelligent assistance cannot bypass statistical decisions or human confirmation; results retain traceable inputs, models, configuration, and audit records.

### v4.7.0 — Bilingual Interface and Report Localisation

- Build a Qt-independent localisation layer with Chinese and English resource parity, missing-key fallback, and plugin text extension.
- Support runtime language switching and persist the user's choice, updating menus, tabs, dialogs, status messages, and errors without a restart.
- Apply the selected language to PDF, Word, Excel, PowerPoint, HTML reports, and charts, with consistent date, number, unit, and font-fallback rules.
- Record the generation language in report metadata and evidence traces so outputs remain reproducible and reviewable across languages.
- Add regression coverage for long-text layout, shortcuts, accessible names, and Chinese/English help entry points.

Completion criteria: switching language while the application is running updates open views and all subsequent exports; Chinese and English resource keys match and no primary interface text remains untranslated; report, chart, date, and number formats follow the selected language; switching language does not change analysis results or project-file semantics.

### v4.8.0 — Video Time-Study Research and Deepening

- Start with public-source and representative-scenario research covering cycle segmentation, multiple operators and stations, occlusion handling, exception review, offline privacy, file interoperability, licensing, and deployment cost.
- Convert the research into an acceptance-driven feature list, then deepen the event contract between visual plugins such as `AKIA-Vision-expansion` and the main application.
- Carry video sessions, cycle boundaries, confidence, manual corrections, and review records through a traceable workflow into time study.
- Improve batch/multi-station analysis, exception-cycle review, task decomposition, baseline/remeasure comparison, and streaming usability for long videos.
- Keep raw video and frames local by default; exclude them from measurement events, evidence packs, and share packs, retaining only controlled references and necessary statistical summaries.

Completion criteria: research findings include explicit priorities and acceptance measures; at least one end-to-end scenario from video to cycles, time study, and evidence passes; manual corrections are traceable and parameters are reproducible; the plugin event contract has version-compatibility tests; the privacy boundary and raw-video retention policy pass a security review.

### v4.9.0 — Real-Time Acquisition and Embedded Interface Expansion

- Define a unified real-time acquisition adapter contract covering capabilities, discovery, configuration validation, timestamps/units/quality flags, reconnection, buffering and backpressure, and health diagnostics.
- On top of the existing OPC UA, Modbus TCP, MQTT, serial-gauge, and CMM DMIS support, add at least two industrial or embedded interface families prioritised through community demand.
- Provide connection profiles, secure credential storage, data-mapping templates, simulators, and conformance tools to reduce the cost of adding devices.
- Add offline buffering, out-of-order and duplicate detection, device-clock-skew warnings, and resource bounds for long-running acquisition.
- Keep connector dependencies optional, provide clear installation guidance when unavailable, and avoid mandatory lock-in to a single device or commercial platform.

Completion criteria: at least two new interface families complete end-to-end acquisition through simulators or real hardware; data enters the unified MeasurementEvent and real-time analysis paths; disconnection, reconnection, ordering, and resource-bound tests pass; existing connectors and project formats remain compatible; third parties can independently implement and validate adapters from the documentation.

## Later Exploration

- Light and high-contrast themes plus accessibility improvements.
- More report templates, statistical methods, and community-driven connectors.
- Advanced video time-study model evaluation, edge-device collaboration, and large-scale line deployment.
- Installer, update, and cross-platform compatibility improvements.
- Broader test coverage, performance baselines, and contributor documentation.

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
- Tags and release notes live in GitHub Releases; this roadmap keeps only current status and future plans.

## Contributing

Bug reports, use cases, design proposals, and pull requests are welcome. See the [README](README.en.md) for development and testing instructions. Report security issues through GitHub's private vulnerability reporting feature.
