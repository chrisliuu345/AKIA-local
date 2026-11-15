"""IE 四类已知值 — 标准工时、线平衡率、加权 OEE、工作抽样样本量（v4.7.0）。

出处：
- Freivalds, Niebel's Methods, Standards, and Work Design：
  正常时间 = 观测时间 × 评比系数，标准工时 = 正常时间 × (1 + 宽放)。
- 易树平、郭伏《基础工业工程》：线平衡率 = Σ工序时间 / (工位数 × 瓶颈时间)。
- Nakajima, Introduction to TPM：OEE = 可用率 × 性能 × 良品率；多项按时间和产量加权。
- 工作抽样样本量 n = Z² p (1-p) / E²。p=0.5、E=5%、95% 置信时 n=385。
"""

from analysis.ie.line_balance import LineBalanceEngine
from analysis.ie.oee import OEEEngine
from analysis.ie.time_study import TimeStudyEngine
from analysis.ie.work_sampling import WorkSamplingEngine
from core.data_objects import Process, Resource, TimeObservation
from tests.known_values import KnownValueCase, assert_close

_TIME = KnownValueCase.with_preset(
    "freivalds-standard-time", "Freivalds / Niebel",
    preset="closed_form",
    reference="ST = OT × rating × (1 + allowance)",
    notes="4 次观测不足剔除门槛，均值、正常时间和标准工时均为可整除闭式值",
)
_BALANCE = KnownValueCase.with_preset(
    "ie-line-balance-rate", "基础工业工程 线平衡率",
    preset="closed_form",
    reference="ΣCT / (工位数 × 瓶颈 CT) = 180 / (4 × 60)",
)
_OEE = KnownValueCase.with_preset(
    "nakajima-oee-weighted", "Nakajima TPM",
    preset="rounded_4dp",
    reference="A=Σ运转/Σ可用，P=Σ(理想节拍×产量)/Σ运转，Q=Σ良品/Σ产量",
    notes="引擎把三项和 OEE 四舍五入到 4 位小数",
)
_SAMPLE = KnownValueCase.with_preset(
    "work-sampling-n-385", "工作抽样样本量",
    preset="closed_form",
    reference="95% 置信、p=50%、绝对误差 5% 时 n=385",
)


def _obs(process: str, seconds: float, cycle: int) -> TimeObservation:
    return TimeObservation(process, "OP", cycle, seconds)


def test_freivalds_standard_time():
    result = TimeStudyEngine.analyze(
        [_obs("P1", 8, 1), _obs("P1", 10, 2), _obs("P1", 12, 3), _obs("P1", 10, 4)],
        rating=1.25, allowance_pct=20)
    row = result["results"][0]
    assert_close(row["avg_time"], 10.0, _TIME, context="观测时间均值")
    assert_close(row["normal_time"], 12.5, _TIME, context="正常时间")
    assert_close(row["standard_time"], 15.0, _TIME, context="标准工时")


def test_ie_line_balance_rate():
    processes = [
        Process("A", "取件", cycle_time=40),
        Process("B", "装配", cycle_time=50),
        Process("C", "检验", cycle_time=30),
        Process("D", "装箱", cycle_time=60),
    ]
    current = LineBalanceEngine().analyze(processes)["current"]
    assert_close(current["balance_rate"], 0.75, _BALANCE, context="线平衡率")
    assert_close(current["balance_loss"], 0.25, _BALANCE, context="平衡损失")
    assert current["bottleneck_id"] == "D"


def test_nakajima_weighted_oee():
    resources = [
        Resource(resource_id="M1", available_time=10, downtime=2,
                 ideal_cycle_time=60, total_qty=400, good_qty=380),
        Resource(resource_id="M2", available_time=8, downtime=1,
                 ideal_cycle_time=30, total_qty=600, good_qty=570),
    ]
    overall = OEEEngine().analyze(resources)["overall"]
    assert_close(overall["availability"], 15 / 18, _OEE, context="加权可用率")
    assert_close(overall["performance"], (7 / 9), _OEE, context="加权性能")
    assert_close(overall["quality"], 0.95, _OEE, context="加权良品率")
    assert_close(overall["oee"], (15 / 18) * (7 / 9) * 0.95, _OEE, context="OEE")


def test_work_sampling_sample_size_385():
    required = WorkSamplingEngine.sample_size_required(50.0, 5.0, 0.95)
    assert_close(required, 385, _SAMPLE, context="样本量")
