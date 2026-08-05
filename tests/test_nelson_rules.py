"""Nelson 判异规则 8/8 专项单元测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from analysis.spc._rules import check_all_nelson_rules


def test_rule_1_beyond_3sigma():
    """规则1: 一点超出3σ"""
    data = np.ones(20, dtype=float) * 10.0
    data[10] = 13.5  # 3.5σ away
    v = check_all_nelson_rules(data, 10.0, 1.0)
    r1 = [x for x in v if x["rule"] == 1]
    assert len(r1) == 1 and r1[0]["point"] == 11


def test_rule_1_multiple():
    """规则1: 多点超出3σ"""
    data = np.ones(50, dtype=float) * 10.0
    data[5], data[20], data[35] = 14.0, 13.2, 13.8
    v = check_all_nelson_rules(data, 10.0, 1.0)
    r1 = [x for x in v if x["rule"] == 1]
    assert len(r1) == 3


def test_rule_2_same_side_9():
    """规则2: 连续9点同侧"""
    data = np.arange(1, 30, dtype=float)
    data[10:19] = 100.0  # all above mean
    v = check_all_nelson_rules(data, 10.0, 5.0)
    r2 = [x for x in v if x["rule"] == 2]
    assert len(r2) >= 1


def test_rule_2_no_violation():
    """规则2: 不够9点无违规"""
    data = np.array([11, 9, 11, 9, 11, 9, 11, 9, 11, 9])
    v = check_all_nelson_rules(data, 10.0, 2.0)
    r2 = [x for x in v if x["rule"] == 2]
    assert len(r2) == 0


def test_rule_3_trend_6():
    """规则3: 连续6点递增"""
    data = np.arange(1, 30, dtype=float)
    data[5:11] = [1, 2, 3, 4, 5, 6]
    v = check_all_nelson_rules(data, 15.0, 3.0)
    r3 = [x for x in v if x["rule"] == 3]
    assert len(r3) == 1


def test_rule_4_alternating_14():
    """规则4: 连续14点交替上下"""
    base = np.ones(50, dtype=float) * 10.0
    for i in range(14):
        base[20 + i] = 10.0 + (1.0 if i % 2 == 0 else -1.0)
    v = check_all_nelson_rules(base, 10.0, 2.0)
    r4 = [x for x in v if x["rule"] == 4]
    assert len(r4) == 1


def test_rule_4_no_violation():
    """规则4: 不交替无违规"""
    data = np.arange(50, dtype=float) + 10.0
    v = check_all_nelson_rules(data, 35.0, 5.0)
    r4 = [x for x in v if x["rule"] == 4]
    assert len(r4) == 0


def test_rule_5_2of3_beyond_2sigma():
    """规则5: 连续3点中2点超出2σ"""
    data = np.ones(30) * 10.1
    data[10], data[12] = 13.0, 13.5  # beyond 2σ
    v = check_all_nelson_rules(data, 10.0, 1.0)
    r5 = [x for x in v if x["rule"] == 5]
    assert len(r5) == 1


def test_rule_6_4of5_beyond_1sigma():
    """规则6: 连续5点中4点超出1σ"""
    data = np.ones(30) * 10.1
    data[10:15] = [11.5, 11.3, 10.5, 11.8, 11.6]
    v = check_all_nelson_rules(data, 10.0, 1.0)
    r6 = [x for x in v if x["rule"] == 6]
    assert len(r6) == 1


def test_rule_7_15_within_1sigma():
    """规则7: 连续15点在±1σ内"""
    data = np.ones(50) * 10.0
    data[10:25] = 10.05
    v = check_all_nelson_rules(data, 10.0, 1.0)
    r7 = [x for x in v if x["rule"] == 7]
    assert len(r7) == 1


def test_rule_8_outside_1sigma():
    """规则8: 连续8点均在±1σ外"""
    data = np.ones(50) * 10.0
    data[20:28] = [12, 8, 13, 7, 11.5, 8.5, 12.3, 8.2]
    v = check_all_nelson_rules(data, 10.0, 1.0)
    r8 = [x for x in v if x["rule"] == 8]
    assert len(r8) == 1


def test_normal_data_few_violations():
    """正态数据: 违规点极少"""
    np.random.seed(42)
    data = np.random.normal(10.0, 0.5, 100)
    v = check_all_nelson_rules(data, np.mean(data), np.std(data))
    assert len(v) <= 4  # 100个正态点应≤4个违规


def test_short_data_no_crash():
    """短数据不应崩溃"""
    for n in [1, 2, 5, 10, 15]:
        data = np.random.normal(10, 1, n)
        v = check_all_nelson_rules(data, np.mean(data), np.std(data))
        assert isinstance(v, list)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
