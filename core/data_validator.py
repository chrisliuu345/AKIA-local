"""
数据校验模块 — 缺失值检测、异常值检测、正态性预检、数据完整性验证
"""

from typing import Dict, List, Any
import pandas as pd
from scipy import stats


class DataValidator:
    """数据质量校验引擎"""

    def __init__(self):
        self.warnings: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.stats: Dict[str, Any] = {}

    def validate(self, df: pd.DataFrame, measurement_cols: List[str]) -> Dict[str, Any]:
        self.warnings.clear()
        self.errors.clear()
        self.stats.clear()

        self._check_empty(df)
        self._check_missing(df, measurement_cols)
        self._check_outliers(df, measurement_cols)
        self._check_duplicates(df)
        self._compute_summary(df, measurement_cols)

        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self.stats,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }

    def _check_empty(self, df: pd.DataFrame) -> None:
        if df.empty:
            self.errors.append({"type": "empty", "message": "数据框为空"})

    def _check_missing(self, df: pd.DataFrame, measurement_cols: List[str]) -> None:
        total_rows = len(df)
        for col in measurement_cols:
            if col not in df.columns:
                self.errors.append({"type": "missing_column", "column": col, "message": f"测量列 '{col}' 不存在"})
                continue
            missing = df[col].isna().sum()
            if missing > 0:
                pct = missing / total_rows * 100
                level = "error" if pct > 50 else "warning" if pct > 10 else "info"
                msg = {
                    "type": "missing_values",
                    "column": col,
                    "count": int(missing),
                    "percentage": round(pct, 2),
                    "level": level,
                    "message": f"列 '{col}' 存在 {missing} 个缺失值 ({pct:.1f}%)",
                }
                if level == "error":
                    self.errors.append(msg)
                else:
                    self.warnings.append(msg)

    def _check_outliers(self, df: pd.DataFrame, measurement_cols: List[str]) -> None:
        for col in measurement_cols:
            if col not in df.columns:
                continue
            data = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(data) < 4:
                continue

            q1 = data.quantile(0.25)
            q3 = data.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outlier_mask = (data < lower) | (data > upper)
            outlier_count = outlier_mask.sum()

            if outlier_count > 0:
                self.warnings.append({
                    "type": "outliers",
                    "column": col,
                    "count": int(outlier_count),
                    "percentage": round(outlier_count / len(data) * 100, 2),
                    "lower_bound": round(lower, 4),
                    "upper_bound": round(upper, 4),
                    "message": f"列 '{col}' 检测到 {outlier_count} 个异常值",
                })

    def _check_duplicates(self, df: pd.DataFrame) -> None:
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            self.warnings.append({
                "type": "duplicates",
                "count": int(dup_count),
                "message": f"检测到 {dup_count} 行重复数据",
            })

    def _compute_summary(self, df: pd.DataFrame, measurement_cols: List[str]) -> None:
        for col in measurement_cols:
            if col not in df.columns:
                continue
            data = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(data) == 0:
                continue

            mean = float(data.mean())
            std = float(data.std(ddof=1))
            median = float(data.median())
            data_min = float(data.min())
            data_max = float(data.max())

            is_constant = std < 1e-12 or std / (abs(mean) + 1e-9) < 1e-8
            if is_constant:
                skew_val, kurtosis_val = 0.0, 0.0
            else:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    skew_val = stats.skew(data)
                    kurtosis_val = stats.kurtosis(data)

            _statistic, p_value = stats.shapiro(data) if len(data) <= 5000 else (None, None)
            if len(data) > 5000 and not is_constant and std > 0:
                _statistic, p_value = stats.kstest(data, lambda x, m=mean, s=std: stats.norm.cdf(x, loc=m, scale=s))

            self.stats[col] = {
                "count": len(data),
                "mean": round(mean, 4),
                "std_dev": round(std, 4),
                "median": round(median, 4),
                "min": round(data_min, 4),
                "max": round(data_max, 4),
                "range": round(data_max - data_min, 4),
                "skewness": round(float(skew_val), 4),
                "kurtosis": round(float(kurtosis_val), 4),
                "normality_p_value": round(float(p_value), 6) if p_value is not None else None,
                "is_normal": p_value is not None and p_value > 0.05,
                "q1": round(float(data.quantile(0.25)), 4),
                "q3": round(float(data.quantile(0.75)), 4),
            }

    @staticmethod
    def check_normality(data: pd.Series) -> Dict[str, Any]:
        clean = data.dropna()
        n = len(clean)
        if n < 3:
            return {"is_normal": False, "reason": "数据量不足 (n<3)"}

        if n <= 5000:
            stat, p = stats.shapiro(clean)
            method = "Shapiro-Wilk"
        else:
            m_s, s_s = clean.mean(), clean.std()
            if s_s > 0:
                stat, p = stats.kstest(clean, lambda x: stats.norm.cdf(x, loc=m_s, scale=s_s))
                method = "Kolmogorov-Smirnov"
            else:
                stat, p = 0.0, 1.0
                method = "N/A (常数数据)"

        return {
            "is_normal": p > 0.05,
            "statistic": round(float(stat), 6),
            "p_value": round(float(p), 6),
            "method": method,
            "sample_size": n,
        }

    @staticmethod
    def check_variance_equality(*groups: pd.Series) -> Dict[str, Any]:
        clean_groups = [g.dropna() for g in groups if len(g.dropna()) >= 2]
        if len(clean_groups) < 2:
            return {"equal_variance": False, "reason": "有效组数不足"}

        stat, p = stats.levene(*clean_groups)
        return {
            "equal_variance": p > 0.05,
            "statistic": round(float(stat), 6),
            "p_value": round(float(p), 6),
            "method": "Levene",
        }
