"""test_generate_cp_rows.py — FMEA → CP 行生成测试"""

import pytest
from core.fmea_engine import FMEAItem, FMEAEngine
from config.settings import RPN_HIGH, RPN_CRITICAL


def _make_item(**kwargs):
    """创建 FMEAItem 并自动计算 RPN"""
    defaults = {
        "function": "车削", "failure_mode": "尺寸超差",
        "effect": "装配不良", "severity": 7,
        "cause": "刀具磨损", "occurrence": 5,
        "control": "首件检验", "detection": 4,
    }
    defaults.update(kwargs)
    item = FMEAItem(**defaults)
    item.calc_rpn()
    return item


class TestGenerateCpRows:
    """FMEA → CP 行生成测试"""

    def test_empty_items(self):
        rows = FMEAEngine.generate_cp_rows([])
        assert rows == []

    def test_low_risk_filtered(self):
        """低风险项 (RPN < 100) 应被过滤"""
        item = _make_item(severity=3, occurrence=3, detection=3)  # RPN=27
        rows = FMEAEngine.generate_cp_rows([item])
        assert rows == []

    def test_high_risk_included(self):
        """高风险项 (RPN >= 100) 应被包含"""
        item = _make_item(severity=10, occurrence=10, detection=1)  # RPN=100
        rows = FMEAEngine.generate_cp_rows([item])
        assert len(rows) == 1

    def test_custom_threshold(self):
        """自定义阈值"""
        item = _make_item(severity=5, occurrence=5, detection=4)  # RPN=100
        rows = FMEAEngine.generate_cp_rows([item], rpn_threshold=50)
        assert len(rows) == 1

    def test_cp_row_structure(self):
        """CP 行应包含 9 列"""
        item = _make_item(severity=10, occurrence=10, detection=1)
        rows = FMEAEngine.generate_cp_rows([item])
        assert len(rows) == 1
        assert len(rows[0]) == 9  # CP_HEADERS 有 9 列

    def test_cp_row_content(self):
        """CP 行内容映射正确"""
        item = _make_item(
            function="钻孔", failure_mode="孔径偏大",
            cause="钻头磨损", control="SPC监控", severity=8,
            occurrence=6, detection=3,  # RPN=144
        )
        rows = FMEAEngine.generate_cp_rows([item])
        row = rows[0]
        assert row[1] == "钻孔"  # 工序名称
        assert "孔径偏大" in row[2]  # 特性
        assert "钻头磨损" in row[2]  # 特性包含原因

    def test_severity_frequency_mapping(self):
        """严重度决定抽样频率"""
        # 严重度 >= 8 → 每件
        item_high = _make_item(severity=9, occurrence=12, detection=1)  # RPN=108
        rows = FMEAEngine.generate_cp_rows([item_high])
        assert rows[0][6] == "每件"  # frequency

        # 严重度 5-7 → 每小时
        item_med = _make_item(severity=6, occurrence=10, detection=2)  # RPN=120
        rows = FMEAEngine.generate_cp_rows([item_med])
        assert rows[0][6] == "每小时"

        # 严重度 < 5 → 每批
        item_low = _make_item(severity=4, occurrence=10, detection=3)  # RPN=120
        rows = FMEAEngine.generate_cp_rows([item_low])
        assert rows[0][6] == "每批"

    def test_reaction_plan_critical(self):
        """RPN >= 200 → 停线反应"""
        item = _make_item(severity=10, occurrence=10, detection=2)  # RPN=200
        rows = FMEAEngine.generate_cp_rows([item])
        assert "停线" in rows[0][8]

    def test_reaction_plan_high(self):
        """RPN 100-199 → 隔离反应"""
        item = _make_item(severity=10, occurrence=10, detection=1)  # RPN=100
        rows = FMEAEngine.generate_cp_rows([item])
        assert "隔离" in rows[0][8]

    def test_multiple_items(self):
        """多个高风险项生成多行"""
        items = [
            _make_item(severity=10, occurrence=10, detection=1),  # RPN=100
            _make_item(severity=9, occurrence=9, detection=2),    # RPN=162
            _make_item(severity=3, occurrence=3, detection=3),    # RPN=27 (filtered)
        ]
        rows = FMEAEngine.generate_cp_rows(items)
        assert len(rows) == 2

    def test_op_numbering(self):
        """工序编号自增"""
        items = [
            _make_item(severity=10, occurrence=10, detection=1),
            _make_item(severity=9, occurrence=9, detection=2),
        ]
        rows = FMEAEngine.generate_cp_rows(items)
        assert rows[0][0] == "OP10"
        assert rows[1][0] == "OP20"

    def test_control_method_with_recommended_action(self):
        """有推荐措施时，控制方法包含推荐"""
        item = _make_item(
            severity=10, occurrence=10, detection=1,
            recommended_action="增加抽检频次",
        )
        rows = FMEAEngine.generate_cp_rows([item])
        assert "增加抽检频次" in rows[0][7]
