"""
Design of Experiments (DOE) — factorial design generation and analysis.

Tests:
  - full_factorial: Generate 2^k full factorial design
  - fractional_factorial: Generate 2^(k-p) fractional factorial design
  - doe_analysis: Analyze factorial experiment results (main effects + interactions)
"""

from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from app.stats import AnalysisResult, PlotlyChart
from app.stats import charts


# ---------------------------------------------------------------------------
# Full Factorial Design Generation
# ---------------------------------------------------------------------------

def full_factorial(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Generate a 2^k full factorial design matrix.

    Config:
        factors: dict[str, tuple[any, any]]  — { "Temperature": (150, 200), "Pressure": (50, 100) }
        center_points: int                   — number of center point runs (default: 0)
        replicates: int                      — number of replicates (default: 1)
    """
    factors = config.get("factors", {})
    center_points = config.get("center_points", 0)
    replicates = config.get("replicates", 1)

    if len(factors) < 2:
        return AnalysisResult(test_type="full_factorial", test_category="doe", success=False,
                              summary={}, details={"error": "Need at least 2 factors"})

    if len(factors) > 10:
        return AnalysisResult(test_type="full_factorial", test_category="doe", success=False,
                              summary={}, details={"error": f"Too many factors ({len(factors)}). Maximum 10 for full factorial."})

    factor_names = list(factors.keys())
    k = len(factor_names)
    n_runs = 2 ** k * replicates + center_points

    # Generate coded design matrix (-1, +1)
    coded_levels = list(product([-1, 1], repeat=k))

    # Expand for replicates
    design_coded = coded_levels * replicates

    # Add center points
    for _ in range(center_points):
        design_coded.append(tuple([0] * k))

    # Build actual values
    design_actual = []
    for run in design_coded:
        row = {}
        for i, factor in enumerate(factor_names):
            low, high = factors[factor]
            if run[i] == -1:
                row[factor] = low
            elif run[i] == 1:
                row[factor] = high
            else:
                row[factor] = (low + high) / 2  # center point
        design_actual.append(row)

    # Randomize run order
    rng = np.random.default_rng(42)
    run_order = list(range(len(design_actual)))
    rng.shuffle(run_order)

    design_table = []
    for idx, orig_idx in enumerate(run_order):
        entry = {"run_order": idx + 1, "std_order": orig_idx + 1}
        entry.update(design_actual[orig_idx])
        entry["coded"] = {factor_names[j]: design_coded[orig_idx][j] for j in range(k)}
        design_table.append(entry)

    summary = {
        "design_type": f"2^{k} Full Factorial",
        "factors": k,
        "factor_names": factor_names,
        "total_runs": len(design_table),
        "base_runs": 2 ** k,
        "replicates": replicates,
        "center_points": center_points,
    }

    return AnalysisResult(
        test_type="full_factorial",
        test_category="doe",
        success=True,
        summary=summary,
        details={
            "design_table": design_table,
            "factors": factors,
            "coded_levels": {name: [-1, 1] for name in factor_names},
            "actual_levels": factors,
        },
        charts=[],
        interpretation_context={
            "test_name": f"2^{k} Full Factorial Design",
            "factors": factor_names,
            "total_runs": len(design_table),
            "instruction": (
                f"This design requires {len(design_table)} experimental runs. "
                "Record the response variable for each run, then use doe_analysis to analyze results."
            ),
        },
        warnings=[],
    )


# ---------------------------------------------------------------------------
# Fractional Factorial Design Generation
# ---------------------------------------------------------------------------

def fractional_factorial(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Generate a 2^(k-p) fractional factorial design.

    Config:
        factors: dict[str, tuple[any, any]]  — factor names with low/high levels
        fraction: int                        — p value (number of generators, e.g., 1 for half-fraction)
        replicates: int                      — number of replicates (default: 1)
    """
    factors = config.get("factors", {})
    p = config.get("fraction", 1)
    replicates = config.get("replicates", 1)

    factor_names = list(factors.keys())
    k = len(factor_names)

    if k < 3:
        return AnalysisResult(test_type="fractional_factorial", test_category="doe", success=False,
                              summary={}, details={"error": "Fractional factorial requires at least 3 factors"})

    if p >= k:
        return AnalysisResult(test_type="fractional_factorial", test_category="doe", success=False,
                              summary={}, details={"error": f"Fraction p={p} must be less than k={k}"})

    base_k = k - p
    base_runs = 2 ** base_k

    # Generate base design for (k-p) factors
    base_design = list(product([-1, 1], repeat=base_k))

    # Generate remaining factors using highest-order interactions
    full_design = []
    for run in base_design:
        row = list(run)
        for gen_idx in range(p):
            # Use product of base columns as generator
            # Simple generator: last factor = product of first (base_k) factors
            generated = 1
            for val in run[:base_k - gen_idx]:
                generated *= val
            row.append(generated)
        full_design.append(tuple(row))

    # Expand for replicates
    full_design = full_design * replicates

    # Randomize and build table
    rng = np.random.default_rng(42)
    run_order = list(range(len(full_design)))
    rng.shuffle(run_order)

    design_table = []
    for idx, orig_idx in enumerate(run_order):
        coded = full_design[orig_idx]
        entry = {"run_order": idx + 1, "std_order": orig_idx + 1}
        for j, name in enumerate(factor_names):
            low, high = factors[name]
            entry[name] = low if coded[j] == -1 else high
        entry["coded"] = {factor_names[j]: coded[j] for j in range(k)}
        design_table.append(entry)

    resolution = base_k - p + 1  # rough estimate

    summary = {
        "design_type": f"2^({k}-{p}) Fractional Factorial",
        "factors": k,
        "fraction": p,
        "factor_names": factor_names,
        "base_runs": base_runs,
        "total_runs": len(design_table),
        "replicates": replicates,
        "resolution": f"Resolution {resolution}" if resolution >= 3 else "Low resolution",
    }

    return AnalysisResult(
        test_type="fractional_factorial",
        test_category="doe",
        success=True,
        summary=summary,
        details={
            "design_table": design_table,
            "factors": factors,
            "generators": f"p={p}",
        },
        charts=[],
        interpretation_context={
            "test_name": f"2^({k}-{p}) Fractional Factorial Design",
            "factors": factor_names,
            "total_runs": len(design_table),
            "resolution": summary["resolution"],
            "instruction": (
                f"This {summary['resolution']} design requires {len(design_table)} runs "
                f"(reduced from {2 ** k} in full factorial). "
                "Some effects will be confounded. Record response values for each run."
            ),
        },
        warnings=["Main effects may be confounded with higher-order interactions." if p > 0 else ""],
    )


# ---------------------------------------------------------------------------
# DOE Analysis (Analyze factorial experiment results)
# ---------------------------------------------------------------------------

def doe_analysis(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Analyze results from a factorial experiment.

    Config:
        response_column: str       — the measured response (Y)
        factor_columns: list[str]  — factor columns (should contain coded -1/+1 or categorical levels)
        alpha: float               — significance level (default: 0.05)
    """
    response_col = config.get("response_column")
    factor_cols = config.get("factor_columns", [])
    alpha = config.get("alpha", 0.05)

    if not response_col or response_col not in df.columns:
        return AnalysisResult(test_type="doe_analysis", test_category="doe", success=False,
                              summary={}, details={"error": f"Response column '{response_col}' not found"})

    missing = [c for c in factor_cols if c not in df.columns]
    if missing:
        return AnalysisResult(test_type="doe_analysis", test_category="doe", success=False,
                              summary={}, details={"error": f"Factor columns not found: {missing}"})

    if len(factor_cols) < 1:
        return AnalysisResult(test_type="doe_analysis", test_category="doe", success=False,
                              summary={}, details={"error": "Need at least 1 factor column"})

    clean = df[[response_col] + factor_cols].dropna()
    n = len(clean)
    warnings: list[str] = []

    if n < 4:
        return AnalysisResult(test_type="doe_analysis", test_category="doe", success=False,
                              summary={}, details={"error": f"Need at least 4 observations, got {n}"})

    try:
        import statsmodels.api as sm
        from statsmodels.formula.api import ols

        # Sanitize column names
        col_map = {}
        safe_response = "Y_response"
        col_map[response_col] = safe_response
        safe_factors = []
        for i, f in enumerate(factor_cols):
            safe = f"F{i}"
            col_map[f] = safe
            safe_factors.append(safe)

        formula_df = clean.rename(columns=col_map)
        formula_df[safe_response] = formula_df[safe_response].astype(float)
        for sf in safe_factors:
            formula_df[sf] = formula_df[sf].astype(str)

        # Build formula with main effects and two-way interactions
        main_terms = [f"C({sf})" for sf in safe_factors]
        interaction_terms = []
        if len(safe_factors) >= 2:
            for i in range(len(safe_factors)):
                for j in range(i + 1, len(safe_factors)):
                    interaction_terms.append(f"C({safe_factors[i]}):C({safe_factors[j]})")

        formula = f"{safe_response} ~ " + " + ".join(main_terms + interaction_terms)
        model = ols(formula, data=formula_df).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)

        # Parse ANOVA results
        effects = {}
        for idx in anova_table.index:
            if idx == "Residual":
                continue
            row = anova_table.loc[idx]
            f_val = float(row.get("F", 0)) if not pd.isna(row.get("F")) else None
            p_val = float(row.get("PR(>F)", 1)) if not pd.isna(row.get("PR(>F)")) else None

            # Map back to original names
            label = str(idx)
            for safe, orig in zip(safe_factors, factor_cols):
                label = label.replace(f"C({safe})", orig)

            effects[label] = {
                "sum_sq": float(row.get("sum_sq", 0)),
                "df": float(row.get("df", 0)),
                "F": f_val,
                "p_value": p_val,
                "significant": p_val < alpha if p_val is not None else False,
            }

        significant_effects = [name for name, e in effects.items() if e["significant"]]

        # Main effects plot
        factor_levels_dict: dict[str, list] = {}
        factor_means_dict: dict[str, list[float]] = {}
        for factor in factor_cols:
            levels = sorted(clean[factor].astype(str).unique())
            factor_levels_dict[factor] = levels
            means = [float(clean[clean[factor].astype(str) == lvl][response_col].astype(float).mean()) for lvl in levels]
            factor_means_dict[factor] = means

        chart_list = [
            charts.main_effects_plot(
                factor_names=factor_cols,
                factor_levels=factor_levels_dict,
                factor_means=factor_means_dict,
                title=f"Main Effects Plot — {response_col}",
                yaxis_title=f"Mean {response_col}",
            ),
        ]

        # Interaction plot for first two factors (if >= 2 factors)
        if len(factor_cols) >= 2:
            f1, f2 = factor_cols[0], factor_cols[1]
            f1_levels = sorted(clean[f1].astype(str).unique())
            f2_levels = sorted(clean[f2].astype(str).unique())

            int_means: dict[str, list[float]] = {}
            for f2_lvl in f2_levels:
                means = []
                for f1_lvl in f1_levels:
                    subset = clean[(clean[f1].astype(str) == f1_lvl) & (clean[f2].astype(str) == f2_lvl)]
                    means.append(float(subset[response_col].astype(float).mean()) if len(subset) > 0 else 0)
                int_means[f2_lvl] = means

            chart_list.append(charts.interaction_plot(
                x_levels=f1_levels,
                trace_levels=f2_levels,
                means=int_means,
                title=f"Interaction: {f1} × {f2}",
                xaxis_title=f1,
                yaxis_title=f"Mean {response_col}",
                trace_name=f2,
            ))

        # Pareto of effects (absolute effect sizes)
        effect_sizes = []
        for name, e in effects.items():
            if e["F"] is not None:
                effect_sizes.append((name, abs(e["F"])))
        effect_sizes.sort(key=lambda x: x[1], reverse=True)

        if effect_sizes:
            chart_list.append(charts.bar_chart(
                categories=[e[0] for e in effect_sizes],
                values=[e[1] for e in effect_sizes],
                title="Pareto of Standardized Effects (|F-statistic|)",
                yaxis_title="|F|",
                orientation="h",
            ))

        summary = {
            "r_squared": float(model.rsquared),
            "adj_r_squared": float(model.rsquared_adj),
            "effects": effects,
            "significant_effects": significant_effects,
            "n": n,
            "factor_count": len(factor_cols),
        }

        return AnalysisResult(
            test_type="doe_analysis",
            test_category="doe",
            success=True,
            summary=summary,
            details={
                "response_column": response_col,
                "factor_columns": factor_cols,
                "alpha": alpha,
                "anova_effects": effects,
                "r_squared": float(model.rsquared),
            },
            charts=chart_list,
            interpretation_context={
                "test_name": "DOE Analysis (Factorial)",
                "response_column": response_col,
                "factor_columns": factor_cols,
                "significant_effects": significant_effects,
                "r_squared": float(model.rsquared),
                "r_squared_pct": round(float(model.rsquared) * 100, 1),
                "alpha": alpha,
                "recommendation": (
                    f"Significant effects: {', '.join(significant_effects)}. "
                    f"Model explains {model.rsquared * 100:.1f}% of variation."
                    if significant_effects else
                    "No statistically significant effects found at the chosen alpha level."
                ),
            },
            warnings=warnings,
        )

    except Exception as e:
        return AnalysisResult(test_type="doe_analysis", test_category="doe", success=False,
                              summary={}, details={"error": str(e)}, warnings=[str(e)])
