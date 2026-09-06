"""v3.4.0 可靠性模块集成测试 — 全流程验证"""

import numpy as np
import pandas as pd

from analysis.reliability.weibull import WeibullAnalyzer
from analysis.reliability.survival import kaplan_meier, cox_regression
from analysis.reliability.rbd import calculate_system_reliability
from analysis.reliability import warranty
from analysis.charts.chart_generator import generate_chart


class TestReliabilityIntegration:

    def test_full_weibull_analysis(self):
        """完整 Weibull 分析流程"""
        np.random.seed(42)
        data = np.random.weibull(2.5, 50) * 100
        analyzer = WeibullAnalyzer()

        # 2P
        r2 = analyzer.analyze(data.tolist())
        assert r2["error"] is None
        assert r2["result"].method == "2P-MLE"
        assert r2["result"].confidence_intervals is not None

        # 4P
        r4 = analyzer.analyze(data.tolist(), four_parameter=True)
        assert r4["error"] is None

    def test_full_survival_analysis(self):
        """完整生存分析流程"""
        np.random.seed(42)
        T = pd.Series(np.random.exponential(100, 80))
        E = pd.Series(np.random.binomial(1, 0.7, 80))

        # KM
        km = kaplan_meier(T, E)
        assert km["analysis_type"] == "reliability.survival.km"
        assert len(km["timeline"]) > 0

        # Cox
        df = pd.DataFrame({"T": T, "E": E, "X1": np.random.randn(80)})
        cox = cox_regression(df, "T", "E", ["X1"])
        assert cox["summary"]["concordance_index"] > 0

    def test_full_rbd_analysis(self):
        """完整 RBD 分析流程"""
        components = [
            {"name": "电源", "reliability": 0.98},
            {"name": "主板", "reliability": 0.95},
            {"name": "硬盘", "reliability": 0.90},
            {"name": "风扇", "reliability": 0.85},
        ]
        # 串联系统
        r_series = calculate_system_reliability(components, structure="series")
        assert r_series["summary"]["system_reliability"] < 0.85
        assert r_series["weakest_component"]["name"] == "风扇"

        # 并联系统
        r_parallel = calculate_system_reliability(components[:2], structure="parallel")
        assert r_parallel["summary"]["system_reliability"] > 0.98

        # k/n 表决
        r_kn = calculate_system_reliability(
            components[:3], structure="k_out_of_n", k_out_of_n={"k": 2, "n": 3}
        )
        assert 0.5 < r_kn["summary"]["system_reliability"] < 1.0

    def test_full_warranty_analysis(self):
        """完整保修分析流程"""
        np.random.seed(42)
        data = pd.Series(np.random.weibull(2.5, 50) * 100)
        result = warranty.analyze(
            data, warranty_period=50, cost_per_failure=500, total_units=1000
        )
        assert result["summary"]["expected_failures"] > 0
        assert result["summary"]["warranty_cost_estimate"] > 0

    def test_chart_generation_all_new_types(self):
        """验证所有新增图表类型可渲染"""
        import matplotlib
        matplotlib.use("Agg")

        charts = {
            "KM生存曲线": {
                "timeline": [0, 10, 20, 30, 40, 50],
                "survival_function": [1.0, 0.9, 0.8, 0.7, 0.6, 0.5],
                "confidence_lower": [0.95, 0.85, 0.75, 0.65, 0.55, 0.45],
                "confidence_upper": [1.0, 0.95, 0.85, 0.75, 0.65, 0.55],
                "label": "Treatment",
            },
            "KM双组对比": {
                "group_a": {"timeline": [0, 10, 20], "survival_function": [1.0, 0.8, 0.6],
                            "confidence_lower": [0.95, 0.75, 0.55], "confidence_upper": [1.0, 0.85, 0.65], "label": "A"},
                "group_b": {"timeline": [0, 10, 20], "survival_function": [1.0, 0.7, 0.4],
                            "confidence_lower": [0.95, 0.65, 0.35], "confidence_upper": [1.0, 0.75, 0.45], "label": "B"},
                "summary": {"logrank_p_value": 0.03},
            },
            "RBD框图": {
                "components": [{"name": "A", "reliability": 0.95}, {"name": "B", "reliability": 0.90}],
                "summary": {"structure": "series", "system_reliability": 0.855},
            },
            "保修成本图": {
                "summary": {
                    "reliability_at_warranty_end": 0.85,
                    "failure_probability": 0.15,
                    "expected_failures": 150,
                    "warranty_cost_estimate": 75000,
                    "cost_per_failure": 500,
                    "total_units": 1000,
                },
            },
        }

        for name, data_dict in charts.items():
            fig = generate_chart(name, data_dict)
            assert fig is not None
            import matplotlib.pyplot as plt
            plt.close(fig)
