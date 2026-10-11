"""证据账本性能预算测试（v4.3.0 B5-2）。"""

import time

from core.evidence_ledger import EvidenceLedger


def _ledger(count: int = 1000) -> EvidenceLedger:
    ledger = EvidenceLedger()
    for index in range(count):
        ledger.append("case_step", actor="perf",
                      object_refs=[f"case:C{index % 10}"],
                      payload={"index": index})
    return ledger


class TestLedgerPerformance:
    def test_append_1k_under_budget(self):
        ledger = EvidenceLedger()
        start = time.perf_counter()
        for index in range(1000):
            ledger.append("case_step", actor="perf",
                          object_refs=[f"case:C{index % 10}"],
                          payload={"index": index})
        elapsed = time.perf_counter() - start
        assert len(ledger) == 1000
        assert ledger.verify()["ok"] is True
        assert elapsed < 2.0, f"1000 条事件追加 {elapsed:.3f}s 超出预算"
        assert elapsed / 1000 < 0.002, "单事件平均耗时超出 2ms"

    def test_open_and_verify_1k_under_budget(self):
        payload = _ledger().to_jsonl()
        start = time.perf_counter()
        loaded = EvidenceLedger.from_jsonl(payload)
        result = loaded.verify()
        loaded.events_for("case:C1")
        elapsed = time.perf_counter() - start
        assert result["ok"] is True
        assert elapsed < 0.5, f"加载校验 1000 条事件 {elapsed:.3f}s 超出预算"

    def test_jsonl_size_extrapolation(self):
        size = len(_ledger().to_bytes())
        # 1 万事件文件预算 < 5MB（按 1000 条实测线性外推）
        assert size * 10 < 5 * 1024 * 1024

    def test_single_import_event_overhead(self):
        """导入路径每个文件只记 1 条事件，单次开销应为毫秒级。"""
        ledger = EvidenceLedger()
        start = time.perf_counter()
        ledger.append("data_imported", object_refs=["/tmp/a.xlsx"],
                      payload={"sheets": 3, "rows": 1_000_000})
        elapsed = time.perf_counter() - start
        assert elapsed < 0.005, f"单条导入事件 {elapsed * 1000:.2f}ms 超出预算"

    def test_share_pack_scan_bounded_for_large_table(self, tmp_path):
        """泄漏扫描对 2 万行唯一值表必须有界（v4.3.0 逐候选项实现为分钟级）。"""
        import numpy as np
        import pandas as pd

        from core.share_pack import build_share_pack

        count = 20000
        rng = np.random.default_rng(0)
        raw = {"S": pd.DataFrame({
            "serial": [f"SN-{index:08d}-{int(extra)}"
                       for index, extra in enumerate(rng.integers(1000, 9999, count))],
        })}
        start = time.perf_counter()
        result = build_share_pack(str(tmp_path / "big-share"), raw_data=raw)
        elapsed = time.perf_counter() - start
        assert result["scan"]["ok"] is True
        assert elapsed < 30.0, f"2 万行分享包导出 {elapsed:.1f}s 超出预算"
