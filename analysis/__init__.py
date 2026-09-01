"""
QA-Tool 统计分析引擎

子包:
  spc         — 统计过程控制 (9种控制图)
  capability  — 过程能力分析 (正态/非正态/组间组内)
  msa         — 测量系统分析 (量具R&R/偏倚/线性/属性一致性)
  hypothesis  — 假设检验 (t检验/ANOVA/正态性/方差齐性/非参数检验)
  doe         — 实验设计 (因子设计/响应曲面/Box-Behnken)
  regression  — 回归分析 (线性/多元/残差诊断)
  ie          — IE 工业工程 (工时研究/工作抽样/线平衡/OEE/VSM)
  ai          — AI 智能分析 (根因分析 SHAP+RF+相关性)
  charts      — 图表生成 (通用图表生成器 12种图表)
  reliability — 可靠性工程 (Weibull寿命分析/MTBF/MTTR)
  time_series — 时间序列分析 (ACF/PACF/季节分解/指数平滑/ARIMA/预测)
"""
__all__ = ["spc", "capability", "msa", "hypothesis", "doe", "regression", "ie", "ai", "charts", "reliability", "time_series"]
