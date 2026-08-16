"""ALT 加速寿命试验 — Arrhenius / 逆幂律模型"""

import numpy as np
from typing import Dict, Any
from scipy import stats as sp_stats
from scipy.optimize import curve_fit


class ALTEngine:
    """加速寿命试验分析: Arrhenius (温度) + 逆幂律 (电压/压力)"""

    @staticmethod
    def arrhenius_life(stress_temp: np.ndarray, life: np.ndarray,
                       use_temp: float, activation_energy: float = 0.7) -> Dict[str, Any]:
        """Arrhenius 模型: L(T) = A * exp(Ea/(k*T))
        参数:
            stress_temp: 加速应力温度 (K)
            life: 对应寿命 (任意单位)
            use_temp: 使用温度 (Celsius), 自动转换为 K
            activation_energy: 激活能 (eV), 默认 0.7
        返回: AF, 外推寿命, 拟合参数, R²
        """
        T_use = use_temp + 273.15
        k = 8.617333262145e-5  # Boltzmann (eV/K)

        # 拟合: ln(L) = ln(A) + Ea/(k*T)
        x = 1.0 / (k * stress_temp)
        y = np.log(life)

        # 最小二乘法
        slope, intercept, r, p, std_err = sp_stats.linregress(x, y)
        Ea_fitted = slope
        A_fitted = np.exp(intercept)

        # 加速因子
        af = np.exp(Ea_fitted / k * (1.0 / T_use - 1.0 / np.mean(stress_temp)))
        life_pred = A_fitted * np.exp(Ea_fitted / (k * T_use))

        # 置信区间
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
        # 拟合: ln(L) = ln(C) - n*ln(V)
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
