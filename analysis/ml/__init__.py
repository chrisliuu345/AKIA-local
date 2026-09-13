"""预测分析与机器学习引擎（v4.0.0）。

模块划分（按需导入，保持应用启动轻量）:
    common.py   数据契约 / 任务类型判定 / 数据集校验
    prep.py     预处理流水线（缺失值 / 编码 / 分箱 / 标准化）+ 切分
    trees.py    CART 分类回归树（预剪枝 / 后剪枝 / 规则导出）
    evaluate.py 指标 / 混淆矩阵 / ROC / 交叉验证 / 学习曲线 / 残差
    forest.py   随机森林（OOB / 特征重要性 / 置换重要性）
    boosting.py 梯度提升（sklearn HistGradientBoosting + 可选 XGBoost）
    explain.py  模型解释（SHAP + 原生重要性降级）
    mars.py     MARS 多元自适应回归（纯 numpy）
    automl.py   多模型 CV 排名与推荐

约定:
    - 本层禁止依赖 Qt（tests/test_layering.py 守卫）
    - 结果字典统一含 "analysis_type" 前缀 "ml."
"""

__all__ = [
    "common",
    "prep",
    "trees",
    "evaluate",
    "forest",
    "boosting",
    "explain",
    "mars",
    "automl",
]
