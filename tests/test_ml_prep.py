"""v4.0.0 P0 — 机器学习数据准备层（任务判定 / 体检 / 切分 / 预处理流水线）。"""

import numpy as np
import pandas as pd
import pytest

from analysis.ml import common, prep


def _frame(n=120, seed=7):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "直径": rng.normal(10, 0.3, n),
        "温度": rng.normal(60, 5, n),
        "设备": rng.choice(["A", "B", "C"], n),
        "班次": rng.choice(["早", "晚"], n),
        "强度": rng.normal(50, 4, n),          # 回归目标
        "判定": rng.choice(["OK", "NG"], n),   # 分类目标
        "结果码": rng.integers(0, 2, n),       # 0/1 数值 → 分类
    })


# ---------------- 任务类型判定 ----------------

class TestTaskDetection:

    def test_continuous_numeric_is_regression(self):
        assert common.detect_task_type(_frame()["强度"]) == common.TASK_REGRESSION

    def test_text_is_classification(self):
        assert common.detect_task_type(_frame()["判定"]) == common.TASK_CLASSIFICATION

    def test_binary_integer_is_classification(self):
        assert common.detect_task_type(_frame()["结果码"]) == common.TASK_CLASSIFICATION

    def test_explicit_task_overrides_detection(self):
        # 强度是连续列，显式指定 classification 时应被接受（用户可手动覆盖）
        assert common.detect_task_type(
            _frame()["强度"], task="classification") == common.TASK_CLASSIFICATION
        assert common.detect_task_type(
            _frame()["判定"], task="回归") == common.TASK_REGRESSION

    def test_invalid_task_rejected(self):
        with pytest.raises(common.MLDataError, match="不支持的任务类型"):
            common.detect_task_type(_frame()["强度"], task="clustering")


# ---------------- 数据集校验 ----------------

class TestValidateDataset:

    def test_groups_numeric_and_categorical(self):
        info = common.validate_dataset(_frame(), "强度",
                                       features=["直径", "设备", "班次"])
        assert info["task"] == common.TASK_REGRESSION
        assert info["numeric_features"] == ["直径"]
        assert info["categorical_features"] == ["设备", "班次"]
        assert info["n_rows"] == 120

    def test_default_features_exclude_target(self):
        info = common.validate_dataset(_frame(), "判定")
        assert "判定" not in info["features"]
        assert "直径" in info["features"]
        assert info["task"] == common.TASK_CLASSIFICATION

    def test_target_nan_rows_dropped(self):
        df = _frame(n=30)
        df.loc[df.index[:3], "强度"] = np.nan
        info = common.validate_dataset(df, "强度")
        assert info["n_rows"] == 27
        assert info["n_dropped_target_na"] == 3

    def test_errors(self):
        with pytest.raises(common.MLDataError, match="数据表为空"):
            common.validate_dataset(pd.DataFrame(), "强度")
        with pytest.raises(common.MLDataError, match="目标列不存在"):
            common.validate_dataset(_frame(), "不存在")
        with pytest.raises(common.MLDataError, match="特征列不存在"):
            common.validate_dataset(_frame(), "强度", features=["不存在"])
        with pytest.raises(common.MLDataError, match="至少需要一个特征列"):
            common.validate_dataset(_frame()[["强度"]], "强度")
        with pytest.raises(common.MLDataError, match="有效样本不足"):
            common.validate_dataset(_frame(n=10), "强度")

    def test_single_class_rejected(self):
        df = _frame(n=40)
        df["判定"] = "OK"
        with pytest.raises(common.MLDataError, match="至少需要 2 个类别"):
            common.validate_dataset(df, "判定")


# ---------------- 切分与预处理流水线 ----------------

class TestPrepareData:

    def test_split_sizes_and_reproducibility(self):
        df = _frame()
        a = prep.prepare_data(df, "强度", features=["直径", "温度", "设备"],
                              test_size=0.25, random_state=1)
        b = prep.prepare_data(df, "强度", features=["直径", "温度", "设备"],
                              test_size=0.25, random_state=1)
        assert a["summary"]["n_train"] == 90
        assert a["summary"]["n_test"] == 30
        assert list(a["X_test"].index) == list(b["X_test"].index)
        assert a["task"] == common.TASK_REGRESSION

    def test_stratified_split_keeps_class_ratio(self):
        df = _frame(n=200)
        result = prep.prepare_data(df, "判定", test_size=0.3, random_state=3)
        assert result["summary"]["stratified"] is True
        train_ratio = (result["y_train"] == "OK").mean()
        test_ratio = (result["y_test"] == "OK").mean()
        assert abs(train_ratio - test_ratio) < 0.08

    def test_invalid_test_size(self):
        with pytest.raises(ValueError, match="test_size"):
            prep.prepare_data(_frame(), "强度", test_size=1.5)

    def test_pipeline_handles_missing_and_unseen_categories(self):
        df = _frame()
        df.loc[df.index[:5], "直径"] = np.nan
        df.loc[df.index[:2], "设备"] = np.nan
        result = prep.prepare_data(df, "强度",
                                   features=["直径", "设备"], random_state=5)
        pipe = result["pipeline"]
        X_train = result["X_train"].copy()
        pipe.fit(X_train, result["y_train"])

        X_new = X_train.iloc[:6].copy()
        X_new.iloc[0, X_new.columns.get_loc("直径")] = np.nan
        X_new.iloc[1, X_new.columns.get_loc("设备")] = "新设备"   # 未见类别
        transformed = pipe.named_steps["prep"].transform(X_new)
        assert np.isfinite(np.asarray(transformed, dtype=float)).all()

    def test_scaler_fitted_on_train_only(self):
        """防泄漏：标准化统计量必须来自训练集，而非全量数据。"""
        df = _frame()
        result = prep.prepare_data(df, "强度", features=["直径"],
                                   test_size=0.3, random_state=11)
        pipe = result["pipeline"]
        pipe.fit(result["X_train"], result["y_train"])
        scaler = (pipe.named_steps["prep"]
                  .named_transformers_["num"].named_steps["scaler"])
        train_mean = result["X_train"]["直径"].mean()
        assert scaler.mean_[0] == pytest.approx(train_mean)
        assert scaler.mean_[0] != pytest.approx(df["直径"].mean())

    def test_binning_branch(self):
        df = _frame()
        result = prep.prepare_data(df, "强度", features=["直径", "温度"],
                                   bin_features=["温度"], n_bins=4,
                                   random_state=7)
        pipe = result["pipeline"]
        pipe.fit(result["X_train"], result["y_train"])
        matrix = pipe.named_steps["prep"].transform(result["X_test"])
        names = list(pipe.named_steps["prep"].get_feature_names_out())
        assert len(names) == matrix.shape[1]
        bin_col = names.index("温度")
        assert len(np.unique(np.asarray(matrix)[:, bin_col])) <= 4

    def test_encoded_feature_names_after_fit(self):
        df = _frame()
        result = prep.prepare_data(df, "判定", features=["直径", "设备"],
                                   random_state=9)
        pipe = result["pipeline"]
        pipe.fit(result["X_train"], result["y_train"])
        names = list(pipe.named_steps["prep"].get_feature_names_out())
        assert any(name.startswith("设备_") for name in names)
        assert "直径" in names


# ---------------- 体检摘要 ----------------

class TestDescribeDataset:

    def test_summary_fields(self):
        out = prep.describe_dataset(_frame(), target="判定",
                                    features=["直径", "设备"])
        assert out["analysis_type"] == "ml.prep_summary"
        assert out["task"] == common.TASK_CLASSIFICATION
        kinds = {c["name"]: c["kind"] for c in out["columns"]}
        assert kinds == {"直径": "numeric", "设备": "categorical"}
        assert set(out["class_counts"]) == {"OK", "NG"}

    def test_requires_target(self):
        with pytest.raises(ValueError, match="目标列"):
            prep.describe_dataset(_frame())
