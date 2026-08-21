"""Weibull 寿命数据分析 — 2P/3P MLE 拟合 + 可靠性指标

使用 scipy.stats.weibull_min 进行极大似然估计 (MLE):
  - 2P Weibull: 固定 location=0
  - 3P Weibull: 自由 location (需要足够数据量才能稳定收敛)

输出:
  - 形状参数 β, 尺度参数 η, 位置参数 γ (3P)
  - B10 / B50 / 特征寿命
  - 可靠性函数 R(t), 失效率 λ(t)
  - 概率图 (Weibull Probability Plot)
  - 拟合优度 (AD 统计量, R²)
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.optimize import minimize


@dataclass
class WeibullResult:
    """Weibull 拟合结果"""
    beta: float                # 形状参数
    eta: float                 # 尺度参数
    gamma: float               # 位置参数 (2P 时为 0)
    method: str                # "2P-MLE" | "3P-MLE" | "rank-regression"
    loglik: float              # 对数似然值
    aic: float                 # AIC
    bic: float                 # BIC
    # 可靠性指标
    b10_life: float            # B10 寿命 (10% 失效)
    b50_life: float            # B50 寿命 / 中位寿命
    characteristic_life: float # 特征寿命 = η + γ
    mean_life: float           # 期望寿命
    # 拟合优度
    ad_statistic: float        # Anderson-Darling 统计量
    r_squared: float           # 概率图 R²
    # 图解数据
    probability_data: Dict[str, List[float]]  # {rank, prob, time} 用于概率图
    reliability_curve: Dict[str, List[float]] # {t, R, h} 用于 R(t)/h(t) 图


class WeibullAnalyzer:
    """Weibull 寿命分布分析器 — 支持完整/右删失数据"""

    MIN_POINTS = 5  # 最少数据点数

    def analyze(self, failure_times: list,
                censored: Optional[list] = None,
                fit_method: str = "mle",
                three_parameter: bool = False,
                confidence_level: float = 0.95) -> Dict[str, Any]:
        """主入口 — 对失效时间数据进行 Weibull 分析

        参数:
            failure_times: 失效时间 (或周期) 数组
            censored: 右删失指示数组 (1=失效, 0=删失)，默认全部为失效
            fit_method: "mle" | "rank-regression"
            three_parameter: 是否尝试 3P Weibull (需要有足够数据)
            confidence_level: 置信水平

        返回:
            {"result": WeibullResult, "warnings": [...], "error": str|None}
        """
        out: Dict[str, Any] = {
            "result": None, "warnings": [], "error": None,
        }

        # ── 数据清洗 ──
        ft = np.asarray(failure_times, dtype=float)
        valid = np.isfinite(ft) & (ft > 0)
        if valid.sum() < self.MIN_POINTS:
            out["error"] = f"有效失效时间数据不足（{valid.sum()} 点，至少 {self.MIN_POINTS} 点）"
            return out

        ft = ft[valid]
        if censored is not None:
            # W37 fix: 校验censored长度与failure_times匹配
            cen_raw = np.asarray(censored, dtype=int)
            if len(cen_raw) != len(failure_times):
                out["error"] = f"删失指示数组长度({len(cen_raw)})与失效时间数组长度({len(failure_times)})不匹配"
                return out
            cen = cen_raw[valid]
            if not np.any(cen == 1):
                out["warnings"].append("所有数据均为删失，无法估计形状参数")
        else:
            cen = np.ones(len(ft), dtype=int)

        failure_only = ft[cen == 1]
        if len(failure_only) < 3:
            out["error"] = "失效事件不足（至少需要 3 个失效点）"
            return out

        # W26 fix: 全部失效时间相等时拟合退化，提前检测
        if np.std(failure_only) == 0:
            out["warnings"].append("所有失效时间相同，Weibull拟合可能退化（β→0, η→极小值）")

        # ── 拟合 ──
        result: Optional[WeibullResult] = None

        if fit_method == "rank-regression":
            result = self._fit_rank_regression(ft, cen)
        else:
            # 先尝试 2P MLE (稳健)
            result = self._fit_2p_mle(failure_only, cen, ft)
            if three_parameter and len(failure_only) >= 10:
                try:
                    result_3p = self._fit_3p_mle(failure_only, cen, ft)
                    if result_3p and result_3p.aic < result.aic:
                        result = result_3p
                    else:
                        out["warnings"].append(
                            "3P Weibull 拟合未显著改善 (AIC ≥ 2P)，采用 2P 结果")
                except Exception as e:
                    out["warnings"].append(f"3P 拟合失败: {e}，采用 2P 结果")

        # ── 可靠性指标 ──
        if result:
            result.b10_life = self._b_life(result, 0.10)
            result.b50_life = self._b_life(result, 0.50)
            result.characteristic_life = result.eta + result.gamma
            if result.beta > 1:
                result.mean_life = result.gamma + result.eta * math.exp(
                    math.log(math.gamma(1 + 1 / result.beta)))
            else:
                result.mean_life = float("inf")

            # 拟合优度
            result.ad_statistic = self._anderson_darling(failure_only, result)
            result.r_squared = self._prob_plot_r2(failure_only, result)

            # 图解数据
            result.probability_data = self._probability_plot_data(failure_only, result)
            result.reliability_curve = self._reliability_curve_data(result)

        out["result"] = result
        return out

    # ──────────────────────────────────────────────
    # 2P Weibull MLE (γ=0)
    # ──────────────────────────────────────────────
    def _fit_2p_mle(self, failures: np.ndarray, censored: np.ndarray,
                    all_times: np.ndarray) -> WeibullResult:
        """MLE 拟合 2P Weibull (γ=0) — 最大化含删失的完整似然

        以 scipy 仅失效拟合结果为初值，再用 L-BFGS-B 优化含删失负对数似然，
        使右删失数据参与参数估计（修复: 旧实现删失仅进 loglik 不参与拟合）。
        """
        # 初值: 仅失效数据的 scipy MLE
        p2 = sp_stats.weibull_min.fit(failures, floc=0)
        beta0, _, eta0 = p2

        def neg_loglik(params):
            beta, eta = params
            if beta <= 0.1 or eta <= 0:
                return 1e12
            return -self._weibull_loglik(beta, eta, 0.0, all_times, censored)

        result = minimize(
            neg_loglik,
            x0=[beta0, eta0],
            bounds=[(0.2, 20), (1e-6, None)],
            method="L-BFGS-B",
        )

        if result.success:
            beta, eta = result.x
            loglik = -result.fun
        else:
            # 优化失败时回退 scipy 直接拟合结果
            beta, eta = float(beta0), float(eta0)
            loglik = self._weibull_loglik(beta, eta, 0.0, all_times, censored)

        gamma = 0.0
        n_params = 2
        n_total = len(all_times)
        aic = 2 * n_params - 2 * loglik
        bic = n_params * np.log(n_total) - 2 * loglik

        return WeibullResult(
            beta=round(float(beta), 6), eta=round(float(eta), 6),
            gamma=gamma, method="2P-MLE",
            loglik=loglik, aic=aic, bic=bic,
            b10_life=0.0, b50_life=0.0,
            characteristic_life=eta, mean_life=0.0,
            ad_statistic=0.0, r_squared=0.0,
            probability_data={}, reliability_curve={},
        )

    # ──────────────────────────────────────────────
    # 3P Weibull MLE (自由 γ)
    # ──────────────────────────────────────────────
    def _fit_3p_mle(self, failures: np.ndarray, censored: np.ndarray,
                    all_times: np.ndarray) -> Optional[WeibullResult]:
        """数值优化 3P Weibull — 以 2P 结果为初始值"""
        # 初始值
        p2 = sp_stats.weibull_min.fit(failures, floc=0)
        beta0, _, eta0 = p2
        gamma0 = np.min(failures) * 0.5

        def neg_loglik(params):
            beta, eta, gamma = params
            if beta <= 0.1 or eta <= 0 or gamma < 0 or gamma >= np.min(all_times):
                return 1e12
            return -self._weibull_loglik(beta, eta, gamma, all_times, censored)

        result = minimize(
            neg_loglik,
            x0=[beta0, eta0, gamma0],
            bounds=[(0.2, 20), (1e-6, None), (0, np.min(all_times) * 0.99)],
            method="L-BFGS-B",
        )

        if not result.success:
            return None

        beta, eta, gamma = result.x
        if gamma < 0 or gamma >= np.min(all_times) * 0.95:
            return None

        loglik = -result.fun
        n_params = 3
        n_total = len(all_times)
        aic = 2 * n_params - 2 * loglik
        bic = n_params * np.log(n_total) - 2 * loglik

        return WeibullResult(
            beta=round(beta, 6), eta=round(eta, 6),
            gamma=round(gamma, 6), method="3P-MLE",
            loglik=loglik, aic=aic, bic=bic,
            b10_life=0.0, b50_life=0.0,
            characteristic_life=eta + gamma, mean_life=0.0,
            ad_statistic=0.0, r_squared=0.0,
            probability_data={}, reliability_curve={},
        )

    # ──────────────────────────────────────────────
    # 秩回归 (Rank Regression / 中位秩)
    # ──────────────────────────────────────────────
    def _fit_rank_regression(self, all_times: np.ndarray,
                            censored: np.ndarray) -> WeibullResult:
        """中位秩 + 最小二乘 Weibull 拟合"""
        # 仅用失效点做秩回归
        failures = all_times[censored == 1]
        n = len(all_times)
        sorted_f = np.sort(failures)
        k = len(sorted_f)

        ranks = np.arange(1, k + 1)
        # Benard 中位秩近似
        F_i = (ranks - 0.3) / (n + 0.4)
        y = np.log(-np.log(1 - F_i))
        x = np.log(sorted_f)

        # 最小二乘: y = β·x - β·ln(η)
        slope, intercept, r, _, _ = sp_stats.linregress(x, y)
        beta = max(slope, 0.2)
        eta = np.exp(-intercept / beta)

        loglik = self._weibull_loglik(beta, eta, 0.0, all_times, censored)
        n_total = len(all_times)
        aic = 2 * 2 - 2 * loglik
        bic = 2 * np.log(n_total) - 2 * loglik

        return WeibullResult(
            beta=round(beta, 6), eta=round(eta, 6), gamma=0.0,
            method="rank-regression",
            loglik=loglik, aic=aic, bic=bic,
            b10_life=0.0, b50_life=0.0,
            characteristic_life=eta, mean_life=0.0,
            ad_statistic=0.0, r_squared=float(r ** 2),
            probability_data={}, reliability_curve={},
        )

    # ──────────────────────────────────────────────
    # 对数似然函数 (含右删失)
    # ──────────────────────────────────────────────
    @staticmethod
    def _weibull_loglik(beta: float, eta: float, gamma: float,
                        times: np.ndarray, censored: np.ndarray) -> float:
        """Weibull 对数似然 (含右删失)"""
        t = np.maximum(times - gamma, 1e-12)
        z = t / eta
        log_pdf = (np.log(beta) - np.log(eta)
                   + (beta - 1) * np.log(z) - z ** beta)
        log_sf = -(z ** beta)
        ll = np.sum(censored * log_pdf + (1 - censored) * log_sf)
        return float(ll)

    # ──────────────────────────────────────────────
    # 可靠性指标
    # ──────────────────────────────────────────────
    @staticmethod
    def _b_life(result: WeibullResult, p: float) -> float:
        """Bx 寿命: P(T ≤ t) = p 对应的时间"""
        if result.beta <= 0:
            return 0.0
        return result.gamma + result.eta * (-np.log(1 - p)) ** (1 / result.beta)

    def reliability(self, t: float, result: WeibullResult) -> float:
        """可靠性: R(t) = P(T > t)"""
        if t <= result.gamma:
            return 1.0
        z = (t - result.gamma) / result.eta
        return float(np.exp(-(z ** result.beta)))

    def hazard_rate(self, t: float, result: WeibullResult) -> float:
        """失效率: h(t) = f(t) / R(t)"""
        if t <= result.gamma:
            return 0.0
        z = (t - result.gamma) / result.eta
        return float((result.beta / result.eta) * (z ** (result.beta - 1)))

    # ──────────────────────────────────────────────
    # 拟合优度
    # ──────────────────────────────────────────────
    @staticmethod
    def _anderson_darling(failures: np.ndarray, result: WeibullResult) -> float:
        """Anderson-Darling 统计量"""
        sorted_f = np.sort(failures)
        n = len(sorted_f)
        if n < 2:
            return 0.0

        z = (sorted_f - result.gamma) / result.eta
        cdf = 1 - np.exp(-(z ** result.beta))
        cdf = np.clip(cdf, 1e-12, 1 - 1e-12)

        i = np.arange(1, n + 1)
        s1 = np.sum((2 * i - 1) * (np.log(cdf) + np.log(1 - cdf[::-1])))
        ad = -n - s1 / n
        return float(max(ad, 0.0))

    @staticmethod
    def _prob_plot_r2(failures: np.ndarray, result: WeibullResult) -> float:
        """概率图 R²"""
        n = len(failures)
        sorted_f = np.sort(failures)
        ranks = np.arange(1, n + 1)
        Fi = (ranks - 0.3) / (n + 0.4)
        y_obs = np.log(-np.log(1 - Fi))
        z = (sorted_f - result.gamma) / result.eta
        y_pred = result.beta * np.log(z)
        ss_res = np.sum((y_obs - y_pred) ** 2)
        ss_tot = np.sum((y_obs - np.mean(y_obs)) ** 2)
        if ss_tot < 1e-12:
            return 1.0
        return float(max(1 - ss_res / ss_tot, 0.0))

    # ──────────────────────────────────────────────
    # 图解数据
    # ──────────────────────────────────────────────
    @staticmethod
    def _probability_plot_data(failures: np.ndarray,
                               result: WeibullResult) -> Dict[str, List[float]]:
        """Weibull 概率图数据"""
        n = len(failures)
        sorted_f = np.sort(failures)
        ranks = np.arange(1, n + 1)
        Fi = (ranks - 0.3) / (n + 0.4)
        return {
            "rank": ranks.tolist(),
            "prob": (Fi * 100).tolist(),
            "time": sorted_f.tolist(),
        }

    @staticmethod
    def _reliability_curve_data(result: WeibullResult) -> Dict[str, List[float]]:
        """R(t) / h(t) 曲线数据"""
        b10 = result.gamma + result.eta * (-np.log(0.90)) ** (1 / result.beta)
        t_max = max(b10 * 3, result.characteristic_life * 2)
        t = np.linspace(0, t_max, 200)
        z = np.maximum((t - result.gamma) / result.eta, 1e-9)
        R = np.exp(-(z ** result.beta))
        h = (result.beta / result.eta) * (z ** (result.beta - 1))
        return {
            "t": t.tolist(),
            "R": R.tolist(),
            "h": h.tolist(),
        }
