"""SMED 甘特图标签截断辅助函数单元测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.tabs.smed_tab import truncate_label


class TestTruncateLabel:
    def test_short_name_unchanged(self):
        assert truncate_label("拆装工装") == "拆装工装"
        assert truncate_label("12345678") == "12345678"  # 恰好 8 字

    def test_long_name_truncated(self):
        assert truncate_label("123456789") == "1234567…"
        assert truncate_label("拆装外部工装并定位") == "拆装外部工装并…"

    def test_custom_max_len(self):
        assert truncate_label("abcdef", max_len=4) == "abc…"
        assert truncate_label("abc", max_len=4) == "abc"

    def test_empty(self):
        assert truncate_label("") == ""
