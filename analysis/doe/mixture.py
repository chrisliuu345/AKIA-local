"""
Mixture Design — simplex lattice · simplex centroid · extreme vertices · Scheffé regression

References:
    Scheffé H (1958). Experiments with Mixtures. J Roy Stat Soc B, 20(2), 344-360.
    Scheffé H (1963). The Simplex-Centroid Design. Technometrics, 5(4), 455-471.
    McLean R A, Anderson V L (1966). Extreme Vertices Design. Technometrics, 8(3), 447-454.
    Cornell J A (2002). Experiments with Mixtures, 3rd ed. Wiley.

Supports: {q,m} simplex lattice, simplex centroid, extreme vertices,
          Scheffé linear/quadratic/special-cubic models
"""
from typing import Dict, Any, List
import itertools
import numpy as np
import pandas as pd
from scipy import stats
from config.settings import MIXTURE_MODELS, MIXTURE_MAX_COMPONENTS


def simplex_lattice(
    components: List[str],
    degree: int = 2,
) -> pd.DataFrame:
    """Generate {q, m} simplex lattice design.

    Parameters
    ----------
    components : list of str
        Component names (q components)
    degree : int
        Lattice degree m (each component takes values in {0, 1/m, ..., 1})

    Returns
    -------
    pd.DataFrame with component columns (proportions summing to 1) + RunOrder
    """
    q = len(components)
    if q < 2:
        raise ValueError("At least 2 components required")
    if q > MIXTURE_MAX_COMPONENTS:
        raise ValueError("Maximum " + str(MIXTURE_MAX_COMPONENTS) + " components, got " + str(q))
    if degree < 1:
        raise ValueError("Degree must be >= 1")

    levels = np.arange(0, degree + 1) / degree
    points = []
    for combo in itertools.product(levels, repeat=q):
        if abs(sum(combo) - 1.0) < 1e-10:
            points.append(combo)

    design = np.array(points)
    n = len(design)

    data = {components[i]: design[:, i] for i in range(q)}
    df = pd.DataFrame(data)
    df["RunOrder"] = range(1, n + 1)
    df["DesignType"] = "Simplex Lattice {" + str(q) + "," + str(degree) + "}"
    return df


def simplex_centroid(
    components: List[str],
) -> pd.DataFrame:
    """Generate simplex-centroid design (2^q - 1 runs).

    Parameters
    ----------
    components : list of str
        Component names (q components)

    Returns
    -------
    pd.DataFrame with component columns + SubsetSize + RunOrder
    """
    q = len(components)
    if q < 2:
        raise ValueError("At least 2 components required")
    if q > MIXTURE_MAX_COMPONENTS:
        raise ValueError("Maximum " + str(MIXTURE_MAX_COMPONENTS) + " components, got " + str(q))

    points = []
    subset_sizes = []
    for r in range(1, q + 1):
        for combo in itertools.combinations(range(q), r):
            point = [0.0] * q
            for idx in combo:
                point[idx] = 1.0 / r
            points.append(point)
            subset_sizes.append(r)

    design = np.array(points)
    n = len(design)

    data = {components[i]: design[:, i] for i in range(q)}
    df = pd.DataFrame(data)
    df["SubsetSize"] = subset_sizes
    df["RunOrder"] = range(1, n + 1)
    df["DesignType"] = "Simplex Centroid"
    return df


def extreme_vertices(
    components: List[str],
    lower_bounds: List[float],
    upper_bounds: List[float],
) -> pd.DataFrame:
    """Generate extreme vertices design (McLean-Anderson algorithm).

    Parameters
    ----------
    components : list of str
        Component names (q components)
    lower_bounds : list of float
        Lower bounds for each component (L_i)
    upper_bounds : list of float
        Upper bounds for each component (U_i)

    Returns
    -------
    pd.DataFrame with constrained component proportions + RunOrder
    """
    q = len(components)
    if q < 2:
        raise ValueError("At least 2 components required")
    if len(lower_bounds) != q or len(upper_bounds) != q:
        raise ValueError("Bounds length must equal number of components")
    if any(lo > hi for lo, hi in zip(lower_bounds, upper_bounds)):
        raise ValueError("Lower bounds must be <= upper bounds")
    if sum(lower_bounds) > 1.0 + 1e-10:
        raise ValueError("Sum of lower bounds must be <= 1")
    if sum(upper_bounds) < 1.0 - 1e-10:
        raise ValueError("Sum of upper bounds must be >= 1")

    vertices = set()
    for free_idx in range(q):
        other_indices = [i for i in range(q) if i != free_idx]
        for combo in itertools.product([0, 1], repeat=q - 1):
            fixed = {}
            for k, idx in enumerate(other_indices):
                fixed[idx] = lower_bounds[idx] if combo[k] == 0 else upper_bounds[idx]
            x_free = 1.0 - sum(fixed.values())
            if lower_bounds[free_idx] - 1e-10 <= x_free <= upper_bounds[free_idx] + 1e-10:
                x_free = max(lower_bounds[free_idx], min(upper_bounds[free_idx], x_free))
                point = [0.0] * q
                for idx, val in fixed.items():
                    point[idx] = val
                point[free_idx] = x_free
                vertices.add(tuple(round(v, 10) for v in point))

    if not vertices:
        raise ValueError("No feasible vertices found for the given bounds")

    centroid = tuple(round(np.mean([v[i] for v in vertices]), 10) for i in range(q))
    if sum(centroid) <= 1.0 + 1e-10:
        vertices.add(centroid)

    vertex_list = sorted(vertices)
    n_verts = len(vertex_list)
    for i in range(n_verts):
        for j in range(i + 1, n_verts):
            mid = tuple(round((vertex_list[i][k] + vertex_list[j][k]) / 2, 10) for k in range(q))
            if all(lower_bounds[k] - 1e-10 <= mid[k] <= upper_bounds[k] + 1e-10 for k in range(q)):
                if abs(sum(mid) - 1.0) < 1e-10:
                    vertices.add(mid)

    vertex_list = sorted(vertices)
    design = np.array(vertex_list)
    n = len(design)

    data = {components[i]: design[:, i] for i in range(q)}
    df = pd.DataFrame(data)
    df["RunOrder"] = range(1, n + 1)
    df["DesignType"] = "Extreme Vertices"
    return df


def _build_scheffe_matrix(X: np.ndarray, model: str) -> np.ndarray:
    """Build Scheffé design matrix (no intercept).

    Parameters
    ----------
    X : ndarray of shape (n, q)
        Mixture proportions
    model : str
        "linear", "quadratic", or "special_cubic"

    Returns
    -------
    ndarray of shape (n, p) where p = number of model terms
    """
    q = X.shape[1]
    cols = [X]

    if model in ("quadratic", "special_cubic"):
        for i in range(q):
            for j in range(i + 1, q):
                cols.append((X[:, i] * X[:, j]).reshape(-1, 1))

    if model == "special_cubic":
        for i in range(q):
            for j in range(i + 1, q):
                for k in range(j + 1, q):
                    cols.append((X[:, i] * X[:, j] * X[:, k]).reshape(-1, 1))

    return np.hstack(cols)


def _model_term_names(components: List[str], model: str) -> List[str]:
    """Generate term names for Scheffé model."""
    q = len(components)
    names = list(components)

    if model in ("quadratic", "special_cubic"):
        for i in range(q):
            for j in range(i + 1, q):
                names.append(components[i] + "*" + components[j])

    if model == "special_cubic":
        for i in range(q):
            for j in range(i + 1, q):
                for k in range(j + 1, q):
                    names.append(components[i] + "*" + components[j] + "*" + components[k])

    return names


def analyze(
    df: pd.DataFrame,
    response_col: str,
    component_cols: List[str],
    model: str = "quadratic",
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Analyze mixture design data using Scheffé polynomial regression.

    Parameters
    ----------
    df : pd.DataFrame
        Design matrix with component proportion columns and response column
    response_col : str
        Column name for response data
    component_cols : list of str
        Component column names (proportions)
    model : str
        Scheffé model type: "linear", "quadratic", or "special_cubic"
    alpha : float
        Significance level for ANOVA

    Returns
    -------
    dict with coefficients, R², ANOVA, significant terms
    """
    if model not in MIXTURE_MODELS:
        raise ValueError("Model must be one of " + str(MIXTURE_MODELS))

    q = len(component_cols)
    if q < 2:
        raise ValueError("At least 2 components required")

    if model == "special_cubic" and q < 3:
        raise ValueError("Special cubic model requires at least 3 components")

    data = df[component_cols + [response_col]].dropna()
    for col in component_cols + [response_col]:
        coerced = pd.to_numeric(data[col], errors="coerce")
        n_nan = coerced.isna().sum()
        if n_nan > 0:
            bad_vals = data[col][coerced.isna()].unique()[:5]
            raise ValueError(
                "列 '" + col + "' 包含非数值数据，无法进行混合设计分析。"
                "示例: " + str(list(bad_vals)) + "。请确保所有列均为数值类型。"
            )

    X_raw = data[component_cols].values.astype(float)
    y = data[response_col].values.astype(float)
    n = len(y)

    X_scheffe = _build_scheffe_matrix(X_raw, model)
    p = X_scheffe.shape[1]

    if n < p:
        raise ValueError("Insufficient observations: " + str(n) + " < " + str(p) + " parameters")

    coeffs, residuals, rank, sv = np.linalg.lstsq(X_scheffe, y, rcond=None)
    y_pred = X_scheffe @ coeffs
    residuals_arr = y - y_pred

    ss_res = float(np.sum(residuals_arr ** 2))
    ss_total = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_total if ss_total > 0 else 0.0

    r_squared_adj = 1.0 - (1.0 - r_squared) * (n - 1) / (n - p) if n > p else r_squared

    term_names = _model_term_names(component_cols, model)
    coefficients = dict(zip(term_names, [round(float(c), 6) for c in coeffs]))

    ss_model = ss_total - ss_res
    df_model = p
    df_error = max(n - p, 1)
    ms_model = ss_model / df_model if df_model > 0 else 0.0
    ms_error = ss_res / df_error if df_error > 0 else 1e-10

    f_model = ms_model / ms_error if ms_error > 1e-10 else 0.0

    if df_error > 0 and ms_error > 0:
        try:
            se = np.sqrt(np.diag(np.linalg.inv(X_scheffe.T @ X_scheffe)) * ms_error)
        except np.linalg.LinAlgError:
            se = np.sqrt(np.diag(np.linalg.pinv(X_scheffe.T @ X_scheffe)) * ms_error)
        t_vals = coeffs / se
        p_vals = 2.0 * (1.0 - stats.t.cdf(np.abs(t_vals), df_error))
    else:
        t_vals = np.zeros(p)
        p_vals = np.ones(p)

    significant_terms = [term_names[i] for i in range(p) if p_vals[i] < alpha]

    term_ss = []
    term_df = []
    term_f = []
    term_p = []
    for i in range(p):
        c_i = float(coeffs[i])
        ss_i = c_i * c_i * float(np.sum(X_scheffe[:, i] ** 2))
        df_i = 1
        ms_i = ss_i / df_i
        f_i = ms_i / ms_error if ms_error > 1e-10 else 0.0
        p_i = 1.0 - stats.f.cdf(max(f_i, 0), 1, df_error) if df_error > 0 else 1.0
        term_ss.append(round(ss_i, 6))
        term_df.append(df_i)
        term_f.append(round(f_i, 4))
        term_p.append(round(p_i, 6))

    return {
        "chart_type": "Mixture Design Analysis",
        "components": component_cols,
        "model": model,
        "observations": n,
        "coefficients": coefficients,
        "r_squared": round(r_squared, 6),
        "r_squared_adjusted": round(r_squared_adj, 6),
        "residual_std": round(float(np.std(residuals_arr, ddof=1)), 6) if n > 1 else 0.0,
        "num_parameters": p,
        "anova": {
            "source": term_names + ["Residual", "Total"],
            "ss": term_ss + [round(ss_res, 6), round(ss_total, 6)],
            "df": term_df + [df_error, n - 1],
            "f_value": term_f + [None, None],
            "p_value": term_p + [None, None],
        },
        "significant_terms": significant_terms,
        "design_points": n,
    }
