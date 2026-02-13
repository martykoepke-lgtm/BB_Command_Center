"""
Process Capability Analysis and Measurement System Analysis (Gage R&R).

Tests:
  - capability_normal: Cp, Cpk, Pp, Ppk for normally distributed data
  - capability_nonnormal: Capability for non-normal distributions (via transformation)
  - msa_gage_rr: Measurement System Analysis — Gage R&R (crossed)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from app.stats import AnalysisResult, PlotlyChart
from app.stats import charts


# ---------------------------------------------------------------------------
# Process Capability — Normal Data
# ---------------------------------------------------------------------------

def capability_normal(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Cp, Cpk, Pp, Ppk for normally distributed process data.

    Config:
        column: str       — measurement column
        lsl: float        — lower specification limit (optional)
        usl: float        — upper specification limit (optional)
        target: float     — target value (optional)
        subgroup_size: int — for within-group sigma estimation (default: 1 = I-MR method)
    """
    column = config.get("column")
    lsl = config.get("lsl")
    usl = config.get("usl")
    target = config.get("target")
    subgroup_size = config.get("subgroup_size", 1)

    if not column or column not in df.columns:
        return AnalysisResult(test_type="capability_normal", test_category="capability", success=False,
                              summary={}, details={"error": f"Column '{column}' not found"})

    if lsl is None and usl is None:
        return AnalysisResult(test_type="capability_normal", test_category="capability", success=False,
                              summary={}, details={"error": "At least one spec limit (lsl or usl) is required"})

    series = df[column].dropna().astype(float)
    values = series.values
    n = len(values)
    warnings: list[str] = []

    if n < 2:
        return AnalysisResult(test_type="capability_normal", test_category="capability", success=False,
                              summary={}, details={"error": "Need at least 2 observations"})

    if n < 30:
        warnings.append(f"Small sample ({n}). Capability indices are more reliable with 30+ observations.")

    # Check normality
    if n >= 3:
        _, norm_p = sp_stats.shapiro(values[:5000])
        if norm_p < 0.05:
            warnings.append(
                f"Data may not be normally distributed (Shapiro-Wilk p={norm_p:.4f}). "
                "Consider capability_nonnormal analysis."
            )

    mean = float(np.mean(values))
    overall_std = float(np.std(values, ddof=1))

    # Within-group sigma estimation
    if subgroup_size == 1:
        # I-MR method (d2 = 1.128 for n=2)
        mr = np.abs(np.diff(values))
        within_std = float(np.mean(mr)) / 1.128 if len(mr) > 0 else overall_std
    else:
        # Pooled subgroup std
        d2_table = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}
        d2 = d2_table.get(subgroup_size, 2.326)
        n_complete = (n // subgroup_size) * subgroup_size
        if n_complete >= subgroup_size * 2:
            subgroups = values[:n_complete].reshape(-1, subgroup_size)
            r_bar = float(np.mean(np.ptp(subgroups, axis=1)))
            within_std = r_bar / d2
        else:
            within_std = overall_std
            warnings.append("Not enough data for subgroup-based sigma. Using overall std.")

    # Prevent division by zero
    if within_std == 0:
        within_std = 1e-10
        warnings.append("Within-group standard deviation is zero.")
    if overall_std == 0:
        overall_std = 1e-10
        warnings.append("Overall standard deviation is zero.")

    # Capability indices (within-group: Cp, Cpk)
    cp = cpk = cpu = cpl = None
    if lsl is not None and usl is not None:
        cp = (usl - lsl) / (6 * within_std)
        cpu = (usl - mean) / (3 * within_std)
        cpl = (mean - lsl) / (3 * within_std)
        cpk = min(cpu, cpl)
    elif usl is not None:
        cpu = (usl - mean) / (3 * within_std)
        cpk = cpu
    elif lsl is not None:
        cpl = (mean - lsl) / (3 * within_std)
        cpk = cpl

    # Performance indices (overall: Pp, Ppk)
    pp = ppk = ppu = ppl = None
    if lsl is not None and usl is not None:
        pp = (usl - lsl) / (6 * overall_std)
        ppu = (usl - mean) / (3 * overall_std)
        ppl = (mean - lsl) / (3 * overall_std)
        ppk = min(ppu, ppl)
    elif usl is not None:
        ppu = (usl - mean) / (3 * overall_std)
        ppk = ppu
    elif lsl is not None:
        ppl = (mean - lsl) / (3 * overall_std)
        ppk = ppl

    # PPM (parts per million out of spec)
    ppm_above = ppm_below = ppm_total = 0.0
    if usl is not None:
        z_upper = (usl - mean) / overall_std
        ppm_above = float(sp_stats.norm.sf(z_upper) * 1_000_000)
    if lsl is not None:
        z_lower = (mean - lsl) / overall_std
        ppm_below = float(sp_stats.norm.sf(z_lower) * 1_000_000)
    ppm_total = ppm_above + ppm_below

    # Sigma level (Z-bench equivalent)
    if ppm_total > 0 and ppm_total < 1_000_000:
        z_bench = float(sp_stats.norm.isf(ppm_total / 1_000_000))
    else:
        z_bench = 6.0 if ppm_total == 0 else 0.0

    summary = {
        "cp": cp,
        "cpk": cpk,
        "cpl": cpl,
        "cpu": cpu,
        "pp": pp,
        "ppk": ppk,
        "ppl": ppl,
        "ppu": ppu,
        "mean": mean,
        "within_std": within_std,
        "overall_std": overall_std,
        "ppm_total": round(ppm_total, 1),
        "ppm_above": round(ppm_above, 1),
        "ppm_below": round(ppm_below, 1),
        "z_bench": round(z_bench, 2),
        "sigma_level": round(z_bench + 1.5, 2),  # short-term sigma with 1.5 shift
        "n": n,
    }

    chart_list = [
        charts.capability_histogram(
            values=values.tolist(),
            lsl=lsl,
            usl=usl,
            target=target,
            title=f"Process Capability — {column}",
        ),
    ]

    # Capability rating
    if cpk is not None:
        if cpk >= 2.0:
            rating = "World-class (Cpk ≥ 2.0)"
        elif cpk >= 1.33:
            rating = "Capable (Cpk ≥ 1.33)"
        elif cpk >= 1.0:
            rating = "Marginally capable (1.0 ≤ Cpk < 1.33)"
        else:
            rating = "Not capable (Cpk < 1.0) — action required"
    else:
        rating = "N/A"

    return AnalysisResult(
        test_type="capability_normal",
        test_category="capability",
        success=True,
        summary=summary,
        details={
            "column": column, "lsl": lsl, "usl": usl, "target": target,
            "subgroup_size": subgroup_size,
        },
        charts=chart_list,
        interpretation_context={
            "test_name": "Process Capability (Normal)",
            "column": column,
            "cpk": cpk,
            "ppk": ppk,
            "rating": rating,
            "ppm_total": round(ppm_total, 1),
            "sigma_level": round(z_bench + 1.5, 2),
            "mean": mean,
            "within_std": within_std,
            "lsl": lsl,
            "usl": usl,
            "recommendation": (
                f"Process is {rating.lower()}. " +
                (f"Estimated {ppm_total:.0f} PPM out of spec. " if ppm_total > 0 else "No parts out of spec. ") +
                (f"Process is centered at {mean:.4f}" + (f", target is {target}." if target else "."))
            ),
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Process Capability — Non-Normal Data
# ---------------------------------------------------------------------------

def capability_nonnormal(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Capability for non-normal data using Box-Cox transformation.

    Config:
        column: str    — measurement column
        lsl: float     — lower specification limit
        usl: float     — upper specification limit
        target: float  — target value (optional)
    """
    column = config.get("column")
    lsl = config.get("lsl")
    usl = config.get("usl")
    target = config.get("target")

    if not column or column not in df.columns:
        return AnalysisResult(test_type="capability_nonnormal", test_category="capability", success=False,
                              summary={}, details={"error": f"Column '{column}' not found"})

    if lsl is None and usl is None:
        return AnalysisResult(test_type="capability_nonnormal", test_category="capability", success=False,
                              summary={}, details={"error": "At least one spec limit required"})

    series = df[column].dropna().astype(float)
    values = series.values
    n = len(values)
    warnings: list[str] = []

    if n < 3:
        return AnalysisResult(test_type="capability_nonnormal", test_category="capability", success=False,
                              summary={}, details={"error": "Need at least 3 observations"})

    # Ensure all positive for Box-Cox
    min_val = float(np.min(values))
    shift = 0.0
    if min_val <= 0:
        shift = abs(min_val) + 1
        values_shifted = values + shift
        warnings.append(f"Data shifted by +{shift} to make all values positive for Box-Cox transformation.")
    else:
        values_shifted = values

    try:
        transformed, lmbda = sp_stats.boxcox(values_shifted)
    except Exception:
        # Fallback: log transform
        transformed = np.log(values_shifted)
        lmbda = 0.0
        warnings.append("Box-Cox optimization failed. Using log transformation.")

    # Transform spec limits
    def transform_val(v: float) -> float:
        v_shifted = v + shift
        if v_shifted <= 0:
            return float('-inf')
        if lmbda == 0:
            return float(np.log(v_shifted))
        return float((v_shifted ** lmbda - 1) / lmbda)

    t_lsl = transform_val(lsl) if lsl is not None else None
    t_usl = transform_val(usl) if usl is not None else None

    t_mean = float(np.mean(transformed))
    t_std = float(np.std(transformed, ddof=1))

    if t_std == 0:
        t_std = 1e-10

    # Capability on transformed data
    cpk = ppk = None
    if t_lsl is not None and t_usl is not None:
        cp = (t_usl - t_lsl) / (6 * t_std)
        cpu = (t_usl - t_mean) / (3 * t_std)
        cpl = (t_mean - t_lsl) / (3 * t_std)
        cpk = min(cpu, cpl)
        ppk = cpk  # same for non-normal since we use overall sigma
    elif t_usl is not None:
        cpu = (t_usl - t_mean) / (3 * t_std)
        cpk = ppk = cpu
    elif t_lsl is not None:
        cpl = (t_mean - t_lsl) / (3 * t_std)
        cpk = ppk = cpl

    # Check normality of transformed data
    _, norm_p = sp_stats.shapiro(transformed[:5000])
    if norm_p < 0.05:
        warnings.append(
            f"Transformed data is still not normal (p={norm_p:.4f}). "
            "Capability indices may not be reliable."
        )

    summary = {
        "cpk": cpk,
        "ppk": ppk,
        "lambda": lmbda,
        "shift": shift,
        "original_mean": float(np.mean(df[column].dropna())),
        "original_std": float(np.std(df[column].dropna(), ddof=1)),
        "transformed_mean": t_mean,
        "transformed_std": t_std,
        "normality_p_transformed": float(norm_p),
        "n": n,
    }

    chart_list = [
        charts.capability_histogram(
            values=df[column].dropna().astype(float).tolist(),
            lsl=lsl, usl=usl, target=target,
            title=f"Process Capability (Non-Normal) — {column}",
        ),
    ]

    return AnalysisResult(
        test_type="capability_nonnormal",
        test_category="capability",
        success=True,
        summary=summary,
        details={
            "column": column, "lsl": lsl, "usl": usl, "target": target,
            "transformation": "box-cox", "lambda": lmbda,
        },
        charts=chart_list,
        interpretation_context={
            "test_name": "Process Capability (Non-Normal, Box-Cox)",
            "column": column,
            "cpk": cpk,
            "lambda": lmbda,
            "lsl": lsl, "usl": usl,
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Gage R&R (Measurement System Analysis)
# ---------------------------------------------------------------------------

def msa_gage_rr(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Crossed Gage R&R — evaluate measurement system variation.

    Config:
        measurement_column: str  — the measured values
        part_column: str         — part/item identifier
        operator_column: str     — operator/appraiser identifier
        tolerance: float         — optional: USL - LSL for %Tolerance calculation
    """
    meas_col = config.get("measurement_column")
    part_col = config.get("part_column")
    oper_col = config.get("operator_column")
    tolerance = config.get("tolerance")

    for col_name, col_val in [("measurement_column", meas_col), ("part_column", part_col), ("operator_column", oper_col)]:
        if not col_val or col_val not in df.columns:
            return AnalysisResult(test_type="msa_gage_rr", test_category="capability", success=False,
                                  summary={}, details={"error": f"{col_name} '{col_val}' not found"})

    clean = df[[meas_col, part_col, oper_col]].dropna()
    clean[meas_col] = clean[meas_col].astype(float)
    warnings: list[str] = []

    parts = clean[part_col].unique()
    operators = clean[oper_col].unique()
    n_parts = len(parts)
    n_operators = len(operators)

    if n_parts < 2 or n_operators < 2:
        return AnalysisResult(test_type="msa_gage_rr", test_category="capability", success=False,
                              summary={}, details={"error": f"Need at least 2 parts and 2 operators. Got {n_parts} parts, {n_operators} operators."})

    # Compute via ANOVA method
    try:
        import statsmodels.api as sm
        from statsmodels.formula.api import ols

        # Sanitize column names
        safe_meas = "measurement"
        safe_part = "part"
        safe_oper = "operator"
        anova_df = clean.rename(columns={meas_col: safe_meas, part_col: safe_part, oper_col: safe_oper})
        anova_df[safe_part] = anova_df[safe_part].astype(str)
        anova_df[safe_oper] = anova_df[safe_oper].astype(str)

        formula = f"{safe_meas} ~ C({safe_part}) + C({safe_oper}) + C({safe_part}):C({safe_oper})"
        model = ols(formula, data=anova_df).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)

        # Number of replicates per cell
        cell_counts = clean.groupby([part_col, oper_col]).size()
        n_replicates = int(cell_counts.mean())

        # Extract mean squares
        ms_part = float(anova_table.loc[f"C({safe_part})", "sum_sq"] / anova_table.loc[f"C({safe_part})", "df"])
        ms_oper = float(anova_table.loc[f"C({safe_oper})", "sum_sq"] / anova_table.loc[f"C({safe_oper})", "df"])

        interaction_key = f"C({safe_part}):C({safe_oper})"
        if interaction_key in anova_table.index:
            ms_interaction = float(anova_table.loc[interaction_key, "sum_sq"] / anova_table.loc[interaction_key, "df"])
        else:
            ms_interaction = 0.0

        ms_error = float(anova_table.loc["Residual", "sum_sq"] / anova_table.loc["Residual", "df"])

        # Variance components
        var_repeatability = ms_error
        var_interaction = max(0, (ms_interaction - ms_error) / n_replicates)
        var_operator = max(0, (ms_oper - ms_interaction) / (n_parts * n_replicates))
        var_part = max(0, (ms_part - ms_interaction) / (n_operators * n_replicates))

        var_reproducibility = var_operator + var_interaction
        var_gage_rr = var_repeatability + var_reproducibility
        var_total = var_gage_rr + var_part

        # Percentages
        pct_gage_rr = (var_gage_rr / var_total * 100) if var_total > 0 else 0
        pct_repeatability = (var_repeatability / var_total * 100) if var_total > 0 else 0
        pct_reproducibility = (var_reproducibility / var_total * 100) if var_total > 0 else 0
        pct_part = (var_part / var_total * 100) if var_total > 0 else 0

        # Study variation (6 * sigma)
        sv_gage_rr = 6 * np.sqrt(var_gage_rr)
        sv_total = 6 * np.sqrt(var_total)

        # %Study Var
        pct_sv_gage_rr = (sv_gage_rr / sv_total * 100) if sv_total > 0 else 0

        # %Tolerance
        pct_tolerance = (sv_gage_rr / tolerance * 100) if tolerance and tolerance > 0 else None

        # Number of distinct categories
        ndc = max(1, int(1.41 * np.sqrt(var_part / var_gage_rr))) if var_gage_rr > 0 else 999

        # Rating
        if pct_sv_gage_rr < 10:
            rating = "Acceptable"
        elif pct_sv_gage_rr < 30:
            rating = "Marginal — may be acceptable depending on application"
        else:
            rating = "Not acceptable — measurement system needs improvement"

        summary = {
            "pct_gage_rr_contribution": round(pct_gage_rr, 2),
            "pct_repeatability": round(pct_repeatability, 2),
            "pct_reproducibility": round(pct_reproducibility, 2),
            "pct_part_to_part": round(pct_part, 2),
            "pct_study_var": round(pct_sv_gage_rr, 2),
            "pct_tolerance": round(pct_tolerance, 2) if pct_tolerance is not None else None,
            "ndc": ndc,
            "rating": rating,
            "n_parts": n_parts,
            "n_operators": n_operators,
            "n_replicates": n_replicates,
        }

        details = {
            "variance_components": {
                "repeatability": round(var_repeatability, 6),
                "reproducibility": round(var_reproducibility, 6),
                "operator": round(var_operator, 6),
                "interaction": round(var_interaction, 6),
                "gage_rr": round(var_gage_rr, 6),
                "part_to_part": round(var_part, 6),
                "total": round(var_total, 6),
            },
            "study_variation": {
                "gage_rr": round(float(sv_gage_rr), 4),
                "total": round(float(sv_total), 4),
            },
            "tolerance": tolerance,
        }

        # Chart: variance component breakdown
        comp_names = ["Repeatability", "Reproducibility", "Part-to-Part"]
        comp_values = [pct_repeatability, pct_reproducibility, pct_part]
        chart_list = [
            charts.bar_chart(
                categories=comp_names, values=comp_values,
                title="Gage R&R — Variance Components (% Contribution)",
                yaxis_title="% of Total Variation",
            ),
        ]

        return AnalysisResult(
            test_type="msa_gage_rr",
            test_category="capability",
            success=True,
            summary=summary,
            details=details,
            charts=chart_list,
            interpretation_context={
                "test_name": "Gage R&R (Crossed ANOVA Method)",
                "pct_gage_rr": round(pct_gage_rr, 2),
                "pct_study_var": round(pct_sv_gage_rr, 2),
                "ndc": ndc,
                "rating": rating,
                "recommendation": (
                    f"Measurement system %Study Var = {pct_sv_gage_rr:.1f}%. {rating}. "
                    f"Number of distinct categories = {ndc} " +
                    ("(≥ 5 is ideal)." if ndc >= 5 else "(< 5 — system cannot adequately distinguish between parts).")
                ),
            },
            warnings=warnings,
        )

    except Exception as e:
        return AnalysisResult(test_type="msa_gage_rr", test_category="capability", success=False,
                              summary={}, details={"error": str(e)}, warnings=[str(e)])
