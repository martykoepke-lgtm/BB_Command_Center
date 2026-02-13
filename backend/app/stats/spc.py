"""
Statistical Process Control (SPC) — control charts for monitoring process stability.

Charts:
  - i_mr_chart: Individual measurements and Moving Range
  - xbar_r_chart: Subgroup means (X-bar) and Ranges (R)
  - p_chart: Proportion defective
  - np_chart: Count defective (constant sample size)
  - c_chart: Count defects per unit (constant opportunity)
  - u_chart: Defects per unit (variable sample size)
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

from app.stats import AnalysisResult, PlotlyChart
from app.stats import charts as chart_module


def _detect_violations(values: Sequence[float], cl: float, ucl: float, lcl: float) -> list[int]:
    """
    Detect Western Electric / Nelson rules violations.
    Returns indices of out-of-control points (Rule 1: beyond 3-sigma).
    """
    violations = []
    for i, v in enumerate(values):
        if v > ucl or v < lcl:
            violations.append(i)
    return violations


# ---------------------------------------------------------------------------
# I-MR Chart (Individuals and Moving Range)
# ---------------------------------------------------------------------------

def i_mr_chart(df: "pd.DataFrame", config: dict) -> AnalysisResult:
    """
    Config:
        column: str          — measurement column
        labels_column: str   — optional column for point labels (e.g., date or sample ID)
    """
    import pandas as pd

    column = config.get("column")
    labels_col = config.get("labels_column")

    if not column or column not in df.columns:
        return AnalysisResult(test_type="i_mr_chart", test_category="spc", success=False,
                              summary={}, details={"error": f"Column '{column}' not found"})

    series = df[column].dropna().astype(float)
    values = series.values
    n = len(values)

    if n < 2:
        return AnalysisResult(test_type="i_mr_chart", test_category="spc", success=False,
                              summary={}, details={"error": "Need at least 2 observations"})

    labels = None
    if labels_col and labels_col in df.columns:
        labels = df.loc[series.index, labels_col].astype(str).tolist()

    # Moving ranges
    mr = np.abs(np.diff(values))
    mr_mean = float(np.mean(mr))

    # Constants for n=2 (individual chart)
    d2 = 1.128  # for subgroup size 2
    d3 = 0.853
    d4 = 3.267

    # I-chart limits
    x_bar = float(np.mean(values))
    sigma_est = mr_mean / d2
    i_ucl = x_bar + 3 * sigma_est
    i_lcl = x_bar - 3 * sigma_est

    # MR-chart limits
    mr_ucl = d4 * mr_mean
    mr_lcl = 0.0  # MR chart LCL is always 0

    # Detect violations
    i_violations = _detect_violations(values.tolist(), x_bar, i_ucl, i_lcl)
    mr_violations = _detect_violations(mr.tolist(), mr_mean, mr_ucl, mr_lcl)

    warnings: list[str] = []
    if i_violations:
        warnings.append(f"{len(i_violations)} point(s) out of control on Individuals chart")
    if mr_violations:
        warnings.append(f"{len(mr_violations)} point(s) out of control on Moving Range chart")

    chart_list = [
        chart_module.control_chart(
            values=values.tolist(),
            center_line=x_bar,
            ucl=i_ucl,
            lcl=i_lcl,
            title=f"I Chart — {column}",
            yaxis_title=column,
            point_labels=labels,
            violations=i_violations,
        ),
        chart_module.control_chart(
            values=mr.tolist(),
            center_line=mr_mean,
            ucl=mr_ucl,
            lcl=mr_lcl,
            title=f"MR Chart — {column}",
            yaxis_title="Moving Range",
            point_labels=labels[1:] if labels else None,
            violations=mr_violations,
        ),
    ]

    summary = {
        "x_bar": x_bar,
        "mr_bar": mr_mean,
        "sigma_estimate": sigma_est,
        "i_ucl": i_ucl,
        "i_lcl": i_lcl,
        "mr_ucl": mr_ucl,
        "n": n,
        "i_violations": len(i_violations),
        "mr_violations": len(mr_violations),
        "in_control": len(i_violations) == 0 and len(mr_violations) == 0,
    }

    return AnalysisResult(
        test_type="i_mr_chart",
        test_category="spc",
        success=True,
        summary=summary,
        details={
            "column": column, "values": values.tolist(),
            "moving_ranges": mr.tolist(),
            "i_violation_indices": i_violations,
            "mr_violation_indices": mr_violations,
        },
        charts=chart_list,
        interpretation_context={
            "test_name": "I-MR Control Chart",
            "column": column,
            "process_mean": x_bar,
            "estimated_sigma": sigma_est,
            "in_control": summary["in_control"],
            "total_violations": len(i_violations) + len(mr_violations),
            "recommendation": (
                "Process is in statistical control. Variation is from common causes only."
                if summary["in_control"] else
                f"Process has special cause variation. {len(i_violations)} point(s) beyond control limits on I chart. "
                "Investigate root causes for these out-of-control signals."
            ),
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# X-bar/R Chart (Subgroup Means and Ranges)
# ---------------------------------------------------------------------------

# X-bar/R constants by subgroup size
_XBAR_R_CONSTANTS = {
    2:  {"A2": 1.880, "D3": 0, "D4": 3.267, "d2": 1.128},
    3:  {"A2": 1.023, "D3": 0, "D4": 2.574, "d2": 1.693},
    4:  {"A2": 0.729, "D3": 0, "D4": 2.282, "d2": 2.059},
    5:  {"A2": 0.577, "D3": 0, "D4": 2.114, "d2": 2.326},
    6:  {"A2": 0.483, "D3": 0, "D4": 2.004, "d2": 2.534},
    7:  {"A2": 0.419, "D3": 0.076, "D4": 1.924, "d2": 2.704},
    8:  {"A2": 0.373, "D3": 0.136, "D4": 1.864, "d2": 2.847},
    9:  {"A2": 0.337, "D3": 0.184, "D4": 1.816, "d2": 2.970},
    10: {"A2": 0.308, "D3": 0.223, "D4": 1.777, "d2": 3.078},
}


def xbar_r_chart(df: "pd.DataFrame", config: dict) -> AnalysisResult:
    """
    Config:
        columns: list[str]    — measurement columns forming each subgroup
                                 OR
        column: str            — single column with measurements
        subgroup_size: int     — subgroup size (if single column, groups sequentially)
        labels_column: str     — optional point labels
    """
    import pandas as pd

    columns = config.get("columns")
    column = config.get("column")
    subgroup_size = config.get("subgroup_size")
    labels_col = config.get("labels_column")

    warnings: list[str] = []

    # Build subgroups
    if columns and len(columns) >= 2:
        subgroup_cols = [c for c in columns if c in df.columns]
        if len(subgroup_cols) < 2:
            return AnalysisResult(test_type="xbar_r_chart", test_category="spc", success=False,
                                  summary={}, details={"error": "Need at least 2 measurement columns"})
        subgroups = df[subgroup_cols].dropna().values.astype(float)
        subgroup_size = subgroups.shape[1]
    elif column and column in df.columns:
        if not subgroup_size or subgroup_size < 2:
            return AnalysisResult(test_type="xbar_r_chart", test_category="spc", success=False,
                                  summary={}, details={"error": "subgroup_size must be >= 2"})
        series = df[column].dropna().astype(float).values
        n_complete = len(series) // subgroup_size * subgroup_size
        if n_complete < subgroup_size * 2:
            return AnalysisResult(test_type="xbar_r_chart", test_category="spc", success=False,
                                  summary={}, details={"error": "Need at least 2 complete subgroups"})
        subgroups = series[:n_complete].reshape(-1, subgroup_size)
    else:
        return AnalysisResult(test_type="xbar_r_chart", test_category="spc", success=False,
                              summary={}, details={"error": "Provide either 'columns' or 'column' + 'subgroup_size'"})

    if subgroup_size not in _XBAR_R_CONSTANTS:
        return AnalysisResult(test_type="xbar_r_chart", test_category="spc", success=False,
                              summary={}, details={"error": f"Subgroup size {subgroup_size} not supported (2-10)"})

    constants = _XBAR_R_CONSTANTS[subgroup_size]
    k = len(subgroups)  # number of subgroups

    # Subgroup means and ranges
    xbar = np.mean(subgroups, axis=1)
    r = np.ptp(subgroups, axis=1)  # max - min per subgroup

    xbar_bar = float(np.mean(xbar))
    r_bar = float(np.mean(r))

    # Control limits
    xbar_ucl = xbar_bar + constants["A2"] * r_bar
    xbar_lcl = xbar_bar - constants["A2"] * r_bar
    r_ucl = constants["D4"] * r_bar
    r_lcl = constants["D3"] * r_bar

    sigma_est = r_bar / constants["d2"]

    labels = None
    if labels_col and labels_col in df.columns:
        labels = df[labels_col].dropna().astype(str).tolist()[:k]

    xbar_violations = _detect_violations(xbar.tolist(), xbar_bar, xbar_ucl, xbar_lcl)
    r_violations = _detect_violations(r.tolist(), r_bar, r_ucl, r_lcl)

    if xbar_violations:
        warnings.append(f"{len(xbar_violations)} subgroup(s) out of control on X-bar chart")
    if r_violations:
        warnings.append(f"{len(r_violations)} subgroup(s) out of control on R chart")

    chart_list = [
        chart_module.control_chart(
            values=xbar.tolist(), center_line=xbar_bar, ucl=xbar_ucl, lcl=xbar_lcl,
            title=f"X-bar Chart (n={subgroup_size})", yaxis_title="Subgroup Mean",
            point_labels=labels, violations=xbar_violations,
        ),
        chart_module.control_chart(
            values=r.tolist(), center_line=r_bar, ucl=r_ucl, lcl=r_lcl,
            title=f"R Chart (n={subgroup_size})", yaxis_title="Subgroup Range",
            point_labels=labels, violations=r_violations,
        ),
    ]

    summary = {
        "xbar_bar": xbar_bar,
        "r_bar": r_bar,
        "sigma_estimate": sigma_est,
        "xbar_ucl": xbar_ucl,
        "xbar_lcl": xbar_lcl,
        "r_ucl": r_ucl,
        "r_lcl": r_lcl,
        "subgroup_size": subgroup_size,
        "num_subgroups": k,
        "xbar_violations": len(xbar_violations),
        "r_violations": len(r_violations),
        "in_control": len(xbar_violations) == 0 and len(r_violations) == 0,
    }

    return AnalysisResult(
        test_type="xbar_r_chart",
        test_category="spc",
        success=True,
        summary=summary,
        details={
            "subgroup_means": xbar.tolist(),
            "subgroup_ranges": r.tolist(),
            "constants_used": constants,
            "xbar_violation_indices": xbar_violations,
            "r_violation_indices": r_violations,
        },
        charts=chart_list,
        interpretation_context={
            "test_name": "X-bar/R Control Chart",
            "process_mean": xbar_bar,
            "estimated_sigma": sigma_est,
            "subgroup_size": subgroup_size,
            "num_subgroups": k,
            "in_control": summary["in_control"],
            "total_violations": len(xbar_violations) + len(r_violations),
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# P Chart (Proportion Defective)
# ---------------------------------------------------------------------------

def p_chart(df: "pd.DataFrame", config: dict) -> AnalysisResult:
    """
    Config:
        defects_column: str      — column with number of defectives per sample
        sample_size_column: str  — column with sample sizes
        OR
        defects_column: str      — column with defectives
        sample_size: int         — constant sample size
    """
    import pandas as pd

    defects_col = config.get("defects_column")
    size_col = config.get("sample_size_column")
    const_size = config.get("sample_size")

    if not defects_col or defects_col not in df.columns:
        return AnalysisResult(test_type="p_chart", test_category="spc", success=False,
                              summary={}, details={"error": f"Column '{defects_col}' not found"})

    defects = df[defects_col].dropna().astype(float).values
    n = len(defects)

    if size_col and size_col in df.columns:
        sizes = df[size_col].dropna().astype(float).values[:n]
    elif const_size:
        sizes = np.full(n, const_size, dtype=float)
    else:
        return AnalysisResult(test_type="p_chart", test_category="spc", success=False,
                              summary={}, details={"error": "Provide sample_size_column or sample_size"})

    if n < 2:
        return AnalysisResult(test_type="p_chart", test_category="spc", success=False,
                              summary={}, details={"error": "Need at least 2 samples"})

    proportions = defects / sizes
    p_bar = float(np.sum(defects) / np.sum(sizes))

    # Variable control limits (per sample)
    ucl_arr = p_bar + 3 * np.sqrt(p_bar * (1 - p_bar) / sizes)
    lcl_arr = np.maximum(0, p_bar - 3 * np.sqrt(p_bar * (1 - p_bar) / sizes))

    # For charting, use average limits
    avg_size = float(np.mean(sizes))
    ucl = p_bar + 3 * np.sqrt(p_bar * (1 - p_bar) / avg_size)
    lcl = max(0, p_bar - 3 * np.sqrt(p_bar * (1 - p_bar) / avg_size))

    violations = [i for i in range(n) if proportions[i] > ucl_arr[i] or proportions[i] < lcl_arr[i]]
    warnings: list[str] = []
    if violations:
        warnings.append(f"{len(violations)} sample(s) out of control")

    chart_list = [
        chart_module.control_chart(
            values=proportions.tolist(), center_line=p_bar, ucl=ucl, lcl=lcl,
            title="P Chart — Proportion Defective", yaxis_title="Proportion",
            violations=violations,
        ),
    ]

    summary = {
        "p_bar": p_bar,
        "ucl": ucl,
        "lcl": lcl,
        "num_samples": n,
        "avg_sample_size": avg_size,
        "violations": len(violations),
        "in_control": len(violations) == 0,
    }

    return AnalysisResult(
        test_type="p_chart", test_category="spc", success=True,
        summary=summary,
        details={"proportions": proportions.tolist(), "violation_indices": violations},
        charts=chart_list,
        interpretation_context={
            "test_name": "P Chart (Proportion Defective)",
            "p_bar": p_bar, "p_bar_pct": round(p_bar * 100, 2),
            "in_control": summary["in_control"],
            "violations": len(violations),
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# NP Chart (Count Defective — constant sample size)
# ---------------------------------------------------------------------------

def np_chart(df: "pd.DataFrame", config: dict) -> AnalysisResult:
    """
    Config:
        defects_column: str  — column with defective counts
        sample_size: int     — constant sample size
    """
    import pandas as pd

    defects_col = config.get("defects_column")
    sample_size = config.get("sample_size")

    if not defects_col or defects_col not in df.columns:
        return AnalysisResult(test_type="np_chart", test_category="spc", success=False,
                              summary={}, details={"error": f"Column '{defects_col}' not found"})
    if not sample_size:
        return AnalysisResult(test_type="np_chart", test_category="spc", success=False,
                              summary={}, details={"error": "sample_size is required"})

    defects = df[defects_col].dropna().astype(float).values
    n = len(defects)

    if n < 2:
        return AnalysisResult(test_type="np_chart", test_category="spc", success=False,
                              summary={}, details={"error": "Need at least 2 samples"})

    np_bar = float(np.mean(defects))
    p_bar = np_bar / sample_size

    ucl = np_bar + 3 * np.sqrt(np_bar * (1 - p_bar))
    lcl = max(0, np_bar - 3 * np.sqrt(np_bar * (1 - p_bar)))

    violations = _detect_violations(defects.tolist(), np_bar, ucl, lcl)
    warnings: list[str] = []
    if violations:
        warnings.append(f"{len(violations)} sample(s) out of control")

    chart_list = [
        chart_module.control_chart(
            values=defects.tolist(), center_line=np_bar, ucl=ucl, lcl=lcl,
            title="NP Chart — Count Defective", yaxis_title="Defective Count",
            violations=violations,
        ),
    ]

    return AnalysisResult(
        test_type="np_chart", test_category="spc", success=True,
        summary={
            "np_bar": np_bar, "p_bar": p_bar, "ucl": ucl, "lcl": lcl,
            "sample_size": sample_size, "num_samples": n,
            "violations": len(violations), "in_control": len(violations) == 0,
        },
        details={"defects": defects.tolist(), "violation_indices": violations},
        charts=chart_list,
        interpretation_context={
            "test_name": "NP Chart",
            "np_bar": np_bar, "p_bar": p_bar,
            "in_control": len(violations) == 0,
            "violations": len(violations),
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# C Chart (Count Defects per Unit — constant opportunity)
# ---------------------------------------------------------------------------

def c_chart(df: "pd.DataFrame", config: dict) -> AnalysisResult:
    """
    Config:
        column: str  — column with defect counts per unit
    """
    import pandas as pd

    column = config.get("column")

    if not column or column not in df.columns:
        return AnalysisResult(test_type="c_chart", test_category="spc", success=False,
                              summary={}, details={"error": f"Column '{column}' not found"})

    counts = df[column].dropna().astype(float).values
    n = len(counts)

    if n < 2:
        return AnalysisResult(test_type="c_chart", test_category="spc", success=False,
                              summary={}, details={"error": "Need at least 2 observations"})

    c_bar = float(np.mean(counts))
    ucl = c_bar + 3 * np.sqrt(c_bar)
    lcl = max(0, c_bar - 3 * np.sqrt(c_bar))

    violations = _detect_violations(counts.tolist(), c_bar, ucl, lcl)
    warnings: list[str] = []
    if violations:
        warnings.append(f"{len(violations)} unit(s) out of control")

    chart_list = [
        chart_module.control_chart(
            values=counts.tolist(), center_line=c_bar, ucl=ucl, lcl=lcl,
            title=f"C Chart — {column}", yaxis_title="Defect Count",
            violations=violations,
        ),
    ]

    return AnalysisResult(
        test_type="c_chart", test_category="spc", success=True,
        summary={
            "c_bar": c_bar, "ucl": ucl, "lcl": lcl, "num_units": n,
            "violations": len(violations), "in_control": len(violations) == 0,
        },
        details={"counts": counts.tolist(), "violation_indices": violations},
        charts=chart_list,
        interpretation_context={
            "test_name": "C Chart (Defects per Unit)",
            "c_bar": c_bar,
            "in_control": len(violations) == 0,
            "violations": len(violations),
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# U Chart (Defects per Unit — variable sample size)
# ---------------------------------------------------------------------------

def u_chart(df: "pd.DataFrame", config: dict) -> AnalysisResult:
    """
    Config:
        defects_column: str       — column with total defects
        units_column: str         — column with number of inspection units
        OR
        defects_column: str       — column with total defects
        units: int                — constant number of units
    """
    import pandas as pd

    defects_col = config.get("defects_column")
    units_col = config.get("units_column")
    const_units = config.get("units")

    if not defects_col or defects_col not in df.columns:
        return AnalysisResult(test_type="u_chart", test_category="spc", success=False,
                              summary={}, details={"error": f"Column '{defects_col}' not found"})

    defects = df[defects_col].dropna().astype(float).values
    n = len(defects)

    if units_col and units_col in df.columns:
        units = df[units_col].dropna().astype(float).values[:n]
    elif const_units:
        units = np.full(n, const_units, dtype=float)
    else:
        return AnalysisResult(test_type="u_chart", test_category="spc", success=False,
                              summary={}, details={"error": "Provide units_column or units"})

    if n < 2:
        return AnalysisResult(test_type="u_chart", test_category="spc", success=False,
                              summary={}, details={"error": "Need at least 2 samples"})

    u_values = defects / units
    u_bar = float(np.sum(defects) / np.sum(units))

    avg_units = float(np.mean(units))
    ucl = u_bar + 3 * np.sqrt(u_bar / avg_units)
    lcl = max(0, u_bar - 3 * np.sqrt(u_bar / avg_units))

    # Variable limits
    ucl_arr = u_bar + 3 * np.sqrt(u_bar / units)
    lcl_arr = np.maximum(0, u_bar - 3 * np.sqrt(u_bar / units))

    violations = [i for i in range(n) if u_values[i] > ucl_arr[i] or u_values[i] < lcl_arr[i]]
    warnings: list[str] = []
    if violations:
        warnings.append(f"{len(violations)} sample(s) out of control")

    chart_list = [
        chart_module.control_chart(
            values=u_values.tolist(), center_line=u_bar, ucl=ucl, lcl=lcl,
            title="U Chart — Defects per Unit", yaxis_title="Rate (defects/unit)",
            violations=violations,
        ),
    ]

    return AnalysisResult(
        test_type="u_chart", test_category="spc", success=True,
        summary={
            "u_bar": u_bar, "ucl": ucl, "lcl": lcl,
            "num_samples": n, "avg_units": avg_units,
            "violations": len(violations), "in_control": len(violations) == 0,
        },
        details={"u_values": u_values.tolist(), "violation_indices": violations},
        charts=chart_list,
        interpretation_context={
            "test_name": "U Chart (Defects per Unit, Variable Size)",
            "u_bar": u_bar,
            "in_control": len(violations) == 0,
            "violations": len(violations),
        },
        warnings=warnings,
    )
