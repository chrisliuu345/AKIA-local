# 插件数据源合同（Plugin API 2.1）

> 插件脚手架与静态兼容性检查见 [插件开发指南](plugin-development.md)。

> 适用：AKIA v4.3.0+（插件 API 2.1）。API 2.0 插件**不受影响**：同一大版本内
> 向后兼容，未声明 `data_source` 能力的插件不会被调用。
>
> 参考实现：[`tests/test_plugin_data_source.py`](../tests/test_plugin_data_source.py)
> 中的夹具插件（合成视觉测量批次 → 案例基线/复测 → 配对检验 → 关闭）。

## 1. 能力声明

插件在 `plugin.json` 中声明 `data_source` 能力，并在实现类中提供
`provide_measurements(context)`：

```json
{
  "id": "example_source",
  "name": "示例测量源",
  "version": "1.0",
  "api_version": "2.1",
  "entry": "example_source_impl:Plugin",
  "capabilities": ["data_source"]
}
```

```python
from core.measurement_event import MeasurementEvent
from core.plugin_api import IAKIAPlugin, PluginManifest


class Plugin(IAKIAPlugin):
    manifest = PluginManifest(
        id="example_source", name="示例测量源", version="1.0",
        capabilities=("data_source",))

    def is_available(self):
        return True, ""

    def provide_measurements(self, context=None):
        # 返回 MeasurementEvent 列表（也接受其 to_dict() 结果）
        return [MeasurementEvent.from_manual(
            32.4, characteristic_id="cycle", method="manual-entry")]
```

## 2. 调用与隔离规则

| 规则 | 行为 |
|------|------|
| 信任门 | 仅**已信任且可用**的插件会被调用；未信任插件只登记 manifest，不导入代码 |
| 超时 | 单插件单次调用默认 5s；超时记录 `record.error=...超时` 并跳过，不阻塞其他插件 |
| 返回类型 | 必须为 `list`/`tuple`；其它类型记错误并跳过该插件本轮数据 |
| 坏事件 | 逐条校验：无效事件被跳过并写 `record.error`，同批有效事件仍会采集 |
| 空批次 | `[]` 合法（表示本轮无数据），不算错误 |
| 异常 | 插件异常被隔离，不影响主程序与其他数据源 |
| 来源强制 | 主程序强制 `source_kind="plugin"`、`source_id=<插件 id>`、`source_name=<插件名>`，插件不能伪装成连接器/手工数据 |

采集入口：案例工作台「导入插件测量」，或代码调用
`PluginManager().collect_measurements(context=...)`；返回
`list[MeasurementEvent]`。

## 3. MeasurementEvent 返回契约

一条事件表示**一批测量事实**（一次采集窗口 / 一段视频的全部周期），不是单点：

| 字段 | 说明 |
|------|------|
| `ts_start` / `ts_end` | 测量发生时间，ISO-8601 **带时区偏移** |
| `recorded_at` | 入库时间，带时区；早于 `ts_end` 超过 300s 会被拒绝（标记时钟偏差） |
| `device` / `channel` / `characteristic_id` | 设备 / 通道 / 质量特性引用（至少提供一个语义标识） |
| `method` | 测量方法（如 `vision-cycle` / `gage-serial`） |
| `confidence` | `high` / `medium` / `low` |
| `validity` | `valid` / `suspect` / `invalid`；后两者必须给 `validity_reason` |
| `summary` | `n` / `mean` / `std` / `min` / `max`（大批量只存摘要） |
| `values` | 内联原始值，可选；默认上限 1000 个，超过请留空 |
| `raw_ref` | 原始数据引用（如 `video://line1/2026-10-04.mp4#t=12.4-93.2`） |
| `fingerprint` | 可选，物化数据与 `core.evidence.pd-hash-v1` 同源 |
| `parent_event_ids` | 可选，合并/派生事件的父事件 |

构造推荐用 `MeasurementEvent.from_samples` / `from_dataframe` / `from_manual`，
避免手写字段漏掉校验。

## 4. 异步推送（视觉/在线流）

持续采集的插件不必等待被轮询，可通过宿主门面受控注入：

```python
def on_cycle_detected(host, event):
    host.submit_measurements([event], plugin_id="example_source")
```

- `host.submit_measurements(events, plugin_id)`：先整体校验再写入，返回事件 ID；
  任一条无效则整批拒绝（不会半写）。
- `host.measurement_events()`：当前项目测量事件只读快照。
- `host.connector_topics()` / `host.recent_measurements(topic)`：读取连接器最近窗口。

事件进入项目 `MeasurementStore`（默认最多 2000 条，FIFO 截断），随 `.qap`
写入 `measurements.jsonl`；案例步骤通过 `measurement_refs` 引用事件 ID。

## 5. 视觉插件（AKIA-Vision-expansion）适配建议

1. **批量粒度**：一个工位/一段视频的周期时间集合 = 一条事件，避免逐帧事件；
2. `method="vision-cycle"`，`channel` 用工位号，`characteristic_id` 关联质量特性；
3. `ts_start/ts_end` 取视频实际时间范围，`recorded_at` 取分析完成时间；
4. `confidence` 由检测置信度映射（如 ≥0.9→high，0.7~0.9→medium，<0.7→low）；
5. 遮挡/丢失跟踪的周期标记 `validity="suspect"` 并写原因，不要静默剔除；
6. `raw_ref` 指向视频文件 + 时间范围或标注文件，**不要把视频/原始帧写入事件**；
7. 现场隐私：默认只回传周期时间与统计摘要，视频留在本机；分享/导出走脱敏包（v4.3.0 B4）。

## 6. 兼容性与版本

- 插件 API 版本在 `plugin.json` 的 `api_version` 声明；主程序 `2.1` 兼容所有 `2.x`；
- `2.0` 插件不声明 `data_source` 即可完全不受影响；
- `requirements`（`requires.akia`）继续按主程序版本门槛校验；
- 数据源接口的破坏性变更只会发生在下一个 API 大版本。
