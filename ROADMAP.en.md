# AKIA Roadmap

[中文](ROADMAP.md) | [English](ROADMAP.en.md) | [Project Home](README.en.md) | [Releases](https://github.com/chrisliuu345/AKIA-local/releases)

**Status**: v4.4.x is the current stable line, with active development continuing.
**Last updated**: 2026-10-17

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

## Near-Term Milestones

### v4.5.0 — Open Interfaces and Automation

- Provide a headless CLI and SDK so core analysis can be used from scripts and automated workflows.
- Provide an MCP service for controlled access to local analysis capabilities by external AI tools.
- Improve the plugin scaffold, capability declarations, and compatibility test tools.
- Add a versioned rule-pack interface for sharing sampling, judgement, and quality rules.
- Complete interface documentation, examples, and automated tests.

Completion criteria: the CLI/SDK runs without a GUI; examples and API documentation are reproducible; existing plugins and project files remain compatible.

### v4.6.0 — Optional Intelligent Assistance and Local Data Assets

- Add model configuration, run records, and an explainable call audit.
- Support user-enabled scoring and anomaly assistance without changing default offline behaviour.
- Explore process-window recommendations, IE evidence chains, and edge anomaly detection.
- Provide exportable and portable formats for local data assets.

Completion criteria: all intelligent features can be disabled; core offline analysis has no external-model dependency; results retain traceable inputs and configuration.

## Later Exploration

- Complete English localisation of the interface and documentation.
- Light and high-contrast themes plus accessibility improvements.
- More data connectors, report templates, and statistical methods.
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
- Releases pass static checks, version consistency, per-file tests, performance baselines, and packaging smoke tests.
- Tags and release notes live in GitHub Releases; this roadmap keeps only current status and future plans.

## Contributing

Bug reports, use cases, design proposals, and pull requests are welcome. See the [README](README.en.md) for development and testing instructions. Report security issues through GitHub's private vulnerability reporting feature.
