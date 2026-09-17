"""正态过程能力已知值 — Cp / Cpk / Pp / Ppk / Cpm / PPM / 合格率（v4.2.0 P1）。

来源: Montgomery, Introduction to Statistical Quality Control（能力指数定义）+
标准正态表（Φ(-2)=0.0227501, Φ(-3)=0.0013499, Φ(-4)=0.0000317）。
"""

import pandas as pd

from analysis.capability import normal_cap
from tests.known_values import KnownValueCase, assert_close

_CASE = KnownValueCase.with_preset(
    "montgomery-capability-asymmetric", "Montgomery SQC / 标准正态表",
    preset="rounded_4dp",
    reference="手算案例：数据 [-1,0,1]，s=1；规格 2/-4",
    notes="引擎输出 4 位小数，容差覆盖末位舍入",
)

_SYMMETRIC_CASE = KnownValueCase.with_preset(
    "normal-table-3sigma-two-sided", "标准正态表",
    preset="rounded_4dp",
    reference="±3σ 双侧理论不良率 0.27%（2700 ppm）",
    notes="数据 [-1,0,1]（s=1），规格 ±3；验证 ppm 与合格率的教科书已知值",
)


class TestNormalCapabilityKnownValues:
    def test_asymmetric_cp_cpk_ppm(self):
        result = normal_cap.analyze(
            pd.Series([-1.0, 0.0, 1.0]), usl=2.0, lsl=-4.0, target=0.0)
        cap = result["capability"]

        assert_close(cap["cp"], 1.0, _CASE, context="Cp = (USL-LSL)/6s")
        assert_close(cap["cpk"], 2.0 / 3.0, _CASE, context="Cpk = min(Cpu, Cpl)")
        assert_close(cap["cpm"], 1.0, _CASE, context="Cpm（目标 0）")
        assert_close(cap["pp"], 1.0, _CASE, context="Pp（s_overall=1）")
        assert_close(cap["ppk"], 2.0 / 3.0, _CASE, context="Ppk")
        assert_close(cap["ppm_usl"], 22750.13, _CASE,
                     context="P(X>2) = 0.0227501 → 22750.13 ppm")
        assert_close(cap["ppm_lsl"], 31.67, _CASE,
                     context="P(X<-4) = 3.167e-5 → 31.67 ppm")
        assert_close(cap["ppm_total"], 22781.80, _CASE,
                     context="双侧合计 22781.80 ppm")
        assert_close(cap["expected_yield_overall"], 97.72, _CASE,
                     context="100% − 2.27818%")

    def test_three_sigma_two_sided_known_values(self):
        result = normal_cap.analyze(
            pd.Series([-1.0, 0.0, 1.0]), usl=3.0, lsl=-3.0, target=0.0)
        cap = result["capability"]

        assert_close(cap["cp"], 1.0, _SYMMETRIC_CASE, context="Cp")
        assert_close(cap["cpk"], 1.0, _SYMMETRIC_CASE, context="Cpk")
        assert_close(cap["ppm_total"], 2699.80, _SYMMETRIC_CASE,
                     context="±3σ 双侧 0.27% → 2700 ppm 级")
        assert_close(cap["expected_yield_within"], 99.73, _SYMMETRIC_CASE,
                     context="±3σ 理论合格率 99.73%")
        assert_close(cap["sigma_level"], 3.0, _SYMMETRIC_CASE,
                     context="sigma_level = 3·Cpk")
