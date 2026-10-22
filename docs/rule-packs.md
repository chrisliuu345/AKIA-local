# AKIA Rule Packs

Rule packs are portable JSON files for sharing sampling configuration, judgement thresholds, and quality checks. They contain declarative data only; AKIA never evaluates embedded code or arbitrary expressions.

## 中文

### 格式

```json
{
  "schema_version": "1.0",
  "id": "example.quality",
  "name": "Example Quality Rule Pack",
  "version": "1.0.0",
  "description": "Portable rules",
  "metadata": {"owner": "quality-team"},
  "rules": [
    {
      "id": "judgement.cpk",
      "category": "judgement",
      "type": "threshold",
      "name": "Process capability target",
      "metric": "cpk",
      "operator": ">=",
      "value": 1.33,
      "severity": "error",
      "message": "Cpk is below the target"
    }
  ]
}
```

规则类别：

- `sampling`：抽样配置，例如 AQL、检验水平、放宽开关。
- `judgement`：过程能力、假设检验、MSA 等判定阈值。
- `quality`：FMEA、告警、质量门禁等检查。

规则类型：

| 类型 | 用途 | 字段 |
|------|------|------|
| `threshold` | 数值阈值 | `metric`、`operator`、`value` |
| `categorical` | 字符串/布尔分类判定 | `metric`、`operator`、`value` |
| `configuration` | 供对应工作流读取的配置 | `settings` |

阈值运算符：`>`、`>=`、`<`、`<=`、`==`、`!=`、`between`。
分类运算符：`==`、`!=`、`in`、`not_in`。
严重度：`error`、`warning`、`info`。

### 使用

```bash
python -m akia_sdk rules-validate \
  --pack config/rule-packs/example-quality.json --pretty

python -m akia_sdk rules-evaluate \
  --pack config/rule-packs/example-quality.json \
  --metrics '{"cpk":1.41,"grr_pct":7.2}' \
  --pretty
```

Python：

```python
from akia_sdk import RulePack

pack = RulePack.load("config/rule-packs/example-quality.json")
result = pack.evaluate({"cpk": 1.41, "grr_pct": 7.2})
assert result["ok"]
print(result["fingerprint"])
```

评估结果会记录 `pack_id`、`pack_version`、内容指纹、通过/失败/警告/跳过数量。未提供的指标会标记为 `skipped` 并列入 `missing_metrics`，不会伪造通过结论。规则包指纹为 `rulepack-hash-v1`，对规则内容、顺序和元数据敏感。

### 安全边界

- 只接受结构化 JSON，不执行公式、脚本或插件代码。
- 最大文件 1 MB；未知字段、未知类别、未知运算符和重复规则 ID 均拒绝。
- 规则包只描述判定依据，不替代证据账本、统计判定或人工确认。

## English

Rule packs are portable JSON files for sampling configuration, judgement thresholds, and quality checks. The schema is version `1.0`; rules are either `threshold`, `categorical`, or `configuration`. All unknown fields, operators, categories, duplicate rule ids, and oversized files are rejected.

Validate with `python -m akia_sdk rules-validate --pack <file>`, and evaluate with `python -m akia_sdk rules-evaluate --pack <file> --metrics '<json>'`. Python callers can use `RulePack.load()` and `RulePack.evaluate()`.

Evaluation records the pack id, version, `rulepack-hash-v1` fingerprint, pass/fail/warning/skipped counts, and missing metric names. Missing metrics are reported as skipped rather than treated as passes. Rule packs are declarative data and never execute embedded code; they do not replace evidence ledgers, statistical judgement, or human confirmation.
