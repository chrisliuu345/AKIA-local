# Standards Data Validation

## 中文

### AQL 抽样表独立核对（2026-10-19）

核对对象：

- 本项目的正常检验抽样表（16 个字码 × 6 个常用 AQL：0.65、1.0、1.5、2.5、4.0、6.5）。
- 独立参考实现：[`drmcoder/aql-sample-size`](https://github.com/drmcoder/aql-sample-size)，
  提交 `ee12b8d3a720d394a5fdb9b750047462e5200a2d`，MIT License。
- 参考数据副本与许可证：`tests/fixtures/aql_reference_mit.json`、
  `tests/fixtures/AQL_REFERENCE_LICENSE.txt`。

核对结果：

| 项目 | 结果 |
|------|------|
| 直接单元格 | 54 格，Ac/Re 与样本量全部一致 |
| 箭头单元格 | 42 格，参考实现未按 ISO 箭头迁移样本量，因此不用于精确判定 |
| 箭头单元格 Ac/Re 差异 | 6 格，项目实现按箭头指向行取样本量与 Ac/Re |
| 自动门禁 | `python tools/check_aql_reference.py` |

比对范围是两份实现共同覆盖的 96 格，不代表已获得标准全文版权或许可。项目仍建议维护者在持有
ISO 2859-1 / GB/T 2828.1 合法文本的环境中，对完整 21 列 AQL 表、特殊检验水平和转移规则执行
人工逐格复核，并将核对人、标准版本与日期记录到发布 Issue。

## English

The normal-inspection table was cross-checked for 16 code letters across six common AQL values against the independent MIT-licensed `drmcoder/aql-sample-size` implementation at commit `ee12b8d3a720d394a5fdb9b750047462e5200a2d`.

All 54 direct cells matched for Ac/Re and sample size. The reference implementation does not apply ISO arrow sample-size shifts, so 42 arrow cells are recorded separately; six of those differ in Ac/Re because AKIA resolves the arrow target row. The automated gate is `python tools/check_aql_reference.py`.

This covers the 96-cell overlap between the two implementations, not the complete standard table. Maintainers should still perform a licensed-text review of all 21 AQL columns, special inspection levels, and transfer rules, recording reviewer, standard revision, and date in the release issue.
