# 智能辅助与模型调用审计

## 中文

v4.6.0 的在线评分与异常辅助默认关闭，在「设置 → QAM Harness → 智能辅助」中显式启用。先在任一分析 Tab 完成统计计算，再到 QAM Harness 点击「在线评分」或「异常辅助」。模型只能生成顾问建议，不会改写统计数值、判定凭证或放行结论，结果必须人工确认。

云端模型仍受云调用总开关和隐私确认约束；远程 Ollama 也按实际 endpoint 执行同一隐私门。拒绝云调用时不会伪造离线评分。无可用模型时，已有分析结果保持不变。

「调用审计」展示本地运行记录，可导出 JSON。记录包含用户问题、统计输入、供应商、模型、协议、脱敏 endpoint、提示词 SHA256 与长度、工具调用、回答、状态和耗时。API Key 不写入审计，完整提示词不落盘。审计默认启用，可在设置中关闭；文件最多保留 500 条，位于平台用户数据目录的 `model_calls.jsonl`。

## English

Online scoring and anomaly assistance are disabled by default. Enable them under Settings → QAM Harness → Intelligent Assistance, run a statistical analysis, then use Online Scoring or Anomaly Assistance in QAM Harness. Model output is advisory only: it never rewrites statistical values, conclusion credentials, or release decisions, and human confirmation is required.

Cloud models remain subject to the cloud switch and privacy consent. Remote Ollama endpoints follow the same endpoint-based gate. A denied cloud call never fabricates an offline score, and unavailable models leave existing analyses unchanged.

Call Audit displays and exports local run records containing the question, statistical input, provider, model, protocol, sanitized endpoint, prompt SHA256 and length, tool calls, response, status, and duration. API keys and full prompts are not persisted. Auditing is enabled by default and can be disabled; at most 500 records are retained in `model_calls.jsonl` under the platform user-data directory.
