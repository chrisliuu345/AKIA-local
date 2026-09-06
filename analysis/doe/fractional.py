"""
Fractional Factorial Design — 2^(k-p) construction + alias analysis

References:
    Montgomery D C (2017). Design and Analysis of Experiments, 9th ed.
    Box G E P, Hunter W G, Hunter J S (1978). Statistics for Experimenters.

Supports: 1/2, 1/4, 1/8 fractions, Resolution III/IV/V, alias structure
"""
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from config.settings import _MIN_ABERRATION_TABLE


def _base_factorial(k: int) -> np.ndarray:
    """Generate 2^k full factorial design matrix (Yates order)"""
    idx = np.arange(2 ** k)
    return 2 * ((idx[:, np.newaxis] >> np.arange(k)[::-1]) & 1).astype(int) - 1


def _parse_generator(gen_str: str) -> List[int]:
    """Parse generator string like 'ABC' into column indices [0,1,2]"""
    return [ord(c.upper()) - ord('A') for c in gen_str.upper()]


def _apply_generator(base_design: np.ndarray, col_indices: List[int]) -> np.ndarray:
    """Create generator column by element-wise product of base columns"""
    result = np.ones(len(base_design), dtype=int)
    for idx in col_indices:
        result *= base_design[:, idx]
    return result


def _get_generators(k: int, fraction: str,
                    user_generators: Optional[Dict[str, str]] = None
                    ) -> Tuple[List[str], Dict]:
    """Resolve generators from user input or minimum aberration table"""
    fraction_map = {"1/2": 1, "1/4": 2, "1/8": 3}
    if fraction not in fraction_map:
        raise ValueError("fraction must be in " + str(list(fraction_map.keys())) + ", got '" + fraction + "'")
    p = fraction_map[fraction]
    k_basic = k - p

    if k_basic < 1:
        raise ValueError("k-p=" + str(k_basic) + " < 1: too many factors for this fraction")

    if user_generators:
        gens = [user_generators.get("factor_" + str(i), "") for i in range(p)]
        return gens, {}

    key = (k, p)
    if key in _MIN_ABERRATION_TABLE:
        info = _MIN_ABERRATION_TABLE[key]
        return info["generators"], info

    gens = []
    for i in range(p):
        gen_cols = list(range(min(i + 2, k_basic)))
        gen_str = "".join(chr(ord('A') + c) for c in gen_cols)
        gens.append(gen_str)
    return gens, {}


def compute_defining_relation(generators: List[str]) -> List[str]:
    """Compute full defining relation from generator list.

    Returns list of words including generators and all their products.
    """
    if not generators:
        return []

    words = list(generators)

    for i in range(len(generators)):
        for j in range(i + 1, len(generators)):
            set_i = set(generators[i].upper())
            set_j = set(generators[j].upper())
            product = set_i.symmetric_difference(set_j)
            if product:
                words.append("".join(sorted(product)))

    words = sorted(set(words), key=lambda w: (len(w), w))
    return words


def compute_resolution(defining_relation: List[str]) -> int:
    """Compute design resolution from defining relation.

    Resolution = min word length in defining relation (excluding 'I').
    """
    if not defining_relation:
        return 999
    return min(len(w) for w in defining_relation)


def compute_alias_structure(factors: List[str],
                            design_matrix: np.ndarray) -> Dict[str, List[str]]:
    """Compute alias groups from design matrix.

    Two effects are aliased if their column vectors are identical.
    """
    k = len(factors)
    effect_cols = {}

    for i, name in enumerate(factors):
        effect_cols[name] = design_matrix[:, i].tobytes()

    for i in range(k):
        for j in range(i + 1, k):
            name = factors[i] + "*" + factors[j]
            col = design_matrix[:, i] * design_matrix[:, j]
            effect_cols[name] = col.tobytes()

    groups: Dict[bytes, List[str]] = {}
    for effect, col_hash in effect_cols.items():
        groups.setdefault(col_hash, []).append(effect)

    return {k: v for k, v in groups.items() if len(v) > 1}


def generate_design(
    factors: List[str],
    fraction: str = "1/2",
    generators: Optional[Dict[str, str]] = None,
    center_points: int = 0,
    block: bool = False,
    random_seed: Optional[int] = None,
) -> pd.DataFrame:
    """Generate 2^(k-p) fractional factorial design.

    Parameters
    ----------
    factors : list of str
        Factor names (k factors)
    fraction : str
        Fraction size: "1/2", "1/4", or "1/8"
    generators : dict, optional
        Generator mapping {factor_name: generator_expression}
        If None, uses minimum aberration table
    center_points : int
        Number of center points (all zeros)
    block : bool
        Whether to add Block column
    random_seed : int, optional
        Random seed for RunOrder

    Returns
    -------
    pd.DataFrame with factor columns, RunOrder, StdOrder
    """
    k = len(factors)
    if k < 2:
        raise ValueError("At least 2 factors required")
    if k > 15:
        raise ValueError("Maximum 15 factors, got " + str(k))

    gen_strs, info = _get_generators(k, fraction, generators)
    p = len(gen_strs)
    k_basic = k - p

    if k_basic < 1:
        raise ValueError("Design not possible for this fraction")

    base = _base_factorial(k_basic)

    design = np.zeros((2 ** k_basic, k), dtype=int)
    design[:, :k_basic] = base

    for i, gen_str in enumerate(gen_strs):
        col_indices = _parse_generator(gen_str)
        design[:, k_basic + i] = _apply_generator(base, col_indices)

    def_rel = compute_defining_relation(gen_strs)
    resolution = compute_resolution(def_rel)

    data = {factors[i]: design[:, i] for i in range(k)}
    df = pd.DataFrame(data)
    df["StdOrder"] = list(range(1, 2 ** k_basic + 1))

    rng = np.random.default_rng(random_seed)
    perm = rng.permutation(2 ** k_basic)
    inv_perm = np.empty(2 ** k_basic, dtype=int)
    inv_perm[perm] = np.arange(2 ** k_basic) + 1
    df["RunOrder"] = inv_perm

    df["DefiningRelation"] = "I=" + "=".join(def_rel) if def_rel else "I"
    df["Resolution"] = resolution

    if center_points > 0:
        center_df = pd.DataFrame({f: [0] * center_points for f in factors})
        center_df["StdOrder"] = [0] * center_points
        center_df["RunOrder"] = list(range(2 ** k_basic + 1, 2 ** k_basic + 1 + center_points))
        center_df["DefiningRelation"] = ""
        center_df["Resolution"] = 0
        df = pd.concat([df, center_df], ignore_index=True)

    if block:
        df["Block"] = ["Design"] * len(df)

    return df


def analyze(
    df: pd.DataFrame,
    response_col: str,
    factor_cols: List[str],
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Analyze fractional factorial design data.

    Computes main effects, ANOVA, alias structure, Pareto data.
    """
    data = df[[response_col] + factor_cols].dropna()
    for col in [response_col] + factor_cols:
        coerced = pd.to_numeric(data[col], errors="coerce")
        n_nan = coerced.isna().sum()
        if n_nan > 0:
            bad_vals = data[col][coerced.isna()].unique()[:5]
            raise ValueError(
                "列 '" + col + "' 包含非数值数据，无法进行DOE分析。"
                "示例: " + str(list(bad_vals)) + "。请确保选择的响应列和因子列均为数值类型。"
            )
    response = data[response_col].values.astype(float)
    design = data[factor_cols].values.astype(float)
    n = len(response)
    k = len(factor_cols)

    high_mask = design > 0
    low_mask = design < 0
    n_high = high_mask.sum(axis=0)
    n_low = low_mask.sum(axis=0)
    sum_high = (response[:, np.newaxis] * high_mask).sum(axis=0)
    sum_low = (response[:, np.newaxis] * low_mask).sum(axis=0)
    valid = (n_high > 0) & (n_low > 0)
    effects_arr = np.where(valid, sum_high / n_high - sum_low / n_low, 0.0)

    grand_mean = float(np.mean(response))
    ss_total = float(np.sum((response - grand_mean) ** 2))
    df_total = n - 1

    ss_arr = np.where(valid, n * (effects_arr / 2) ** 2, 0.0)
    ss_model = float(np.sum(ss_arr))
    ss_error = max(ss_total - ss_model, 0.0)
    df_model = int(np.sum(valid))
    df_error = max(df_total - df_model, 1)

    ms_arr = ss_arr.copy()
    if df_error > 0 and ss_error > 0:
        f_arr = ms_arr / (ss_error / df_error)
        p_arr = 1.0 - stats.f.cdf(np.maximum(f_arr, 0), 1, df_error)
    elif ss_error == 0 and df_error > 0:
        f_arr = np.full(k, float("inf"))
        p_arr = np.zeros(k)
    else:
        f_arr = np.zeros(k)
        p_arr = np.ones(k)

    effects = {factor_cols[i]: round(float(effects_arr[i]), 6) for i in range(k)}
    ss_effects = {factor_cols[i]: round(float(ss_arr[i]), 6) for i in range(k)}
    f_values = {factor_cols[i]: (round(float(f_arr[i]), 4)
                                 if f_arr[i] != float("inf") else f_arr[i])
                for i in range(k)}
    p_values = {factor_cols[i]: round(float(p_arr[i]), 6) for i in range(k)}
    ms_effects = {factor_cols[i]: round(float(ms_arr[i]), 6) for i in range(k)}

    significant = [f for f in factor_cols if p_values.get(f, 1.0) < alpha]

    pareto_data = sorted(
        [{"factor": f, "effect": abs(effects[f]),
          "f_value": f_values[f], "p_value": p_values[f]}
         for f in factor_cols],
        key=lambda x: x["effect"],
        reverse=True,
    )

    r_squared = 1.0 - (ss_error / ss_total) if ss_total > 0 else 0.0

    alias_groups = compute_alias_structure(factor_cols, design)

    return {
        "chart_type": "Fractional Factorial Design",
        "factors": factor_cols,
        "observations": n,
        "grand_mean": round(grand_mean, 6),
        "effects": effects,
        "anova": {
            "source": factor_cols + ["Error", "Total"],
            "ss": [ss_effects[f] for f in factor_cols] + [round(ss_error, 6), round(ss_total, 6)],
            "df": [1] * k + [df_error, df_total],
            "ms": [ms_effects[f] for f in factor_cols] + [round(ss_error / df_error, 6) if df_error > 0 else 0, 0],
            "f_value": [f_values[f] for f in factor_cols] + [None, None],
            "p_value": [p_values[f] for f in factor_cols] + [None, None],
        },
        "significant_factors": significant,
        "pareto_data": pareto_data,
        "alias_groups": alias_groups,
        "model_r_squared": round(r_squared, 6),
    }
