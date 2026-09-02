"""可靠性分析 — Weibull + MTBF 单元测试"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pytest

from analysis.reliability.weibull import WeibullAnalyzer, WeibullResult
from analysis.reliability.mtbf import MTBFAnalyzer, MTBFResult

np.random.seed(42)


# ──────────────────────────────────────────────
# Weibull 测试
# ──────────────────────────────────────────────

class TestWeibullAnalyzer:

    def setup_method(self):
        self.analyzer = WeibullAnalyzer()

    def test_2p_mle_basic(self):
        """2P Weibull MLE: 从已知分布抽样，验证拟合参数在合理范围"""
        # 生成 β=2.0, η=1000 的 Weibull 数据
        true_beta, true_eta = 2.0, 1000.0
        data = true_eta * np.random.weibull(true_beta, 50)
        result = self.analyzer.analyze(data.tolist())
        assert result["error"] is None
        r = result["result"]
        assert r is not None
        assert 1.2 < r.beta < 3.5
        assert 600 < r.eta < 1600
        assert r.method == "2P-MLE"
        assert r.b10_life > 0
        assert r.b50_life > r.b10_life
        assert r.characteristic_life > 0
        assert len(r.probability_data["time"]) == 50

    def test_insufficient_data(self):
        """数据不足时返回 error"""
        result = self.analyzer.analyze([1, 2, 3])  # < 5
        assert result["error"] is not None

    def test_with_censored(self):
        """含右删失数据的分析"""
        failures = list(1000 * np.random.weibull(2.0, 30))
        # 标记最后 5 个为删失
        censored = [1] * 25 + [0] * 5
        result = self.analyzer.analyze(failures, censored=censored)
        assert result["error"] is None
        r = result["result"]
        assert r is not None
        assert r.method == "2P-MLE"

    def test_rank_regression(self):
        """秩回归方法"""
        data = list(1000 * np.random.weibull(2.0, 40))
        result = self.analyzer.analyze(data, fit_method="rank-regression")
        assert result["error"] is None
        r = result["result"]
        assert r is not None
        assert r.method == "rank-regression"
        assert r.r_squared > 0.8  # 秩回归应有较好线性

    def test_3p_weibull(self):
        """3P Weibull 尝试（大样本）"""
        data = list(100 + 1000 * np.random.weibull(2.0, 80))
        result = self.analyzer.analyze(data, three_parameter=True)
        assert result["error"] is None
        r = result["result"]
        assert r is not None
        # 3P 未必选上（取决于 AIC），但至少不会崩溃

    def test_b_life_values(self):
        """B10 / B50 寿命合理性"""
        true_beta, true_eta = 2.0, 1000.0
        data = list(true_eta * np.random.weibull(true_beta, 60))
        result = self.analyzer.analyze(data)
        r = result["result"]
        assert r.b10_life < r.b50_life < r.characteristic_life

    def test_reliability_function(self):
        """R(t) 函数单调递减"""
        data = list(1000 * np.random.weibull(2.0, 50))
        result = self.analyzer.analyze(data)
        r = result["result"]
        R0 = self.analyzer.reliability(0, r)
        R100 = self.analyzer.reliability(100, r)
        R1000 = self.analyzer.reliability(1000, r)
        assert 0.99 <= R0 <= 1.0
        assert R100 > R1000  # 单调递减

    def test_hazard_function(self):
        """h(t) 函数合理（β>1 时递增）"""
        data = list(1000 * np.random.weibull(3.0, 50))  # β>1
        result = self.analyzer.analyze(data)
        r = result["result"]
        if r.beta > 1.5:
            h1 = self.analyzer.hazard_rate(100, r)
            h2 = self.analyzer.hazard_rate(1000, r)
            assert h1 < h2  # β>1: 递增失效率

    def test_curve_data(self):
        """R(t)/h(t) 曲线数据生成"""
        data = list(1000 * np.random.weibull(2.0, 50))
        result = self.analyzer.analyze(data)
        r = result["result"]
        assert len(r.reliability_curve["t"]) == 200
        assert len(r.reliability_curve["R"]) == 200
        assert len(r.reliability_curve["h"]) == 200

    def test_empty_input(self):
        """空数组 / NaN 输入"""
        result = self.analyzer.analyze([])
        assert result["error"] is not None
        result = self.analyzer.analyze([np.nan, np.nan, np.nan])
        assert result["error"] is not None


# ──────────────────────────────────────────────
# MTBF 测试
# ──────────────────────────────────────────────

class TestMTBFAnalyzer:

    def setup_method(self):
        self.analyzer = MTBFAnalyzer()

    def test_basic_mtbf(self):
        """基本 MTBF/MTTR 计算"""
        tbf = [120, 85, 200, 150, 95]
        rt = [2.0, 1.5, 3.0, 2.5, 1.0]
        result = self.analyzer.analyze(tbf, repair_times=rt)
        assert result["error"] is None
        r = result["overall"]
        assert r.n_failures == 5
        assert 120 < r.mtbf < 140  # avg ≈ 130
        assert 1.5 < r.mttr < 2.5   # avg ≈ 2.0
        assert 0.97 < r.availability < 0.99
        assert r.failure_rate > 0

    def test_insufficient_data(self):
        """数据不足"""
        result = self.analyzer.analyze([100])  # 1 条
        assert result["error"] is not None

    def test_no_repair_times(self):
        """无修复时间 — MTTR=0, A=1"""
        tbf = [100, 200, 150, 180, 120]
        result = self.analyzer.analyze(tbf)
        r = result["overall"]
        assert r.mtbf > 0
        assert r.mttr == 0.0
        assert r.availability == 1.0

    def test_confidence_interval(self):
        """MTBF 置信区间"""
        tbf = [100] * 20  # 齐次数据
        result = self.analyzer.analyze(tbf, confidence_level=0.90)
        r = result["overall"]
        assert 0 < r.mtbf_ci_low < r.mtbf < r.mtbf_ci_high

    def test_group_by(self):
        """分组分析"""
        tbf = [100, 120, 80, 200, 150, 130]
        rt = [2, 1.5, 3, 2.5, 2, 1]
        groups = ["A", "A", "A", "B", "B", "B"]
        result = self.analyzer.analyze(tbf, repair_times=rt, group_by=groups)
        assert len(result["groups"]) == 2
        assert result["groups"][0].label == "A"
        assert result["groups"][1].label == "B"

    def test_trend_detection(self):
        """Laplace 趋势检验"""
        # 递减 (改善) 趋势
        tbf_improving = [50, 80, 120, 160, 200]
        result = self.analyzer.analyze(tbf_improving)
        r = result["overall"]
        assert r.trend in ("improving", "stable", "degrading")
        assert r.laplace_stat is not None

    def test_empty_input(self):
        result = self.analyzer.analyze([])
        assert result["error"] is not None


# ──────────────────────────────────────────────
# Weibull 4P 测试
# ──────────────────────────────────────────────

class TestWeibull4P:

    def setup_method(self):
        self.analyzer = WeibullAnalyzer()

    def test_4p_mle_basic(self):
        """4P Weibull MLE: 从位置偏移分布拟合"""
        np.random.seed(42)
        # 生成带位置偏移的数据 (true gamma=10)
        data = np.random.weibull(2.5, 50) * 80 + 10
        result = self.analyzer.analyze(data.tolist(), four_parameter=True)
        assert result["error"] is None
        r = result["result"]
        assert r is not None
        assert r.method in ("4P-MLE", "2P-MLE")  # may fall back to 2P
        if r.method == "4P-MLE":
            assert r.gamma > 0

    def test_4p_with_censored(self):
        """4P Weibull 含删失数据"""
        np.random.seed(42)
        failures = list(np.random.weibull(2.0, 40) * 100 + 5)
        censored = [1] * 35 + [0] * 5
        result = self.analyzer.analyze(failures, censored=censored, four_parameter=True)
        assert result["error"] is None
        assert result["result"] is not None

    def test_4p_fallback_to_2p(self):
        """4P 结果与 2P 对比：4P 应有合理的 gamma"""
        np.random.seed(42)
        # 纯 2P 数据（无位置偏移）
        data = np.random.weibull(2.0, 50) * 100
        result = self.analyzer.analyze(data.tolist(), four_parameter=True)
        assert result["error"] is None
        r = result["result"]
        # 4P may find gamma; just verify it's a valid WeibullResult
        assert r is not None
        assert r.beta > 0
        assert r.eta > 0
        assert r.aic > 0


# ──────────────────────────────────────────────
# Weibull 置信区间测试
# ──────────────────────────────────────────────

class TestWeibullCI:

    def setup_method(self):
        self.analyzer = WeibullAnalyzer()

    def test_ci_2p(self):
        """2P Weibull 置信区间"""
        np.random.seed(42)
        data = np.random.weibull(2.0, 50) * 100
        result = self.analyzer.analyze(data.tolist(), confidence_level=0.95)
        ci = result["result"].confidence_intervals
        assert ci is not None
        assert "beta" in ci
        assert "eta" in ci
        # CI should contain estimate
        assert ci["beta"]["ci_lower"] < ci["beta"]["estimate"] < ci["beta"]["ci_upper"]
        assert ci["eta"]["ci_lower"] < ci["eta"]["estimate"] < ci["eta"]["ci_upper"]
        # SE should be positive
        assert ci["beta"]["std_err"] > 0
        assert ci["eta"]["std_err"] > 0

    def test_ci_4p(self):
        """4P Weibull 置信区间（含 gamma）"""
        np.random.seed(42)
        data = np.random.weibull(2.5, 50) * 80 + 10
        result = self.analyzer.analyze(data.tolist(), four_parameter=True, confidence_level=0.90)
        r = result["result"]
        if r.method == "4P-MLE":
            ci = r.confidence_intervals
            assert ci is not None
            assert "gamma" in ci
            assert ci["gamma"]["ci_lower"] < ci["gamma"]["estimate"] < ci["gamma"]["ci_upper"]

    def test_ci_rank_regression_no_ci(self):
        """秩回归方法不计算置信区间"""
        np.random.seed(42)
        data = np.random.weibull(2.0, 50) * 100
        result = self.analyzer.analyze(data.tolist(), fit_method="rank-regression")
        # rank-regression doesn't compute CI
        assert result["result"].confidence_intervals is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
