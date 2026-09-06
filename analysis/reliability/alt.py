"""ALT 加速寿命试验 — Arrhenius / 逆幂律 / Eyring / 试验规划

模型:
  Arrhenius      — 温度应力 (热老化)
  Inverse Power  — 电压/压力/载荷应力
  Eyring         — 通用温度应力 (更精确的 Arrhenius 扩展)
"""

import math
import numpy as np
from typing import Dict, Any, List
from scipy import stats as sp_stats


class ALTEngine:
    """加速寿命试验分析: Arrhenius (温度) + 逆幂律 (电压/压力)"""

    @staticmethod
    def arrhenius_life(stress_temp: np.ndarray, life: np.ndarray,
                       use_temp: float, activation_energy: float = 0.7) -> Dict[str, Any]:
        """Arrhenius 模型: L(T) = A * exp(Ea/(k*T))
        参数:
            stress_temp: 加速应力温度 (K, 已转换)
            life: 对应寿命 (任意单位)
            use_temp: 使用温度 (Celsius), 自动转换为 K
            activation_energy: 激活能 (eV), 默认 0.7 (保留参数, 实际由回归拟合)
        返回: AF, 外推寿命, 拟合参数, R²
        """
        if len(stress_temp) < 3 or len(life) < 3:
            return {"analysis_type": "reliability.alt.arrhenius", "error": f"样本量不足（需要至少3个数据点，当前stress={len(stress_temp)}, life={len(life)}）"}
        if np.any(stress_temp <= 0):
            return {"analysis_type": "reliability.alt.arrhenius", "error": "stress_temp必须全部为正数（开尔文温度）"}
        if np.any(life <= 0):
            return {"analysis_type": "reliability.alt.arrhenius", "error": "life必须全部为正数"}

        if np.any(stress_temp < 200):
            import warnings
            warnings.warn("stress_temp值较小(<200)，请确认是否已转换为开尔文温度(K)。"
                         "如果传入的是摄氏度，请先转换：T_K = T_C + 273.15", UserWarning)

        T_use = use_temp + 273.15
        k = 8.617333262145e-5

        x = 1.0 / (k * stress_temp)
        y = np.log(life)

        slope, intercept, r, p, std_err = sp_stats.linregress(x, y)
        Ea_fitted = slope
        A_fitted = np.exp(intercept)

        af = np.exp(Ea_fitted / k * (1.0 / T_use - 1.0 / np.mean(stress_temp)))
        life_pred = A_fitted * np.exp(Ea_fitted / (k * T_use))

        y_pred = slope * x + intercept
        residuals = y - y_pred
        se = np.sqrt(np.sum(residuals ** 2) / (len(x) - 2))
        life_low = np.exp(np.log(life_pred) - 1.96 * se)
        life_high = np.exp(np.log(life_pred) + 1.96 * se)

        return {
            "model": "Arrhenius",
            "activation_energy_eV": round(Ea_fitted, 4),
            "A_factor": round(A_fitted, 2),
            "r_squared": round(r ** 2, 4),
            "acceleration_factor": round(af, 2),
            "life_at_use": round(life_pred, 2),
            "life_95ci_low": round(life_low, 2),
            "life_95ci_high": round(life_high, 2),
            "use_temperature_K": round(T_use, 2),
        }

    @staticmethod
    def inverse_power_law(stress: np.ndarray, life: np.ndarray,
                          use_stress: float) -> Dict[str, Any]:
        """逆幂律模型: L(V) = C * V^(-n)
        适用于电压/压力/载荷等非热应力
        参数:
            stress: 加速应力水平
            life: 对应寿命
            use_stress: 正常使用应力
        """
        if len(stress) < 3 or len(life) < 3:
            return {"analysis_type": "reliability.alt.inverse_power_law", "error": "样本量不足（需要至少3个数据点）"}
        if np.any(stress <= 0):
            return {"analysis_type": "reliability.alt.inverse_power_law", "error": "stress必须全部为正数"}
        if np.any(life <= 0):
            return {"analysis_type": "reliability.alt.inverse_power_law", "error": "life必须全部为正数"}
        if use_stress <= 0:
            return {"analysis_type": "reliability.alt.inverse_power_law", "error": "use_stress必须为正数"}

        x = np.log(stress)
        y = np.log(life)

        slope, intercept, r, p, std_err = sp_stats.linregress(x, y)
        n_fitted = -slope
        C_fitted = np.exp(intercept)

        af = (np.mean(stress) / use_stress) ** n_fitted
        life_pred = C_fitted * (use_stress ** (-n_fitted))

        y_pred = -n_fitted * x + np.log(C_fitted)
        se = np.sqrt(np.sum((y - y_pred) ** 2) / (len(x) - 2))
        life_low = np.exp(np.log(life_pred) - 1.96 * se)
        life_high = np.exp(np.log(life_pred) + 1.96 * se)

        return {
            "model": "Inverse Power Law",
            "n_exponent": round(n_fitted, 4),
            "C_factor": round(C_fitted, 2),
            "r_squared": round(r ** 2, 4),
            "acceleration_factor": round(af, 2),
            "life_at_use": round(life_pred, 2),
            "life_95ci_low": round(life_low, 2),
            "life_95ci_high": round(life_high, 2),
            "use_stress": use_stress,
        }

    @staticmethod
    def eyring(stress_temp: np.ndarray, life: np.ndarray,
               use_temp: float) -> Dict[str, Any]:
        """Eyring 模型: L(T) = (A/T) * exp(B/T)
        比 Arrhenius 更精确的热应力模型
        参数:
            stress_temp: 加速应力温度 (K)
            life: 对应寿命
            use_temp: 使用温度 (Celsius)
        """
        if len(stress_temp) < 3 or len(life) < 3:
            return {"analysis_type": "reliability.alt.eyring", "error": "样本量不足（需要至少3个数据点）"}
        if np.any(stress_temp <= 0):
            return {"analysis_type": "reliability.alt.eyring", "error": "stress_temp必须全部为正数（开尔文温度）"}
        if np.any(life <= 0):
            return {"analysis_type": "reliability.alt.eyring", "error": "life必须全部为正数"}
        if use_temp <= -273.15:
            return {"analysis_type": "reliability.alt.eyring", "error": "use_temp必须高于绝对零度"}

        T_use = use_temp + 273.15

        x = 1.0 / stress_temp
        y = np.log(life * stress_temp)

        slope, intercept, r, p, std_err = sp_stats.linregress(x, y)
        B_fitted = slope
        A_fitted = np.exp(intercept)

        life_pred = (A_fitted / T_use) * math.exp(B_fitted / T_use)

        life_stress = (A_fitted / np.mean(stress_temp)) * math.exp(B_fitted / np.mean(stress_temp))
        af = life_pred / life_stress if life_stress > 0 else float("inf")

        y_pred = slope * x + intercept
        residuals = y - y_pred
        se = np.sqrt(np.sum(residuals ** 2) / (len(x) - 2))
        life_low = math.exp(math.log(life_pred) - 1.96 * se)
        life_high = math.exp(math.log(life_pred) + 1.96 * se)

        return {
            "model": "Eyring",
            "A_factor": round(A_fitted, 4),
            "B_parameter": round(B_fitted, 2),
            "r_squared": round(r ** 2, 4),
            "acceleration_factor": round(af, 2),
            "life_at_use": round(life_pred, 2),
            "life_95ci_low": round(life_low, 2),
            "life_95ci_high": round(life_high, 2),
            "use_temperature_K": round(T_use, 2),
        }


def alt_trial_plan(
    model: str,
    stress_levels: List[float],
    use_condition: float,
    target_life: float,
    n_per_level: int = 10,
    total_sample: int = 60,
    confidence_level: float = 0.90,
) -> Dict[str, Any]:
    """
    ALT 试验规划

    根据加速模型和目标，规划试验应力水平和样本量分配。

    Args:
        model: "arrhenius" | "eyring" | "inverse_power"
        stress_levels: 计划的加速应力水平列表
        use_condition: 正常使用条件 (温度K 或 应力值)
        target_life: 目标外推寿命
        n_per_level: 每个应力水平的样本量
        total_sample: 总样本量
        confidence_level: 置信水平

    Returns:
        试验规划结果
    """
    if len(stress_levels) < 2:
        return {"analysis_type": "reliability.alt.trial_plan", "error": "至少需要2个应力水平"}
    if n_per_level < 3:
        return {"analysis_type": "reliability.alt.trial_plan", "error": "每个应力水平至少3个样本"}
    if any(s <= 0 for s in stress_levels):
        return {"analysis_type": "reliability.alt.trial_plan", "error": "应力水平必须全部为正"}
    if use_condition <= 0:
        return {"analysis_type": "reliability.alt.trial_plan", "error": "use_condition必须为正"}

    n_levels = len(stress_levels)
    allocated = min(n_per_level, total_sample // n_levels)
    actual_total = allocated * n_levels

    if model == "arrhenius":
        k = 8.617333262145e-5
        avg_af = np.mean([math.exp(0.7 / k * (1.0 / s - 1.0 / use_condition)) for s in stress_levels])
        estimated_test_time = target_life / avg_af
    elif model == "inverse_power":
        avg_af = np.mean([(use_condition / s) ** 2 for s in stress_levels])
        estimated_test_time = target_life / avg_af
    else:
        estimated_test_time = None

    z = sp_stats.norm.ppf((1 + confidence_level) / 2)

    return {
        "model": model,
        "n_stress_levels": n_levels,
        "stress_levels": stress_levels,
        "use_condition": use_condition,
        "n_per_level": allocated,
        "total_sample_size": actual_total,
        "target_life": target_life,
        "estimated_test_time": round(estimated_test_time, 2) if estimated_test_time else None,
        "confidence_level": confidence_level,
        "z_value": round(float(z), 4),
    }
