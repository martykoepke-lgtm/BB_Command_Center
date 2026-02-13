"""
Descriptive statistics, normality testing, and Pareto analysis.

Tests:
  - descriptive_summary: mean, median, mode, std, range, quartiles, skewness, kurtosis
  - normality_test: Shapiro-Wilk + Anderson-Darling with histogram and probability plot
  - pareto_analysis: Pareto chart with vital-few identification
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from app.stats import AnalysisResult, PlotlyChart
from app.stats import charts


# ---------------------------------------------------------------------------
# Descriptive Summary
# ---------------------------------------------------------------------------

def descriptive_summary(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Compute descriptive statistics for one or more columns.

    Config:
        columns: list[str]  — columns to analyze (default: all numeric)
    """
    columns = config.get("columns")
    if columns:
        numeric_df = df[columns].select_dtypes(include=["number"])
    else:
        numeric_df = df.select_dtypes(include=["number"])

    if numeric_df.empty:
        return AnalysisResult(
            test_type="descriptive_summary",
            test_category="descriptive",
            success=False,
            summary={},
            details={"error": "No numeric columns found"},
            warnings=["No numeric columns available for descriptive statistics"],
        )

    warnings: list[str] = []
    col_stats: dict[str, dict] = {}
    chart_list: list[PlotlyChart] = []

    for col in numeric_df.columns:
        series = numeric_df[col].dropna()
        n = len(series)

        if n == 0:
            warnings.append(f"Column '{col}' has no non-null values")
            continue

        arr = series.values.astype(float)
        q1, median, q3 = float(np.percentile(arr, 25)), float(np.median(arr)), float(np.percentile(arr, 75))

        stats_dict = {
            "n": n,
            "mean": float(np.mean(arr)),
            "median": median,
            "std": float(np.std(arr, ddof=1)) if n > 1 else 0.0,
            "variance": float(np.var(arr, ddof=1)) if n > 1 else 0.0,
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "range": float(np.max(arr) - np.min(arr)),
            "q1": q1,
            "q3": q3,
            "iqr": q3 - q1,
            "skewness": float(sp_stats.skew(arr, bias=False)) if n > 2 else None,
            "kurtosis": float(sp_stats.kurtosis(arr, bias=False)) if n > 3 else None,
            "null_count": int(df[col].isna().sum()),
            "null_pct": round(float(df[col].isna().sum()) / len(df) * 100, 2),
        }

        # Mode (may be multimodal)
        mode_result = sp_stats.mode(arr, keepdims=True)
        stats_dict["mode"] = float(mode_result.mode[0]) if len(mode_result.mode) > 0 else None
        stats_dict["mode_count"] = int(mode_result.count[0]) if len(mode_result.count) > 0 else 0

        # Coefficient of variation
        if stats_dict["mean"] != 0:
            stats_dict["cv"] = round(stats_dict["std"] / abs(stats_dict["mean"]) * 100, 2)

        col_stats[col] = stats_dict

        # Generate histogram
        chart_list.append(charts.histogram(
            values=arr.tolist(),
            name=col,
            title=f"Distribution of {col}",
            xaxis_title=col,
            show_normal_curve=True,
        ))

    # Summary: if single column, surface key stats at top level
    summary = col_stats if len(col_stats) > 1 else (list(col_stats.values())[0] if col_stats else {})

    return AnalysisResult(
        test_type="descriptive_summary",
        test_category="descriptive",
        success=True,
        summary=summary,
        details={"columns": col_stats},
        charts=chart_list,
        interpretation_context={
            "column_count": len(col_stats),
            "columns_analyzed": list(col_stats.keys()),
            "sample_sizes": {col: s["n"] for col, s in col_stats.items()},
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Normality Test
# ---------------------------------------------------------------------------

def normality_test(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Test normality using Shapiro-Wilk and Anderson-Darling.

    Config:
        column: str         — column to test
        alpha: float        — significance level (default: 0.05)
    """
    column = config.get("column")
    alpha = config.get("alpha", 0.05)

    if not column or column not in df.columns:
        return AnalysisResult(
            test_type="normality_test",
            test_category="descriptive",
            success=False,
            summary={},
            details={"error": f"Column '{column}' not found"},
            warnings=[f"Column '{column}' does not exist in the dataset"],
        )

    series = df[column].dropna()
    arr = series.values.astype(float)
    n = len(arr)
    warnings: list[str] = []

    if n < 3:
        return AnalysisResult(
            test_type="normality_test",
            test_category="descriptive",
            success=False,
            summary={},
            details={"error": "Need at least 3 observations"},
            warnings=["Normality test requires at least 3 non-null observations"],
        )

    if n > 5000:
        warnings.append(
            f"Sample size ({n}) exceeds 5000. Shapiro-Wilk may be overly sensitive. "
            "Consider visual assessment (histogram, Q-Q plot) alongside the p-value."
        )

    # Shapiro-Wilk
    shapiro_stat, shapiro_p = sp_stats.shapiro(arr)

    # Anderson-Darling
    ad_result = sp_stats.anderson(arr, dist="norm")
    # Find the critical value for the closest significance level
    ad_significant = False
    ad_critical = None
    ad_sig_level = None
    for cv, sl in zip(ad_result.critical_values, ad_result.significance_level):
        if sl / 100 <= alpha:
            ad_critical = float(cv)
            ad_sig_level = float(sl)
            ad_significant = ad_result.statistic > cv
            break

    is_normal = shapiro_p >= alpha
    shapiro_p_float = float(shapiro_p)

    summary = {
        "is_normal": is_normal,
        "shapiro_wilk_statistic": float(shapiro_stat),
        "shapiro_wilk_p_value": shapiro_p_float,
        "anderson_darling_statistic": float(ad_result.statistic),
        "anderson_darling_critical_value": ad_critical,
        "anderson_darling_significant": ad_significant,
        "alpha": alpha,
        "n": n,
    }

    details = {
        "column": column,
        "shapiro_wilk": {"statistic": float(shapiro_stat), "p_value": shapiro_p_float},
        "anderson_darling": {
            "statistic": float(ad_result.statistic),
            "critical_values": [float(cv) for cv in ad_result.critical_values],
            "significance_levels": [float(sl) for sl in ad_result.significance_level],
        },
        "descriptive": {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr, ddof=1)),
            "skewness": float(sp_stats.skew(arr, bias=False)),
            "kurtosis": float(sp_stats.kurtosis(arr, bias=False)),
        },
    }

    # Charts
    chart_list = [
        charts.histogram(
            values=arr.tolist(),
            name=column,
            title=f"Distribution of {column}",
            xaxis_title=column,
            show_normal_curve=True,
        ),
        charts.probability_plot(
            values=arr.tolist(),
            title=f"Normal Probability Plot — {column}",
        ),
    ]

    conclusion = "normal" if is_normal else "not normal"
    interpretation_context = {
        "column": column,
        "conclusion": conclusion,
        "p_value": shapiro_p_float,
        "alpha": alpha,
        "sample_size": n,
        "skewness": details["descriptive"]["skewness"],
        "kurtosis": details["descriptive"]["kurtosis"],
        "recommendation": (
            "Data appears normally distributed. Parametric tests (t-test, ANOVA) are appropriate."
            if is_normal else
            "Data does NOT appear normally distributed. Consider non-parametric alternatives "
            "(Mann-Whitney, Kruskal-Wallis) or data transformations."
        ),
    }

    return AnalysisResult(
        test_type="normality_test",
        test_category="descriptive",
        success=True,
        summary=summary,
        details=details,
        charts=chart_list,
        interpretation_context=interpretation_context,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Pareto Analysis
# ---------------------------------------------------------------------------

def pareto_analysis(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Pareto analysis — identify the vital few categories.

    Config:
        category_column: str  — column with categories
        value_column: str     — column with counts/values (optional; if omitted, counts occurrences)
        top_n: int            — number of categories to show (default: all)
    """
    category_col = config.get("category_column")
    value_col = config.get("value_column")
    top_n = config.get("top_n")

    if not category_col or category_col not in df.columns:
        return AnalysisResult(
            test_type="pareto_analysis",
            test_category="descriptive",
            success=False,
            summary={},
            details={"error": f"Category column '{category_col}' not found"},
            warnings=[f"Column '{category_col}' does not exist in the dataset"],
        )

    warnings: list[str] = []

    if value_col and value_col in df.columns:
        grouped = df.groupby(category_col)[value_col].sum().sort_values(ascending=False)
    else:
        grouped = df[category_col].value_counts().sort_values(ascending=False)

    if top_n:
        grouped = grouped.head(top_n)

    categories = grouped.index.astype(str).tolist()
    values = grouped.values.tolist()
    total = sum(values) if values else 1

    # Cumulative percentages
    cumulative = []
    running = 0.0
    for v in values:
        running += v
        cumulative.append(round(running / total * 100, 2))

    # Identify vital few (categories that make up ~80%)
    vital_few = []
    for cat, cum_pct in zip(categories, cumulative):
        vital_few.append(cat)
        if cum_pct >= 80:
            break

    summary = {
        "total": total,
        "category_count": len(categories),
        "vital_few_count": len(vital_few),
        "vital_few_pct": cumulative[len(vital_few) - 1] if vital_few else 0,
        "vital_few": vital_few,
    }

    details = {
        "categories": categories,
        "values": values,
        "percentages": [round(v / total * 100, 2) for v in values],
        "cumulative_percentages": cumulative,
        "vital_few": vital_few,
        "trivial_many": [c for c in categories if c not in vital_few],
    }

    chart_list = [
        charts.pareto_chart(
            categories=categories,
            values=values,
            title=f"Pareto Analysis — {category_col}",
            yaxis_title=value_col or "Count",
        ),
    ]

    interpretation_context = {
        "category_column": category_col,
        "total": total,
        "vital_few": vital_few,
        "vital_few_pct": summary["vital_few_pct"],
        "top_category": categories[0] if categories else None,
        "top_category_pct": round(values[0] / total * 100, 2) if values else 0,
        "recommendation": (
            f"Focus on the vital few: {', '.join(vital_few)}. "
            f"These {len(vital_few)} categories account for {summary['vital_few_pct']:.1f}% of the total."
        ),
    }

    return AnalysisResult(
        test_type="pareto_analysis",
        test_category="descriptive",
        success=True,
        summary=summary,
        details=details,
        charts=chart_list,
        interpretation_context=interpretation_context,
        warnings=warnings,
    )
