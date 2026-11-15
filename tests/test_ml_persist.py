"""v4.0.0 P4 — 模型持久化（.qamodel 保存 / 加载 / 预测）。"""

from pathlib import Path

import pandas as pd
import pytest

from analysis.ml import persist, train


def _frame(n=140, seed=41):
    import numpy as np
    rng = np.random.default_rng(seed)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    return pd.DataFrame({
        "温度": x1,
        "压力": x2,
        "判定": ["OK" if v > 0 else "NG" for v in x1 + x2 + rng.normal(0, 0.4, n)],
        "强度": 2.5 * x1 - x2 + rng.normal(0, 0.3, n),
    })


class TestSaveLoad:

    def test_roundtrip_regression(self, tmp_path):
        df = _frame()
        fit = train.fit_pipeline(df, "强度", ["温度", "压力"], model="tree",
                                 cv=3, random_state=5)
        path = persist.save_model(tmp_path / "model", fit["pipeline"],
                                  task=fit["task"], target="强度",
                                  features=fit["features"], model=fit["model"],
                                  params=fit["params"], metrics=fit["metrics"])
        assert path.endswith(persist.MODEL_EXT)
        bundle = persist.load_model(path)
        assert bundle["format"] == persist.FORMAT_NAME
        assert bundle["task"] == "regression"
        assert bundle["features"] == ["温度", "压力"]
        assert bundle["metrics"]["test"]["r2"] > 0.5
        info = persist.model_info(path)
        assert "pipeline" not in info

    def test_roundtrip_classification_with_probability(self, tmp_path):
        df = _frame()
        fit = train.fit_pipeline(df, "判定", ["温度", "压力"], model="forest",
                                 cv=3, random_state=5,
                                 params={"n_estimators": 40})
        path = persist.save_model(tmp_path / "cls.qamodel", fit["pipeline"],
                                  task=fit["task"], target="判定",
                                  features=fit["features"])
        predictions = persist.predict_frame(persist.load_model(path), df)
        assert "预测值" in predictions.columns
        assert "预测概率" in predictions.columns
        assert len(predictions) == len(df)

    def test_missing_file_rejected(self, tmp_path):
        with pytest.raises(persist.ModelFileError, match="不存在"):
            persist.load_model(tmp_path / "nope.qamodel")

    def test_foreign_file_rejected(self, tmp_path, monkeypatch):
        import joblib

        loaded = []

        def _spy(source):
            loaded.append(source)
            return joblib.load(source)

        monkeypatch.setattr(persist.joblib, "load", _spy)
        bad = tmp_path / "bad.qamodel"
        joblib.dump({"format": "something-else"}, bad)
        with pytest.raises(persist.ModelFileError, match="HMAC"):
            persist.load_model(bad)
        assert loaded == []

    def test_tampered_signature_does_not_unpickle(self, tmp_path, monkeypatch):
        loaded = []

        def _spy(_source):
            loaded.append(True)

        monkeypatch.setattr(persist.joblib, "load", _spy)
        path = persist.save_model(tmp_path / "m.qamodel", {"marker": 1},
                                  task="regression", target="y", features=["x"])
        target = Path(path)
        raw = bytearray(target.read_bytes())
        raw[-1] ^= 0x01
        target.write_bytes(raw)
        with pytest.raises(persist.ModelFileError, match="HMAC"):
            persist.load_model(path)
        assert loaded == []

    def test_predict_requires_feature_columns(self, tmp_path):
        df = _frame()
        fit = train.fit_pipeline(df, "强度", ["温度", "压力"], model="linear")
        path = persist.save_model(tmp_path / "m.qamodel", fit["pipeline"],
                                  task=fit["task"], target="强度",
                                  features=fit["features"])
        with pytest.raises(persist.ModelFileError, match="缺少模型所需特征列"):
            persist.predict_frame(persist.load_model(path), df[["判定"]])
