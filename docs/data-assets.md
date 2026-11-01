# 本地数据资产 `.qda`

## 中文

`.qda` 是 v4.6.0 引入的可移植本地数据资产容器。通过「文件 → 导出本地数据资产」保存，通过「导入本地数据资产」恢复；导入对话框也可把旧 `.qap` 项目经同一契约迁移。

格式为 ZIP，采用 `schema_version=1.0` 和固定 `kind=akia-local-data-asset`：

- `manifest.json`：版本、应用版本、工作表映射、记录计数、每个文件的 SHA256 和大小。
- `data/sheet_N.csv`：工作表；原始表名保存在 manifest，不直接进入路径。
- `context.json`、`standards.json`、`measurements.jsonl`、`sampling.json` 等现有领域段。
- `assets.json`：统一的 `characteristics`、`lots`、`standard_times` 和可扩展 `extensions` 段。
- 可选分析、图表、案例、证据、量具、收益和技能段。

读取时先执行归档路径、条目数、解压量和压缩比检查，再验证文件集合、schema 主版本及逐项哈希。损坏或被篡改的文件不会被恢复。后续特性、批次和标准工时扩展继续使用 `.qda`，不另起平行资产格式。

## English

`.qda` is the portable local data-asset container introduced in v4.6.0. Use File → Export Local Data Asset and File → Import Local Data Asset. The import dialog can also migrate an existing `.qap` project through the same contract.

The ZIP format uses `schema_version=1.0` and `kind=akia-local-data-asset`. Its manifest records the application version, worksheet mapping, counts, and every file's SHA256 and size. Worksheets use indexed filenames with original names held in the manifest. Existing context, standards, measurements, sampling, analysis, chart, case, evidence, gauge, benefit, and skill segments are preserved.

`assets.json` provides unified `characteristics`, `lots`, `standard_times`, and extensible `extensions` sections so future domain records do not require a parallel file format. Loading enforces archive resource limits, schema-major compatibility, exact file membership, and per-file hashes before restoring any data.
