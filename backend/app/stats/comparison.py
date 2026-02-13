"""
Comparison tests — parametric and non-parametric group comparisons.

Tests:
  - one_sample_t: Compare sample mean to a known value
  - two_sample_t: Compare means of two independent groups
  - paired_t: Compare means of paired observations
  - one_way_anova: Compare means across 3+ groups
  - two_way_anova: Two-factor comparison with interaction
  - mann_whitney: Non-parametric 2-sample comparison
  - kruskal_wallis: Non-parametric 3+ group comparison
  - chi_square_association: Test association between categorical variables
  - chi_square_goodness: Test distribution fit
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from app.stats import AnalysisResult, PlotlyChart
from app.stats import charts


def _check_normality(arr: np.ndarray, name: str, warnings: list[str]) -> bool:
    """Quick normality check — returns True if likely normal."""
    if len(arr) < 3:
        return True  # Can't test, assume OK
    _, p = sp_stats.shapiro(arr[:5000])  # Shapiro limited to 5000
    if p < 0.05:
        warnings.append(
            f"Group '{name}' may not be normally distributed (Shapiro-Wilk p={p:.4f}). "
            "Consider a non-parametric alternative."
        )
        return False
    return True


def _cohen_d(group1: np.ndarray, group2: np.ndarray) -> float:
    """Cohen's d effect size for two groups."""
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return float((np.mean(group1) - np.mean(group2)) / pooled_std)


def _effect_size_label(d: float) -> str:
    """Interpret Cohen's d."""
    ad = abs(d)
    if ad < 0.2:
        return "negligible"
    elif ad < 0.5:
        return "small"
    elif ad < 0.8:
        return "medium"
    else:
        return "large"


# ---------------------------------------------------------------------------
# One-Sample t-Test
# ---------------------------------------------------------------------------

def one_sample_t(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        column: str            — column to test
        population_mean: float — hypothesized population mean
        alpha: float           — significance level (default: 0.05)
        alternative: str       — "two-sided" | "less" | "greater" (default: "two-sided")
    """
    column = config.get("column")
    pop_mean = config.get("population_mean")
    alpha = config.get("alpha", 0.05)
    alternative = config.get("alternative", "two-sided")

    if not column or column not in df.columns:
        return AnalysisResult(
            test_type="one_sample_t", test_category="comparison", success=False,
            summary={}, details={"error": f"Column '{column}' not found"},
        )
    if pop_mean is None:
        return AnalysisResult(
            test_type="one_sample_t", test_category="comparison", success=False,
            summary={}, details={"error": "population_mean is required"},
        )

    series = df[column].dropna().astype(float)
    arr = series.values
    n = len(arr)
    warnings: list[str] = []

    if n < 2:
        return AnalysisResult(
            test_type="one_sample_t", test_category="comparison", success=False,
            summary={}, details={"error": "Need at least 2 observations"},
            warnings=["Insufficient data for one-sample t-test"],
        )

    _check_normality(arr, column, warnings)

    t_stat, p_value = sp_stats.ttest_1samp(arr, pop_mean)
    # Adjust p-value for one-sided if needed
    if alternative == "less":
        p_value = p_value / 2 if t_stat < 0 else 1 - p_value / 2
    elif alternative == "greater":
        p_value = p_value / 2 if t_stat > 0 else 1 - p_value / 2

    sample_mean = float(np.mean(arr))
    sample_std = float(np.std(arr, ddof=1))
    se = sample_std / np.sqrt(n)
    ci = sp_stats.t.interval(1 - alpha, df=n - 1, loc=sample_mean, scale=se)
    effect_size = (sample_mean - pop_mean) / sample_std if sample_std > 0 else 0.0

    significant = float(p_value) < alpha

    summary = {
        "statistic": float(t_stat),
        "p_value": float(p_value),
        "significant": significant,
        "sample_mean": sample_mean,
        "population_mean": pop_mean,
        "difference": sample_mean - pop_mean,
        "effect_size": effect_size,
        "ci_lower": float(ci[0]),
        "ci_upper": float(ci[1]),
    }

    chart_list = [
        charts.histogram(arr.tolist(), name=column, title=f"Distribution of {column}", xaxis_title=column, show_normal_curve=True),
    ]

    return AnalysisResult(
        test_type="one_sample_t",
        test_category="comparison",
        success=True,
        summary=summary,
        details={
            "column": column, "n": n, "alpha": alpha, "alternative": alternative,
            "sample_std": sample_std, "standard_error": float(se),
            "degrees_of_freedom": n - 1,
        },
        charts=chart_list,
        interpretation_context={
            "test_name": "One-Sample t-Test",
            "column": column,
            "sample_mean": sample_mean,
            "population_mean": pop_mean,
            "p_value": float(p_value),
            "significant": significant,
            "alpha": alpha,
            "effect_size": effect_size,
            "effect_label": _effect_size_label(effect_size),
            "conclusion": (
                f"The sample mean ({sample_mean:.4f}) is significantly different from {pop_mean}"
                if significant else
                f"No significant difference between sample mean ({sample_mean:.4f}) and {pop_mean}"
            ),
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Two-Sample t-Test
# ---------------------------------------------------------------------------

def two_sample_t(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        y_column: str     — response variable (continuous)
        x_column: str     — grouping variable (2 levels)
        alpha: float      — significance level (default: 0.05)
        equal_var: bool   — assume equal variance? (default: auto-detect via Levene)
        alternative: str  — "two-sided" | "less" | "greater" (default: "two-sided")
    """
    y_col = config.get("y_column")
    x_col = config.get("x_column")
    alpha = config.get("alpha", 0.05)
    equal_var = config.get("equal_var")  # None = auto-detect
    alternative = config.get("alternative", "two-sided")

    if not y_col or y_col not in df.columns:
        return AnalysisResult(test_type="two_sample_t", test_category="comparison", success=False,
                              summary={}, details={"error": f"Y column '{y_col}' not found"})
    if not x_col or x_col not in df.columns:
        return AnalysisResult(test_type="two_sample_t", test_category="comparison", success=False,
                              summary={}, details={"error": f"X column '{x_col}' not found"})

    clean = df[[y_col, x_col]].dropna()
    groups = clean[x_col].unique()
    if len(groups) != 2:
        return AnalysisResult(test_type="two_sample_t", test_category="comparison", success=False,
                              summary={}, details={"error": f"Expected 2 groups, found {len(groups)}: {list(groups)}"},
                              warnings=[f"Two-sample t-test requires exactly 2 groups. Found: {list(groups)}"])

    g1 = clean[clean[x_col] == groups[0]][y_col].astype(float).values
    g2 = clean[clean[x_col] == groups[1]][y_col].astype(float).values
    warnings: list[str] = []

    if len(g1) < 2 or len(g2) < 2:
        return AnalysisResult(test_type="two_sample_t", test_category="comparison", success=False,
                              summary={}, details={"error": "Each group needs at least 2 observations"})

    _check_normality(g1, str(groups[0]), warnings)
    _check_normality(g2, str(groups[1]), warnings)

    # Auto-detect equal variance via Levene's test
    if equal_var is None:
        levene_stat, levene_p = sp_stats.levene(g1, g2)
        equal_var = levene_p >= 0.05
        if not equal_var:
            warnings.append(
                f"Levene's test indicates unequal variances (p={levene_p:.4f}). Using Welch's t-test."
            )

    t_stat, p_value = sp_stats.ttest_ind(g1, g2, equal_var=equal_var, alternative=alternative)
    d = _cohen_d(g1, g2)

    group_data = {str(groups[0]): g1.tolist(), str(groups[1]): g2.tolist()}

    summary = {
        "statistic": float(t_stat),
        "p_value": float(p_value),
        "significant": float(p_value) < alpha,
        "group_1": str(groups[0]),
        "group_1_mean": float(np.mean(g1)),
        "group_1_n": len(g1),
        "group_2": str(groups[1]),
        "group_2_mean": float(np.mean(g2)),
        "group_2_n": len(g2),
        "mean_difference": float(np.mean(g1) - np.mean(g2)),
        "effect_size": d,
        "effect_label": _effect_size_label(d),
        "equal_var": equal_var,
    }

    chart_list = [
        charts.box_plot(group_data, title=f"{y_col} by {x_col}", yaxis_title=y_col),
    ]

    return AnalysisResult(
        test_type="two_sample_t",
        test_category="comparison",
        success=True,
        summary=summary,
        details={"y_column": y_col, "x_column": x_col, "alpha": alpha, "alternative": alternative,
                 "group_1_std": float(np.std(g1, ddof=1)), "group_2_std": float(np.std(g2, ddof=1))},
        charts=chart_list,
        interpretation_context={
            "test_name": "Two-Sample t-Test" + (" (Welch's)" if not equal_var else " (Pooled)"),
            "y_column": y_col, "x_column": x_col,
            "groups": [str(groups[0]), str(groups[1])],
            "means": [float(np.mean(g1)), float(np.mean(g2))],
            "p_value": float(p_value),
            "significant": float(p_value) < alpha,
            "effect_size": d,
            "effect_label": _effect_size_label(d),
            "alpha": alpha,
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Paired t-Test
# ---------------------------------------------------------------------------

def paired_t(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        column_before: str  — before measurements
        column_after: str   — after measurements
        alpha: float        — significance level (default: 0.05)
    """
    col_before = config.get("column_before")
    col_after = config.get("column_after")
    alpha = config.get("alpha", 0.05)

    if not col_before or col_before not in df.columns:
        return AnalysisResult(test_type="paired_t", test_category="comparison", success=False,
                              summary={}, details={"error": f"Before column '{col_before}' not found"})
    if not col_after or col_after not in df.columns:
        return AnalysisResult(test_type="paired_t", test_category="comparison", success=False,
                              summary={}, details={"error": f"After column '{col_after}' not found"})

    clean = df[[col_before, col_after]].dropna()
    before = clean[col_before].astype(float).values
    after = clean[col_after].astype(float).values
    n = len(before)
    warnings: list[str] = []

    if n < 2:
        return AnalysisResult(test_type="paired_t", test_category="comparison", success=False,
                              summary={}, details={"error": "Need at least 2 paired observations"})

    diffs = after - before
    _check_normality(diffs, "differences", warnings)

    t_stat, p_value = sp_stats.ttest_rel(before, after)
    mean_diff = float(np.mean(diffs))
    std_diff = float(np.std(diffs, ddof=1))
    se = std_diff / np.sqrt(n)
    ci = sp_stats.t.interval(1 - alpha, df=n - 1, loc=mean_diff, scale=se)
    effect = mean_diff / std_diff if std_diff > 0 else 0.0

    summary = {
        "statistic": float(t_stat),
        "p_value": float(p_value),
        "significant": float(p_value) < alpha,
        "mean_difference": mean_diff,
        "std_difference": std_diff,
        "mean_before": float(np.mean(before)),
        "mean_after": float(np.mean(after)),
        "effect_size": effect,
        "ci_lower": float(ci[0]),
        "ci_upper": float(ci[1]),
        "n_pairs": n,
    }

    chart_list = [
        charts.box_plot(
            {"Before": before.tolist(), "After": after.tolist()},
            title=f"Before vs After", yaxis_title="Value",
        ),
        charts.histogram(diffs.tolist(), name="Differences", title="Distribution of Differences",
                         xaxis_title="After - Before", show_normal_curve=True),
    ]

    return AnalysisResult(
        test_type="paired_t",
        test_category="comparison",
        success=True,
        summary=summary,
        details={"column_before": col_before, "column_after": col_after, "alpha": alpha, "n": n},
        charts=chart_list,
        interpretation_context={
            "test_name": "Paired t-Test",
            "before_col": col_before, "after_col": col_after,
            "mean_before": float(np.mean(before)), "mean_after": float(np.mean(after)),
            "mean_difference": mean_diff,
            "p_value": float(p_value),
            "significant": float(p_value) < alpha,
            "effect_size": effect,
            "effect_label": _effect_size_label(effect),
            "alpha": alpha,
            "direction": "increased" if mean_diff > 0 else "decreased",
            "pct_change": round(abs(mean_diff) / abs(float(np.mean(before))) * 100, 2) if np.mean(before) != 0 else 0,
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# One-Way ANOVA
# ---------------------------------------------------------------------------

def one_way_anova(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        y_column: str  — response variable (continuous)
        x_column: str  — grouping variable (3+ levels)
        alpha: float   — significance level (default: 0.05)
    """
    y_col = config.get("y_column")
    x_col = config.get("x_column")
    alpha = config.get("alpha", 0.05)

    if not y_col or y_col not in df.columns:
        return AnalysisResult(test_type="one_way_anova", test_category="comparison", success=False,
                              summary={}, details={"error": f"Y column '{y_col}' not found"})
    if not x_col or x_col not in df.columns:
        return AnalysisResult(test_type="one_way_anova", test_category="comparison", success=False,
                              summary={}, details={"error": f"X column '{x_col}' not found"})

    clean = df[[y_col, x_col]].dropna()
    groups_dict: dict[str, np.ndarray] = {}
    for name, group in clean.groupby(x_col):
        arr = group[y_col].astype(float).values
        if len(arr) >= 2:
            groups_dict[str(name)] = arr

    if len(groups_dict) < 2:
        return AnalysisResult(test_type="one_way_anova", test_category="comparison", success=False,
                              summary={}, details={"error": f"Need at least 2 groups with 2+ observations"},
                              warnings=["Insufficient groups for ANOVA"])

    warnings: list[str] = []
    for gname, garr in groups_dict.items():
        _check_normality(garr, gname, warnings)

    # Levene's test for equal variances
    levene_stat, levene_p = sp_stats.levene(*groups_dict.values())
    if levene_p < 0.05:
        warnings.append(
            f"Levene's test indicates unequal variances (p={levene_p:.4f}). "
            "ANOVA is moderately robust, but consider Kruskal-Wallis if groups are very unequal."
        )

    f_stat, p_value = sp_stats.f_oneway(*groups_dict.values())

    # Effect size: eta-squared
    grand_mean = float(np.mean(clean[y_col].astype(float)))
    ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups_dict.values())
    ss_total = sum(np.sum((g - grand_mean) ** 2) for g in groups_dict.values())
    eta_sq = float(ss_between / ss_total) if ss_total > 0 else 0.0

    group_stats = {name: {"n": len(arr), "mean": float(np.mean(arr)), "std": float(np.std(arr, ddof=1))}
                   for name, arr in groups_dict.items()}

    summary = {
        "statistic": float(f_stat),
        "p_value": float(p_value),
        "significant": float(p_value) < alpha,
        "group_count": len(groups_dict),
        "eta_squared": eta_sq,
        "levene_p": float(levene_p),
    }

    chart_list = [
        charts.box_plot(
            {name: arr.tolist() for name, arr in groups_dict.items()},
            title=f"{y_col} by {x_col}",
            yaxis_title=y_col,
        ),
    ]

    # Post-hoc: Tukey HSD if significant
    posthoc = None
    if float(p_value) < alpha and len(groups_dict) >= 3:
        try:
            from statsmodels.stats.multicomp import pairwise_tukeyhsd
            tukey = pairwise_tukeyhsd(clean[y_col].astype(float), clean[x_col].astype(str), alpha=alpha)
            posthoc = []
            for row in tukey.summary().data[1:]:
                posthoc.append({
                    "group1": str(row[0]), "group2": str(row[1]),
                    "meandiff": float(row[2]), "p_adj": float(row[3]),
                    "lower": float(row[4]), "upper": float(row[5]),
                    "reject": bool(row[6]),
                })
        except Exception:
            warnings.append("Tukey HSD post-hoc test could not be computed.")

    details = {
        "y_column": y_col, "x_column": x_col, "alpha": alpha,
        "group_stats": group_stats, "posthoc_tukey": posthoc,
        "levene": {"statistic": float(levene_stat), "p_value": float(levene_p)},
    }

    return AnalysisResult(
        test_type="one_way_anova",
        test_category="comparison",
        success=True,
        summary=summary,
        details=details,
        charts=chart_list,
        interpretation_context={
            "test_name": "One-Way ANOVA",
            "y_column": y_col, "x_column": x_col,
            "group_count": len(groups_dict),
            "group_names": list(groups_dict.keys()),
            "group_means": {name: float(np.mean(arr)) for name, arr in groups_dict.items()},
            "p_value": float(p_value),
            "significant": float(p_value) < alpha,
            "eta_squared": eta_sq,
            "alpha": alpha,
            "has_posthoc": posthoc is not None,
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Two-Way ANOVA
# ---------------------------------------------------------------------------

def two_way_anova(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        y_column: str    — response variable
        factor_a: str    — first factor
        factor_b: str    — second factor
        alpha: float     — significance level (default: 0.05)
    """
    y_col = config.get("y_column")
    factor_a = config.get("factor_a")
    factor_b = config.get("factor_b")
    alpha = config.get("alpha", 0.05)

    for col_name, col_val in [("y_column", y_col), ("factor_a", factor_a), ("factor_b", factor_b)]:
        if not col_val or col_val not in df.columns:
            return AnalysisResult(test_type="two_way_anova", test_category="comparison", success=False,
                                  summary={}, details={"error": f"{col_name} '{col_val}' not found"})

    warnings: list[str] = []
    clean = df[[y_col, factor_a, factor_b]].dropna()

    try:
        import statsmodels.api as sm
        from statsmodels.formula.api import ols

        # Sanitize column names for formula
        safe_y = y_col.replace(" ", "_")
        safe_a = factor_a.replace(" ", "_")
        safe_b = factor_b.replace(" ", "_")
        formula_df = clean.rename(columns={y_col: safe_y, factor_a: safe_a, factor_b: safe_b})
        formula_df[safe_y] = formula_df[safe_y].astype(float)
        formula_df[safe_a] = formula_df[safe_a].astype(str)
        formula_df[safe_b] = formula_df[safe_b].astype(str)

        formula = f"Q('{safe_y}') ~ C(Q('{safe_a}')) * C(Q('{safe_b}'))"
        model = ols(formula, data=formula_df).fit()
        anova_table = sm.stats.anova_lm(model, typ=2)

        results = {}
        for idx in anova_table.index:
            row = anova_table.loc[idx]
            key = str(idx).strip()
            results[key] = {
                "sum_sq": float(row.get("sum_sq", 0)),
                "df": float(row.get("df", 0)),
                "F": float(row.get("F", 0)) if not pd.isna(row.get("F")) else None,
                "PR(>F)": float(row.get("PR(>F)", 1)) if not pd.isna(row.get("PR(>F)")) else None,
            }

        summary = {"anova_table": results, "alpha": alpha}

        # Build interaction plot
        a_levels = sorted(clean[factor_a].astype(str).unique())
        b_levels = sorted(clean[factor_b].astype(str).unique())
        interaction_means: dict[str, list[float]] = {}
        for b_lvl in b_levels:
            means = []
            for a_lvl in a_levels:
                subset = clean[(clean[factor_a].astype(str) == a_lvl) & (clean[factor_b].astype(str) == b_lvl)]
                means.append(float(subset[y_col].astype(float).mean()) if len(subset) > 0 else 0)
            interaction_means[b_lvl] = means

        chart_list = [
            charts.interaction_plot(
                x_levels=a_levels,
                trace_levels=b_levels,
                means=interaction_means,
                title=f"Interaction: {factor_a} x {factor_b}",
                xaxis_title=factor_a,
                yaxis_title=f"Mean {y_col}",
                trace_name=factor_b,
            ),
        ]

        return AnalysisResult(
            test_type="two_way_anova",
            test_category="comparison",
            success=True,
            summary=summary,
            details={"y_column": y_col, "factor_a": factor_a, "factor_b": factor_b,
                     "anova_table": results, "model_r_squared": float(model.rsquared)},
            charts=chart_list,
            interpretation_context={
                "test_name": "Two-Way ANOVA",
                "y_column": y_col, "factor_a": factor_a, "factor_b": factor_b,
                "anova_results": results,
                "alpha": alpha,
            },
            warnings=warnings,
        )

    except Exception as e:
        return AnalysisResult(
            test_type="two_way_anova", test_category="comparison", success=False,
            summary={}, details={"error": str(e)},
            warnings=[f"Two-way ANOVA failed: {e}"],
        )


# ---------------------------------------------------------------------------
# Mann-Whitney U (non-parametric 2-sample)
# ---------------------------------------------------------------------------

def mann_whitney(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        y_column: str  — response variable
        x_column: str  — grouping variable (2 levels)
        alpha: float   — significance level (default: 0.05)
        alternative: str — "two-sided" | "less" | "greater"
    """
    y_col = config.get("y_column")
    x_col = config.get("x_column")
    alpha = config.get("alpha", 0.05)
    alternative = config.get("alternative", "two-sided")

    if not y_col or y_col not in df.columns:
        return AnalysisResult(test_type="mann_whitney", test_category="comparison", success=False,
                              summary={}, details={"error": f"Y column '{y_col}' not found"})
    if not x_col or x_col not in df.columns:
        return AnalysisResult(test_type="mann_whitney", test_category="comparison", success=False,
                              summary={}, details={"error": f"X column '{x_col}' not found"})

    clean = df[[y_col, x_col]].dropna()
    groups = clean[x_col].unique()
    if len(groups) != 2:
        return AnalysisResult(test_type="mann_whitney", test_category="comparison", success=False,
                              summary={}, details={"error": f"Expected 2 groups, found {len(groups)}"})

    g1 = clean[clean[x_col] == groups[0]][y_col].astype(float).values
    g2 = clean[clean[x_col] == groups[1]][y_col].astype(float).values

    if len(g1) < 1 or len(g2) < 1:
        return AnalysisResult(test_type="mann_whitney", test_category="comparison", success=False,
                              summary={}, details={"error": "Each group needs at least 1 observation"})

    u_stat, p_value = sp_stats.mannwhitneyu(g1, g2, alternative=alternative)

    # Rank-biserial correlation as effect size
    n1, n2 = len(g1), len(g2)
    r = 1 - (2 * float(u_stat)) / (n1 * n2)

    summary = {
        "statistic": float(u_stat),
        "p_value": float(p_value),
        "significant": float(p_value) < alpha,
        "group_1": str(groups[0]),
        "group_1_median": float(np.median(g1)),
        "group_1_n": n1,
        "group_2": str(groups[1]),
        "group_2_median": float(np.median(g2)),
        "group_2_n": n2,
        "rank_biserial_r": r,
    }

    chart_list = [
        charts.box_plot(
            {str(groups[0]): g1.tolist(), str(groups[1]): g2.tolist()},
            title=f"{y_col} by {x_col}", yaxis_title=y_col,
        ),
    ]

    return AnalysisResult(
        test_type="mann_whitney",
        test_category="comparison",
        success=True,
        summary=summary,
        details={"y_column": y_col, "x_column": x_col, "alpha": alpha, "alternative": alternative},
        charts=chart_list,
        interpretation_context={
            "test_name": "Mann-Whitney U Test",
            "y_column": y_col, "x_column": x_col,
            "medians": {str(groups[0]): float(np.median(g1)), str(groups[1]): float(np.median(g2))},
            "p_value": float(p_value),
            "significant": float(p_value) < alpha,
            "alpha": alpha,
        },
        warnings=[],
    )


# ---------------------------------------------------------------------------
# Kruskal-Wallis (non-parametric 3+ groups)
# ---------------------------------------------------------------------------

def kruskal_wallis(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        y_column: str  — response variable
        x_column: str  — grouping variable (3+ levels)
        alpha: float   — significance level (default: 0.05)
    """
    y_col = config.get("y_column")
    x_col = config.get("x_column")
    alpha = config.get("alpha", 0.05)

    if not y_col or y_col not in df.columns:
        return AnalysisResult(test_type="kruskal_wallis", test_category="comparison", success=False,
                              summary={}, details={"error": f"Y column '{y_col}' not found"})
    if not x_col or x_col not in df.columns:
        return AnalysisResult(test_type="kruskal_wallis", test_category="comparison", success=False,
                              summary={}, details={"error": f"X column '{x_col}' not found"})

    clean = df[[y_col, x_col]].dropna()
    groups_dict: dict[str, np.ndarray] = {}
    for name, group in clean.groupby(x_col):
        arr = group[y_col].astype(float).values
        if len(arr) >= 1:
            groups_dict[str(name)] = arr

    if len(groups_dict) < 2:
        return AnalysisResult(test_type="kruskal_wallis", test_category="comparison", success=False,
                              summary={}, details={"error": "Need at least 2 groups"})

    h_stat, p_value = sp_stats.kruskal(*groups_dict.values())

    # Effect size: epsilon-squared
    n_total = sum(len(g) for g in groups_dict.values())
    epsilon_sq = float((h_stat - len(groups_dict) + 1) / (n_total - len(groups_dict))) if n_total > len(groups_dict) else 0

    group_stats = {name: {"n": len(arr), "median": float(np.median(arr)), "mean_rank": 0}
                   for name, arr in groups_dict.items()}

    summary = {
        "statistic": float(h_stat),
        "p_value": float(p_value),
        "significant": float(p_value) < alpha,
        "group_count": len(groups_dict),
        "epsilon_squared": epsilon_sq,
    }

    chart_list = [
        charts.box_plot(
            {name: arr.tolist() for name, arr in groups_dict.items()},
            title=f"{y_col} by {x_col}", yaxis_title=y_col,
        ),
    ]

    return AnalysisResult(
        test_type="kruskal_wallis",
        test_category="comparison",
        success=True,
        summary=summary,
        details={"y_column": y_col, "x_column": x_col, "alpha": alpha, "group_stats": group_stats},
        charts=chart_list,
        interpretation_context={
            "test_name": "Kruskal-Wallis H Test",
            "y_column": y_col, "x_column": x_col,
            "group_count": len(groups_dict),
            "group_medians": {name: float(np.median(arr)) for name, arr in groups_dict.items()},
            "p_value": float(p_value),
            "significant": float(p_value) < alpha,
            "alpha": alpha,
        },
        warnings=[],
    )


# ---------------------------------------------------------------------------
# Chi-Square Test of Association
# ---------------------------------------------------------------------------

def chi_square_association(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        column_a: str  — first categorical variable
        column_b: str  — second categorical variable
        alpha: float   — significance level (default: 0.05)
    """
    col_a = config.get("column_a")
    col_b = config.get("column_b")
    alpha = config.get("alpha", 0.05)

    if not col_a or col_a not in df.columns:
        return AnalysisResult(test_type="chi_square_association", test_category="comparison", success=False,
                              summary={}, details={"error": f"Column '{col_a}' not found"})
    if not col_b or col_b not in df.columns:
        return AnalysisResult(test_type="chi_square_association", test_category="comparison", success=False,
                              summary={}, details={"error": f"Column '{col_b}' not found"})

    clean = df[[col_a, col_b]].dropna()
    contingency = pd.crosstab(clean[col_a], clean[col_b])
    warnings: list[str] = []

    if contingency.size == 0:
        return AnalysisResult(test_type="chi_square_association", test_category="comparison", success=False,
                              summary={}, details={"error": "Empty contingency table"})

    chi2, p_value, dof, expected = sp_stats.chi2_contingency(contingency)

    # Check expected frequency assumption
    low_expected = (expected < 5).sum()
    total_cells = expected.size
    if low_expected > 0:
        warnings.append(
            f"{low_expected} of {total_cells} cells ({low_expected / total_cells * 100:.0f}%) have expected "
            f"frequency < 5. Chi-square results may not be reliable."
        )

    # Cramér's V effect size
    n = contingency.values.sum()
    min_dim = min(contingency.shape[0] - 1, contingency.shape[1] - 1)
    cramers_v = np.sqrt(chi2 / (n * min_dim)) if n > 0 and min_dim > 0 else 0

    summary = {
        "statistic": float(chi2),
        "p_value": float(p_value),
        "significant": float(p_value) < alpha,
        "degrees_of_freedom": int(dof),
        "cramers_v": float(cramers_v),
        "n": int(n),
    }

    # Heatmap of observed counts
    chart_list = [
        charts.heatmap(
            matrix=contingency.values.tolist(),
            labels=contingency.columns.astype(str).tolist(),
            title=f"Contingency Table: {col_a} × {col_b}",
            colorscale="Blues",
        ),
    ]
    # Override heatmap z range for counts (not -1 to 1)
    chart_list[0].data[0]["zmin"] = 0
    chart_list[0].data[0]["zmax"] = int(contingency.values.max())
    chart_list[0].data[0].pop("colorbar", None)

    return AnalysisResult(
        test_type="chi_square_association",
        test_category="comparison",
        success=True,
        summary=summary,
        details={
            "column_a": col_a, "column_b": col_b, "alpha": alpha,
            "observed": contingency.values.tolist(),
            "expected": expected.tolist(),
            "row_labels": contingency.index.astype(str).tolist(),
            "col_labels": contingency.columns.astype(str).tolist(),
        },
        charts=chart_list,
        interpretation_context={
            "test_name": "Chi-Square Test of Association",
            "column_a": col_a, "column_b": col_b,
            "p_value": float(p_value),
            "significant": float(p_value) < alpha,
            "cramers_v": float(cramers_v),
            "alpha": alpha,
            "conclusion": (
                f"There IS a statistically significant association between {col_a} and {col_b}"
                if float(p_value) < alpha else
                f"No significant association found between {col_a} and {col_b}"
            ),
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Chi-Square Goodness of Fit
# ---------------------------------------------------------------------------

def chi_square_goodness(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        column: str              — categorical column to test
        expected_proportions: dict  — {category: proportion} (must sum to 1) or None for uniform
        alpha: float             — significance level (default: 0.05)
    """
    column = config.get("column")
    expected_props = config.get("expected_proportions")
    alpha = config.get("alpha", 0.05)

    if not column or column not in df.columns:
        return AnalysisResult(test_type="chi_square_goodness", test_category="comparison", success=False,
                              summary={}, details={"error": f"Column '{column}' not found"})

    observed_counts = df[column].value_counts()
    categories = observed_counts.index.astype(str).tolist()
    observed = observed_counts.values.tolist()
    n = sum(observed)
    warnings: list[str] = []

    if expected_props:
        expected = [expected_props.get(cat, 0) * n for cat in categories]
    else:
        # Uniform distribution
        expected = [n / len(categories)] * len(categories)

    low_expected = sum(1 for e in expected if e < 5)
    if low_expected > 0:
        warnings.append(f"{low_expected} categories have expected frequency < 5.")

    chi2, p_value = sp_stats.chisquare(observed, f_exp=expected)

    summary = {
        "statistic": float(chi2),
        "p_value": float(p_value),
        "significant": float(p_value) < alpha,
        "degrees_of_freedom": len(categories) - 1,
        "n": n,
    }

    chart_list = [
        charts.bar_chart(
            categories=categories,
            values=observed,
            title=f"Observed vs Expected — {column}",
            yaxis_title="Count",
        ),
    ]

    return AnalysisResult(
        test_type="chi_square_goodness",
        test_category="comparison",
        success=True,
        summary=summary,
        details={
            "column": column, "alpha": alpha,
            "categories": categories,
            "observed": observed,
            "expected": [round(e, 2) for e in expected],
        },
        charts=chart_list,
        interpretation_context={
            "test_name": "Chi-Square Goodness of Fit",
            "column": column,
            "p_value": float(p_value),
            "significant": float(p_value) < alpha,
            "alpha": alpha,
            "distribution_tested": "specified" if expected_props else "uniform",
        },
        warnings=warnings,
    )
