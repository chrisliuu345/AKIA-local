"""AI 根因分析 — 三路证据融合（SHAP 特征重要性 + 相关性 + 异常联动）

当 SPC 检出违规点时，自动分析违规列与其他测量列的关系，
输出按综合得分排序的候选根因列表。

    根因得分 = 0.4 × 特征重要性 + 0.3 × 相关系数 + 0.3 × 异常联动度

SHAP 不可用时自动降级为 RandomForest feature_importances_。
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class RootCause:
    column: str
    score: float
    importance: float
    correlation: float
    anomaly_linkage: int
    explanation: str = ""


def _check_shap():
    try:
        import shap  # noqa: F401
        return True
    except Exception:
        return False


class RootCauseAnalyzer:
    MIN_ROWS = 12

    def __init__(self, n_estimators: int = 100, use_shap: bool = True,
                 max_rows: int = 1000, shap_rows: int = 300,
                 random_state: int = 42,
                 w_importance: float | None = None, w_correlation: float | None = None,
                 w_linkage: float | None = None):
        from config.settings import (
            ROOT_CAUSE_W_IMPORTANCE, ROOT_CAUSE_W_CORRELATION, ROOT_CAUSE_W_LINKAGE,
        )
        self.n_estimators = n_estimators
        self.use_shap = use_shap and _check_shap()
        self.max_rows = max_rows
        self.shap_rows = shap_rows
        self.random_state = random_state
        self.W_IMPORTANCE = w_importance if w_importance is not None else ROOT_CAUSE_W_IMPORTANCE
        self.W_CORRELATION = w_correlation if w_correlation is not None else ROOT_CAUSE_W_CORRELATION
        self.W_LINKAGE = w_linkage if w_linkage is not None else ROOT_CAUSE_W_LINKAGE

    def analyze(self, df: pd.DataFrame, target_column: str,
                violations: list[dict] | None = None,
                subgroup_size: int = 1,
                top_k: int = 8) -> dict[str, Any]:
        """
        参数:
            df: 原始数据表（含全部列）
            target_column: 发生违规的目标列
            violations: SPC 违规点列表 [{"point": 1-based序号, ...}]
            subgroup_size: 子组大小（I-MR/CUSUM/EWMA 传 1）
            top_k: 返回根因条数
        返回:
            {"causes": [RootCause], "method": "shap"|"rf",
             "n_violation_rows": int, "error": str|None}
        """
        out = {"causes": [], "method": "shap" if self.use_shap else "rf",
               "n_violation_rows": 0, "error": None}

        if df is None or df.empty:
            out["error"] = "数据为空"
            return out
        if target_column not in df.columns:
            out["error"] = f"目标列 '{target_column}' 不存在"
            return out

        y = pd.to_numeric(df[target_column], errors="coerce")
        valid_y = y.notna()
        if valid_y.sum() < self.MIN_ROWS:
            out["error"] = f"目标列有效数据不足（{valid_y.sum()} 行，至少 {self.MIN_ROWS} 行）"
            return out

        feature_cols = []
        for c in df.columns:
            if c == target_column:
                continue
            s = pd.to_numeric(df[c], errors="coerce")
            if s.notna().sum() >= self.MIN_ROWS and s.std() > 0:
                feature_cols.append(c)

        if not feature_cols:
            out["error"] = "没有可用的特征列（需要至少 1 个数值列作为候选根因）"
            return out

        X = df.loc[valid_y, feature_cols].apply(pd.to_numeric, errors="coerce")
        yv = y[valid_y].astype(float)
        X = X.fillna(X.median(numeric_only=True)).fillna(0.0)

        if len(X) > self.max_rows:
            idx = X.sample(self.max_rows, random_state=self.random_state).index.sort_values()
            X, yv = X.loc[idx], yv.loc[idx]

        importance, method = self._compute_feature_importance(X, yv)
        out["method"] = method
        correlation = self._compute_correlations(X, yv)
        violation_rows = self._violation_row_indices(
            violations, subgroup_size, len(df))
        out["n_violation_rows"] = len(violation_rows)
        linkage = self._compute_anomaly_linkage(df, feature_cols, violation_rows)

        causes = self._rank_causes(feature_cols, importance, correlation,
                                   linkage, len(violation_rows))
        out["causes"] = causes[:top_k]
        return out

    def _compute_feature_importance(self, X: pd.DataFrame, y: pd.Series):
        from sklearn.ensemble import RandomForestRegressor

        model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1,
        )
        model.fit(X, y)

        if self.use_shap:
            try:
                import shap
                Xs = X.sample(min(len(X), self.shap_rows),
                              random_state=self.random_state)
                explainer = shap.TreeExplainer(model)
                sv = explainer.shap_values(Xs)
                imp = np.abs(np.asarray(sv)).mean(axis=0)
                if imp.shape[0] == len(X.columns) and np.isfinite(imp).all():
                    return imp, "shap"
            except Exception:
                pass
        return np.asarray(model.feature_importances_), "rf"

    def _compute_correlations(self, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
        from scipy import stats as sp_stats

        result: dict[str, float] = {}
        yv = y.to_numpy(dtype=float)
        for c in X.columns:
            xv = X[c].to_numpy(dtype=float)
            mask = np.isfinite(xv) & np.isfinite(yv)
            if mask.sum() < 8 or np.std(xv[mask]) == 0:
                result[c] = 0.0
                continue
            try:
                rp = abs(sp_stats.pearsonr(xv[mask], yv[mask])[0])
            except Exception:
                rp = 0.0
            try:
                rs = abs(sp_stats.spearmanr(xv[mask], yv[mask])[0])
            except Exception:
                rs = 0.0
            result[c] = float(max(rp if np.isfinite(rp) else 0.0,
                                  rs if np.isfinite(rs) else 0.0))
        return result

    @staticmethod
    def _violation_row_indices(violations: list[dict] | None,
                               subgroup_size: int, n_rows: int) -> list[int]:
        if not violations:
            return []
        sg = max(int(subgroup_size), 1)
        rows: set = set()
        for v in violations:
            try:
                point = int(v.get("point", 0))
            except (TypeError, ValueError):
                continue
            if point < 1:
                continue
            start = (point - 1) * sg
            for r in range(start, min(start + sg, n_rows)):
                rows.add(r)
        return sorted(rows)

    def _compute_anomaly_linkage(self, df: pd.DataFrame,
                                 feature_cols: list[str],
                                 violation_rows: list[int]) -> dict[str, int]:
        linkage = {c: 0 for c in feature_cols}
        if not violation_rows:
            return linkage

        for c in feature_cols:
            s = pd.to_numeric(df[c], errors="coerce")
            mean, std = s.mean(), s.std()
            if not std or not np.isfinite(std):
                continue
            z = (s - mean) / std
            linkage[c] = int((z.iloc[violation_rows].abs() > 2).sum())
        return linkage

    @staticmethod
    def _normalize(values: np.ndarray) -> np.ndarray:
        vmax = float(np.max(values)) if len(values) else 0.0
        if vmax <= 0:
            return np.zeros_like(values)
        return values / vmax

    def _rank_causes(self, cols: list[str],
                     importance: np.ndarray,
                     correlation: dict[str, float],
                     linkage: dict[str, int],
                     n_viol_rows: int) -> list[RootCause]:
        imp_norm = self._normalize(np.asarray(importance, dtype=float))
        corr_arr = np.array([correlation.get(c, 0.0) for c in cols])
        corr_norm = self._normalize(corr_arr)
        link_arr = np.array([linkage.get(c, 0) for c in cols], dtype=float)
        link_norm = self._normalize(link_arr)

        causes: list[RootCause] = []
        for i, c in enumerate(cols):
            score = (self.W_IMPORTANCE * imp_norm[i]
                     + self.W_CORRELATION * corr_norm[i]
                     + self.W_LINKAGE * link_norm[i])
            cause = RootCause(
                column=c,
                score=round(float(score), 4),
                importance=round(float(imp_norm[i]), 4),
                correlation=round(float(corr_arr[i]), 4),
                anomaly_linkage=int(link_arr[i]),
            )
            cause.explanation = self._explain(cause, cols, imp_norm, n_viol_rows)
            causes.append(cause)

        causes.sort(key=lambda x: x.score, reverse=True)
        return causes

    @staticmethod
    def _explain(cause: RootCause, cols: list[str],
                 imp_norm: np.ndarray, n_viol_rows: int) -> str:
        parts: list[str] = []
        if cause.importance >= 0.9:
            parts.append("特征重要性最高")
        elif cause.importance >= 0.6:
            parts.append("特征重要性较高")

        r = cause.correlation
        if r >= 0.7:
            parts.append(f"与目标列强相关 (r={r:.2f})")
        elif r >= 0.4:
            parts.append(f"与目标列中等相关 (r={r:.2f})")

        if n_viol_rows and cause.anomaly_linkage:
            ratio = cause.anomaly_linkage / max(n_viol_rows, 1)
            if ratio >= 0.5:
                parts.append(f"{cause.anomaly_linkage}/{n_viol_rows} 个异常点同时超限")
            else:
                parts.append(f"{cause.anomaly_linkage} 个异常点处联动")

        if not parts:
            parts.append("与异常关联较弱，作为参考项")
        return "；".join(parts)
