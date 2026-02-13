"""
Programmatic statistical validation engine.

Layer 1 of the dual-layer validation system. Runs deterministic checks
on every statistical test — no AI calls, no cost, no latency.

Checks three dimensions:
  1. Input validation — sample size, data types, required columns, config completeness
  2. Output validation — p-value range, finite statistics, CI ordering, expected keys
  3. Assumption validation — normality, equal variance, independence, chi-square minimums

Returns a ValidationReport that feeds into Layer 2 (AI Validator Agent) and
is stored in the analysis results for user-facing display.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from scipy import stats as scipy_stats

from app.stats import AnalysisResult


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class FindingCategory(str, Enum):
    SAMPLE_SIZE = "sample_size"
    DATA_TYPE = "data_type"
    MISSING_DATA = "missing_data"
    CONFIGURATION = "configuration"
    ASSUMPTION = "assumption"
    OUTPUT_RANGE = "output_range"
    STATISTICAL = "statistical"


class ValidationFinding(BaseModel):
    """A single validation finding."""
    severity: Severity
    category: FindingCategory
    message: str
    detail: str = ""


class ValidationReport(BaseModel):
    """Result of programmatic validation."""
    passed: bool
    confidence: str = "high"  # "high", "medium", "low"
    findings: list[ValidationFinding] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "confidence": self.confidence,
            "findings": [f.model_dump() for f in self.findings],
            "recommendations": self.recommendations,
        }


# ---------------------------------------------------------------------------
# Test requirements lookup
# ---------------------------------------------------------------------------

_TEST_REQUIREMENTS: dict[str, dict[str, Any]] = {
    # Descriptive
    "descriptive_summary": {
        "min_samples": 1,
        "requires_numeric": True,
        "required_config": ["column"],
    },
    "normality_test": {
        "min_samples": 8,
        "requires_numeric": True,
        "required_config": ["column"],
    },
    "pareto_analysis": {
        "min_samples": 2,
        "requires_numeric": False,
        "required_config": ["category_column"],
    },
    # Comparison — parametric
    "one_sample_t": {
        "min_samples": 5,
        "requires_numeric": True,
        "required_config": ["column", "hypothesized_mean"],
        "assumes_normality": True,
    },
    "two_sample_t": {
        "min_samples": 5,
        "min_per_group": 3,
        "requires_numeric": True,
        "required_config": ["column", "group_column"],
        "assumes_normality": True,
        "assumes_equal_variance": True,
    },
    "paired_t": {
        "min_samples": 5,
        "requires_numeric": True,
        "required_config": ["column1", "column2"],
        "assumes_normality": True,
    },
    "one_way_anova": {
        "min_samples": 10,
        "min_per_group": 3,
        "requires_numeric": True,
        "required_config": ["column", "group_column"],
        "assumes_normality": True,
        "assumes_equal_variance": True,
    },
    "two_way_anova": {
        "min_samples": 12,
        "min_per_group": 2,
        "requires_numeric": True,
        "required_config": ["column", "factor1", "factor2"],
        "assumes_normality": True,
        "assumes_equal_variance": True,
    },
    # Comparison — nonparametric
    "mann_whitney": {
        "min_samples": 5,
        "min_per_group": 3,
        "requires_numeric": True,
        "required_config": ["column", "group_column"],
    },
    "kruskal_wallis": {
        "min_samples": 10,
        "min_per_group": 3,
        "requires_numeric": True,
        "required_config": ["column", "group_column"],
    },
    # Comparison — categorical
    "chi_square_association": {
        "min_samples": 20,
        "requires_numeric": False,
        "required_config": ["column1", "column2"],
        "assumes_expected_counts": True,
    },
    "chi_square_goodness": {
        "min_samples": 20,
        "requires_numeric": False,
        "required_config": ["column"],
    },
    # Regression
    "correlation": {
        "min_samples": 10,
        "requires_numeric": True,
        "required_config": ["columns"],
    },
    "simple_regression": {
        "min_samples": 10,
        "requires_numeric": True,
        "required_config": ["x_column", "y_column"],
        "assumes_normality": True,
    },
    "multiple_regression": {
        "min_samples": 20,
        "requires_numeric": True,
        "required_config": ["x_columns", "y_column"],
        "assumes_normality": True,
        "checks_multicollinearity": True,
    },
    "logistic_regression": {
        "min_samples": 30,
        "requires_numeric": False,
        "required_config": ["x_columns", "y_column"],
    },
    # SPC
    "i_mr_chart": {
        "min_samples": 20,
        "requires_numeric": True,
        "required_config": ["column"],
    },
    "xbar_r_chart": {
        "min_samples": 20,
        "requires_numeric": True,
        "required_config": ["column"],
    },
    "p_chart": {
        "min_samples": 20,
        "requires_numeric": True,
        "required_config": ["defective_column", "sample_size_column"],
    },
    "np_chart": {
        "min_samples": 20,
        "requires_numeric": True,
        "required_config": ["defective_column"],
    },
    "c_chart": {
        "min_samples": 20,
        "requires_numeric": True,
        "required_config": ["column"],
    },
    "u_chart": {
        "min_samples": 20,
        "requires_numeric": True,
        "required_config": ["defect_column", "unit_column"],
    },
    # Capability
    "capability_normal": {
        "min_samples": 30,
        "requires_numeric": True,
        "required_config": ["column", "lsl", "usl"],
        "assumes_normality": True,
    },
    "capability_nonnormal": {
        "min_samples": 30,
        "requires_numeric": True,
        "required_config": ["column", "lsl", "usl"],
    },
    "msa_gage_rr": {
        "min_samples": 10,
        "requires_numeric": True,
        "required_config": ["measurement_column", "operator_column", "part_column"],
    },
    # DOE
    "full_factorial": {
        "min_samples": 4,
        "requires_numeric": False,
        "required_config": ["factors"],
    },
    "fractional_factorial": {
        "min_samples": 4,
        "requires_numeric": False,
        "required_config": ["factors"],
    },
    "doe_analysis": {
        "min_samples": 8,
        "requires_numeric": True,
        "required_config": ["response_column", "factor_columns"],
    },
}


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def validate_inputs(
    test_type: str,
    configuration: dict,
    dataset_summary: dict | None,
    df: pd.DataFrame | None = None,
) -> ValidationReport:
    """Validate test inputs before/after execution."""
    findings: list[ValidationFinding] = []
    recommendations: list[str] = []

    reqs = _TEST_REQUIREMENTS.get(test_type)
    if reqs is None:
        findings.append(ValidationFinding(
            severity=Severity.WARNING,
            category=FindingCategory.CONFIGURATION,
            message=f"Unknown test type '{test_type}' — cannot validate requirements",
        ))
        return ValidationReport(passed=True, confidence="low", findings=findings)

    # --- Configuration completeness ---
    required_config = reqs.get("required_config", [])
    for key in required_config:
        if key not in configuration:
            findings.append(ValidationFinding(
                severity=Severity.ERROR,
                category=FindingCategory.CONFIGURATION,
                message=f"Missing required configuration parameter: '{key}'",
                detail=f"Test '{test_type}' requires '{key}' in its configuration.",
            ))

    # --- Sample size ---
    row_count = 0
    if df is not None and not df.empty:
        row_count = len(df)
    elif dataset_summary and dataset_summary.get("row_count"):
        row_count = dataset_summary["row_count"]

    min_samples = reqs.get("min_samples", 1)
    if row_count > 0 and row_count < min_samples:
        findings.append(ValidationFinding(
            severity=Severity.ERROR,
            category=FindingCategory.SAMPLE_SIZE,
            message=f"Insufficient sample size: {row_count} rows (minimum {min_samples} required)",
            detail=f"Test '{test_type}' needs at least {min_samples} observations for reliable results.",
        ))
        recommendations.append(f"Collect at least {min_samples} observations before running this test.")
    elif row_count > 0 and row_count < min_samples * 2:
        findings.append(ValidationFinding(
            severity=Severity.WARNING,
            category=FindingCategory.SAMPLE_SIZE,
            message=f"Small sample size: {row_count} rows (minimum {min_samples}, recommended {min_samples * 2}+)",
            detail="Results may have low statistical power. Consider collecting more data.",
        ))

    # --- Group sizes for comparison tests ---
    min_per_group = reqs.get("min_per_group")
    if min_per_group and df is not None and not df.empty:
        group_col = configuration.get("group_column")
        if group_col and group_col in df.columns:
            group_sizes = df[group_col].value_counts()
            small_groups = group_sizes[group_sizes < min_per_group]
            if len(small_groups) > 0:
                findings.append(ValidationFinding(
                    severity=Severity.ERROR,
                    category=FindingCategory.SAMPLE_SIZE,
                    message=f"Group(s) too small: {dict(small_groups)} (minimum {min_per_group} per group)",
                    detail="Small groups reduce statistical power and may invalidate test assumptions.",
                ))

    # --- Data types ---
    if df is not None and not df.empty and reqs.get("requires_numeric"):
        # Check the primary analysis column(s) for numeric type
        columns_to_check = []
        for key in ["column", "column1", "column2", "y_column", "x_column",
                     "measurement_column", "response_column"]:
            col = configuration.get(key)
            if col and col in df.columns:
                columns_to_check.append(col)

        cols_list = configuration.get("columns") or configuration.get("x_columns")
        if isinstance(cols_list, list):
            for col in cols_list:
                if col in df.columns:
                    columns_to_check.append(col)

        for col in columns_to_check:
            if not pd.api.types.is_numeric_dtype(df[col]):
                findings.append(ValidationFinding(
                    severity=Severity.ERROR,
                    category=FindingCategory.DATA_TYPE,
                    message=f"Column '{col}' is not numeric (dtype: {df[col].dtype})",
                    detail=f"This test requires numeric data. Convert or choose a different column.",
                ))

    # --- Missing data ---
    if df is not None and not df.empty:
        total_missing = df.isnull().sum().sum()
        total_cells = df.size
        if total_cells > 0:
            missing_pct = (total_missing / total_cells) * 100
            if missing_pct > 20:
                findings.append(ValidationFinding(
                    severity=Severity.ERROR,
                    category=FindingCategory.MISSING_DATA,
                    message=f"High missing data rate: {missing_pct:.1f}% of values are missing",
                    detail="Results may be unreliable. Consider imputation or data cleaning.",
                ))
                recommendations.append("Address missing data before running analysis.")
            elif missing_pct > 5:
                findings.append(ValidationFinding(
                    severity=Severity.WARNING,
                    category=FindingCategory.MISSING_DATA,
                    message=f"Notable missing data: {missing_pct:.1f}% of values are missing",
                    detail="Check if missingness is random or systematic.",
                ))

    # --- Determine pass/fail ---
    has_errors = any(f.severity == Severity.ERROR for f in findings)
    has_warnings = any(f.severity == Severity.WARNING for f in findings)

    if has_errors:
        confidence = "low"
    elif has_warnings:
        confidence = "medium"
    else:
        confidence = "high"

    return ValidationReport(
        passed=not has_errors,
        confidence=confidence,
        findings=findings,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------

def validate_outputs(test_type: str, result: AnalysisResult) -> ValidationReport:
    """Validate statistical test outputs for sanity."""
    findings: list[ValidationFinding] = []
    recommendations: list[str] = []

    summary = result.summary
    details = result.details

    # --- p-value range ---
    p_value = summary.get("p_value")
    if p_value is not None:
        if not isinstance(p_value, (int, float)):
            findings.append(ValidationFinding(
                severity=Severity.ERROR,
                category=FindingCategory.OUTPUT_RANGE,
                message=f"p-value is not numeric: {p_value}",
            ))
        elif math.isnan(p_value) or math.isinf(p_value):
            findings.append(ValidationFinding(
                severity=Severity.ERROR,
                category=FindingCategory.OUTPUT_RANGE,
                message="p-value is NaN or infinite — computation likely failed",
            ))
        elif p_value < 0 or p_value > 1:
            findings.append(ValidationFinding(
                severity=Severity.ERROR,
                category=FindingCategory.OUTPUT_RANGE,
                message=f"p-value out of range: {p_value} (must be 0-1)",
            ))

    # --- Test statistic finiteness ---
    for stat_key in ["statistic", "test_statistic", "f_statistic", "t_statistic",
                     "chi2_statistic", "u_statistic", "h_statistic"]:
        stat_val = summary.get(stat_key)
        if stat_val is not None and isinstance(stat_val, (int, float)):
            if math.isnan(stat_val) or math.isinf(stat_val):
                findings.append(ValidationFinding(
                    severity=Severity.ERROR,
                    category=FindingCategory.OUTPUT_RANGE,
                    message=f"Test statistic '{stat_key}' is NaN or infinite",
                    detail="This typically indicates a degenerate dataset (zero variance, identical groups, etc.).",
                ))

    # --- Effect size bounds ---
    effect_size = summary.get("effect_size")
    if effect_size is not None and isinstance(effect_size, (int, float)):
        if math.isnan(effect_size) or math.isinf(effect_size):
            findings.append(ValidationFinding(
                severity=Severity.WARNING,
                category=FindingCategory.OUTPUT_RANGE,
                message="Effect size is NaN or infinite",
            ))
        elif abs(effect_size) > 10:
            findings.append(ValidationFinding(
                severity=Severity.WARNING,
                category=FindingCategory.STATISTICAL,
                message=f"Unusually large effect size: {effect_size:.2f}",
                detail="Effect sizes > 2.0 are rare in practice. Verify the data is correct.",
            ))

    # --- R-squared bounds ---
    r_squared = summary.get("r_squared") or details.get("r_squared")
    if r_squared is not None and isinstance(r_squared, (int, float)):
        if r_squared < 0 or r_squared > 1:
            findings.append(ValidationFinding(
                severity=Severity.ERROR,
                category=FindingCategory.OUTPUT_RANGE,
                message=f"R-squared out of range: {r_squared} (must be 0-1)",
            ))

    # --- Degrees of freedom ---
    for df_key in ["df", "degrees_of_freedom", "df_between", "df_within"]:
        df_val = summary.get(df_key) or details.get(df_key)
        if df_val is not None and isinstance(df_val, (int, float)):
            if df_val <= 0:
                findings.append(ValidationFinding(
                    severity=Severity.ERROR,
                    category=FindingCategory.OUTPUT_RANGE,
                    message=f"Degrees of freedom '{df_key}' <= 0: {df_val}",
                    detail="Indicates insufficient data for this test.",
                ))

    # --- Confidence intervals ---
    ci_lower = summary.get("ci_lower") or details.get("ci_lower")
    ci_upper = summary.get("ci_upper") or details.get("ci_upper")
    if ci_lower is not None and ci_upper is not None:
        if isinstance(ci_lower, (int, float)) and isinstance(ci_upper, (int, float)):
            if ci_lower > ci_upper:
                findings.append(ValidationFinding(
                    severity=Severity.ERROR,
                    category=FindingCategory.OUTPUT_RANGE,
                    message=f"Confidence interval inverted: [{ci_lower}, {ci_upper}]",
                ))

    # --- Charts present when expected ---
    chart_tests = {"descriptive_summary", "normality_test", "pareto_analysis",
                   "i_mr_chart", "xbar_r_chart", "p_chart", "np_chart", "c_chart", "u_chart",
                   "capability_normal", "capability_nonnormal", "simple_regression",
                   "correlation", "doe_analysis"}
    if test_type in chart_tests and result.success and not result.charts:
        findings.append(ValidationFinding(
            severity=Severity.WARNING,
            category=FindingCategory.OUTPUT_RANGE,
            message="No charts generated for a test that typically produces visualizations",
            detail="Charts help interpret results. This may indicate a rendering issue.",
        ))

    # --- Warnings from the test itself ---
    if result.warnings:
        for w in result.warnings:
            findings.append(ValidationFinding(
                severity=Severity.WARNING,
                category=FindingCategory.STATISTICAL,
                message=f"Test warning: {w}",
            ))

    # --- Determine pass/fail ---
    has_errors = any(f.severity == Severity.ERROR for f in findings)
    has_warnings = any(f.severity == Severity.WARNING for f in findings)

    if has_errors:
        confidence = "low"
    elif has_warnings:
        confidence = "medium"
    else:
        confidence = "high"

    return ValidationReport(
        passed=not has_errors,
        confidence=confidence,
        findings=findings,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Assumption validation
# ---------------------------------------------------------------------------

def validate_assumptions(
    test_type: str,
    df: pd.DataFrame | None,
    configuration: dict,
) -> ValidationReport:
    """Check statistical assumptions for the given test type."""
    findings: list[ValidationFinding] = []
    recommendations: list[str] = []

    if df is None or df.empty:
        return ValidationReport(passed=True, confidence="medium", findings=[
            ValidationFinding(
                severity=Severity.WARNING,
                category=FindingCategory.ASSUMPTION,
                message="No data available to check assumptions",
            )
        ])

    reqs = _TEST_REQUIREMENTS.get(test_type, {})

    # --- Normality check for parametric tests ---
    if reqs.get("assumes_normality"):
        column = configuration.get("column") or configuration.get("y_column")
        columns_to_check = []
        if column and column in df.columns:
            columns_to_check.append(column)
        for key in ["column1", "column2"]:
            col = configuration.get(key)
            if col and col in df.columns:
                columns_to_check.append(col)

        for col in columns_to_check:
            data = df[col].dropna()
            if len(data) >= 8 and pd.api.types.is_numeric_dtype(data):
                try:
                    if len(data) <= 5000:
                        stat, p = scipy_stats.shapiro(data)
                    else:
                        stat, p = scipy_stats.normaltest(data)

                    if p < 0.05:
                        findings.append(ValidationFinding(
                            severity=Severity.WARNING,
                            category=FindingCategory.ASSUMPTION,
                            message=f"Normality assumption may be violated for '{col}' (p={p:.4f})",
                            detail="The Shapiro-Wilk test suggests the data is not normally distributed. "
                                   "Consider a non-parametric alternative.",
                        ))
                        # Suggest alternatives
                        alt_map = {
                            "two_sample_t": "mann_whitney",
                            "one_way_anova": "kruskal_wallis",
                            "paired_t": "Wilcoxon signed-rank test",
                        }
                        alt = alt_map.get(test_type)
                        if alt:
                            recommendations.append(
                                f"Consider using '{alt}' instead — it does not require normality."
                            )
                except Exception:
                    pass  # Normality check is advisory, not blocking

    # --- Equal variance for comparison tests ---
    if reqs.get("assumes_equal_variance"):
        column = configuration.get("column") or configuration.get("y_column")
        group_col = configuration.get("group_column")
        if column and group_col and column in df.columns and group_col in df.columns:
            groups = [g[column].dropna().values for _, g in df.groupby(group_col)
                      if len(g[column].dropna()) >= 2]
            if len(groups) >= 2:
                try:
                    stat, p = scipy_stats.levene(*groups)
                    if p < 0.05:
                        findings.append(ValidationFinding(
                            severity=Severity.WARNING,
                            category=FindingCategory.ASSUMPTION,
                            message=f"Equal variance assumption may be violated (Levene's p={p:.4f})",
                            detail="Group variances appear unequal. The test implementation should "
                                   "use Welch's correction automatically.",
                        ))
                except Exception:
                    pass

    # --- Chi-square expected counts ---
    if reqs.get("assumes_expected_counts"):
        col1 = configuration.get("column1")
        col2 = configuration.get("column2")
        if col1 and col2 and col1 in df.columns and col2 in df.columns:
            try:
                ct = pd.crosstab(df[col1], df[col2])
                # Expected frequencies
                row_totals = ct.sum(axis=1).values
                col_totals = ct.sum(axis=0).values
                total = ct.values.sum()
                expected = np.outer(row_totals, col_totals) / total
                low_count = (expected < 5).sum()
                pct_low = (low_count / expected.size) * 100
                if pct_low > 20:
                    findings.append(ValidationFinding(
                        severity=Severity.WARNING,
                        category=FindingCategory.ASSUMPTION,
                        message=f"{pct_low:.0f}% of expected cell counts are < 5",
                        detail="Chi-square test may not be valid. Consider Fisher's exact test "
                               "or combining categories.",
                    ))
                    recommendations.append("Combine small categories or use Fisher's exact test.")
            except Exception:
                pass

    # --- Multicollinearity for multiple regression ---
    if reqs.get("checks_multicollinearity"):
        x_cols = configuration.get("x_columns", [])
        valid_cols = [c for c in x_cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        if len(valid_cols) >= 2:
            try:
                from statsmodels.stats.outliers_influence import variance_inflation_factor
                X = df[valid_cols].dropna()
                if len(X) > len(valid_cols) + 1:
                    X_with_const = X.copy()
                    X_with_const["_const"] = 1
                    for i, col in enumerate(valid_cols):
                        vif = variance_inflation_factor(X_with_const.values, i)
                        if vif > 10:
                            findings.append(ValidationFinding(
                                severity=Severity.WARNING,
                                category=FindingCategory.ASSUMPTION,
                                message=f"High multicollinearity: VIF={vif:.1f} for '{col}'",
                                detail="VIF > 10 suggests strong multicollinearity. Consider removing "
                                       "correlated predictors.",
                            ))
            except Exception:
                pass

    # --- Determine pass/fail ---
    has_errors = any(f.severity == Severity.ERROR for f in findings)
    has_warnings = any(f.severity == Severity.WARNING for f in findings)

    if has_errors:
        confidence = "low"
    elif has_warnings:
        confidence = "medium"
    else:
        confidence = "high"

    return ValidationReport(
        passed=not has_errors,
        confidence=confidence,
        findings=findings,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Full validation orchestrator
# ---------------------------------------------------------------------------

_CONFIDENCE_PRIORITY = {"low": 0, "medium": 1, "high": 2}


def run_full_validation(
    test_type: str,
    configuration: dict,
    dataset_summary: dict | None,
    result: AnalysisResult,
    df: pd.DataFrame | None = None,
) -> ValidationReport:
    """
    Run all three validation layers and merge into a single report.

    Called by the stats engine after test execution completes.
    """
    # Layer 1a: Input checks
    input_report = validate_inputs(test_type, configuration, dataset_summary, df)

    # Layer 1b: Output checks
    output_report = validate_outputs(test_type, result)

    # Layer 1c: Assumption checks
    assumption_report = validate_assumptions(test_type, df, configuration)

    # Merge all findings
    all_findings = input_report.findings + output_report.findings + assumption_report.findings
    all_recommendations = list(dict.fromkeys(  # deduplicate preserving order
        input_report.recommendations + output_report.recommendations + assumption_report.recommendations
    ))

    # Overall confidence = lowest of the three
    confidences = [input_report.confidence, output_report.confidence, assumption_report.confidence]
    overall_confidence = min(confidences, key=lambda c: _CONFIDENCE_PRIORITY.get(c, 2))

    # Passed = all three passed
    overall_passed = input_report.passed and output_report.passed and assumption_report.passed

    return ValidationReport(
        passed=overall_passed,
        confidence=overall_confidence,
        findings=all_findings,
        recommendations=all_recommendations,
    )
