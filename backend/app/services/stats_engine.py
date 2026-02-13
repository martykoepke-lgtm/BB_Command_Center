"""
Statistical Engine Service — orchestrates test execution, routing, and result handling.

This is the single entry point for running any statistical test. It:
1. Validates the test type and configuration
2. Routes to the correct test implementation module
3. Handles errors and timing
4. Returns a standardized AnalysisResult

Usage:
    from app.services.stats_engine import StatsEngine
    engine = StatsEngine()
    result = engine.run_test("two_sample_t", df, {"y_column": "wait_time", "x_column": "shift"})
"""

from __future__ import annotations

import time
from typing import Callable

import pandas as pd

from app.stats import AnalysisResult
from app.stats import descriptive, comparison, regression, spc, capability, doe


# ---------------------------------------------------------------------------
# Test Registry — maps test_type string to (function, category)
# ---------------------------------------------------------------------------

TestFunction = Callable[[pd.DataFrame, dict], AnalysisResult]

_TEST_REGISTRY: dict[str, tuple[TestFunction, str]] = {
    # Descriptive
    "descriptive_summary": (descriptive.descriptive_summary, "descriptive"),
    "normality_test": (descriptive.normality_test, "descriptive"),
    "pareto_analysis": (descriptive.pareto_analysis, "descriptive"),

    # Comparison
    "one_sample_t": (comparison.one_sample_t, "comparison"),
    "two_sample_t": (comparison.two_sample_t, "comparison"),
    "paired_t": (comparison.paired_t, "comparison"),
    "one_way_anova": (comparison.one_way_anova, "comparison"),
    "two_way_anova": (comparison.two_way_anova, "comparison"),
    "mann_whitney": (comparison.mann_whitney, "comparison"),
    "kruskal_wallis": (comparison.kruskal_wallis, "comparison"),
    "chi_square_association": (comparison.chi_square_association, "comparison"),
    "chi_square_goodness": (comparison.chi_square_goodness, "comparison"),

    # Correlation & Regression
    "correlation": (regression.correlation, "correlation"),
    "simple_regression": (regression.simple_regression, "regression"),
    "multiple_regression": (regression.multiple_regression, "regression"),
    "logistic_regression": (regression.logistic_regression, "regression"),

    # SPC
    "i_mr_chart": (spc.i_mr_chart, "spc"),
    "xbar_r_chart": (spc.xbar_r_chart, "spc"),
    "p_chart": (spc.p_chart, "spc"),
    "np_chart": (spc.np_chart, "spc"),
    "c_chart": (spc.c_chart, "spc"),
    "u_chart": (spc.u_chart, "spc"),

    # Capability
    "capability_normal": (capability.capability_normal, "capability"),
    "capability_nonnormal": (capability.capability_nonnormal, "capability"),
    "msa_gage_rr": (capability.msa_gage_rr, "capability"),

    # DOE
    "full_factorial": (doe.full_factorial, "doe"),
    "fractional_factorial": (doe.fractional_factorial, "doe"),
    "doe_analysis": (doe.doe_analysis, "doe"),
}


# ---------------------------------------------------------------------------
# Test metadata — describes each test for the Stats Advisor agent
# ---------------------------------------------------------------------------

TEST_CATALOG: dict[str, dict] = {
    # Descriptive
    "descriptive_summary": {
        "name": "Descriptive Statistics",
        "category": "descriptive",
        "description": "Mean, median, mode, std dev, range, quartiles, skewness, kurtosis",
        "y_type": "continuous",
        "x_type": None,
        "min_samples": 1,
        "required_config": [],
        "optional_config": ["columns"],
    },
    "normality_test": {
        "name": "Normality Test",
        "category": "descriptive",
        "description": "Shapiro-Wilk and Anderson-Darling tests with histogram and Q-Q plot",
        "y_type": "continuous",
        "x_type": None,
        "min_samples": 3,
        "required_config": ["column"],
        "optional_config": ["alpha"],
    },
    "pareto_analysis": {
        "name": "Pareto Analysis",
        "category": "descriptive",
        "description": "Pareto chart with vital-few identification (80/20 rule)",
        "y_type": "categorical",
        "x_type": None,
        "min_samples": 1,
        "required_config": ["category_column"],
        "optional_config": ["value_column", "top_n"],
    },

    # Comparison
    "one_sample_t": {
        "name": "One-Sample t-Test",
        "category": "comparison",
        "description": "Compare sample mean to a known/target value",
        "y_type": "continuous",
        "x_type": None,
        "min_samples": 2,
        "required_config": ["column", "population_mean"],
        "optional_config": ["alpha", "alternative"],
    },
    "two_sample_t": {
        "name": "Two-Sample t-Test",
        "category": "comparison",
        "description": "Compare means of two independent groups",
        "y_type": "continuous",
        "x_type": "categorical (2 levels)",
        "min_samples": 4,
        "required_config": ["y_column", "x_column"],
        "optional_config": ["alpha", "equal_var", "alternative"],
    },
    "paired_t": {
        "name": "Paired t-Test",
        "category": "comparison",
        "description": "Compare before/after measurements on the same subjects",
        "y_type": "continuous",
        "x_type": "paired",
        "min_samples": 2,
        "required_config": ["column_before", "column_after"],
        "optional_config": ["alpha"],
    },
    "one_way_anova": {
        "name": "One-Way ANOVA",
        "category": "comparison",
        "description": "Compare means across 3 or more groups (with Tukey HSD post-hoc)",
        "y_type": "continuous",
        "x_type": "categorical (3+ levels)",
        "min_samples": 6,
        "required_config": ["y_column", "x_column"],
        "optional_config": ["alpha"],
    },
    "two_way_anova": {
        "name": "Two-Way ANOVA",
        "category": "comparison",
        "description": "Two-factor comparison with interaction effects",
        "y_type": "continuous",
        "x_type": "two categorical factors",
        "min_samples": 8,
        "required_config": ["y_column", "factor_a", "factor_b"],
        "optional_config": ["alpha"],
    },
    "mann_whitney": {
        "name": "Mann-Whitney U Test",
        "category": "comparison",
        "description": "Non-parametric 2-sample comparison (when data isn't normal)",
        "y_type": "continuous (non-normal OK)",
        "x_type": "categorical (2 levels)",
        "min_samples": 2,
        "required_config": ["y_column", "x_column"],
        "optional_config": ["alpha", "alternative"],
    },
    "kruskal_wallis": {
        "name": "Kruskal-Wallis H Test",
        "category": "comparison",
        "description": "Non-parametric 3+ group comparison (when data isn't normal)",
        "y_type": "continuous (non-normal OK)",
        "x_type": "categorical (3+ levels)",
        "min_samples": 4,
        "required_config": ["y_column", "x_column"],
        "optional_config": ["alpha"],
    },
    "chi_square_association": {
        "name": "Chi-Square Test of Association",
        "category": "comparison",
        "description": "Test association between two categorical variables",
        "y_type": "categorical",
        "x_type": "categorical",
        "min_samples": 5,
        "required_config": ["column_a", "column_b"],
        "optional_config": ["alpha"],
    },
    "chi_square_goodness": {
        "name": "Chi-Square Goodness of Fit",
        "category": "comparison",
        "description": "Test whether observed distribution matches expected",
        "y_type": "categorical",
        "x_type": None,
        "min_samples": 5,
        "required_config": ["column"],
        "optional_config": ["expected_proportions", "alpha"],
    },

    # Correlation & Regression
    "correlation": {
        "name": "Correlation Analysis",
        "category": "correlation",
        "description": "Pearson and Spearman correlation matrix with heatmap",
        "y_type": "continuous (multiple)",
        "x_type": None,
        "min_samples": 3,
        "required_config": [],
        "optional_config": ["columns", "method"],
    },
    "simple_regression": {
        "name": "Simple Linear Regression",
        "category": "regression",
        "description": "Single-predictor linear regression with residual plots",
        "y_type": "continuous",
        "x_type": "continuous",
        "min_samples": 3,
        "required_config": ["y_column", "x_column"],
        "optional_config": ["alpha"],
    },
    "multiple_regression": {
        "name": "Multiple Linear Regression",
        "category": "regression",
        "description": "Multiple-predictor regression with VIF and diagnostics",
        "y_type": "continuous",
        "x_type": "continuous (multiple)",
        "min_samples": 10,
        "required_config": ["y_column", "x_columns"],
        "optional_config": ["alpha"],
    },
    "logistic_regression": {
        "name": "Logistic Regression",
        "category": "regression",
        "description": "Binary outcome prediction with odds ratios",
        "y_type": "binary",
        "x_type": "continuous or categorical",
        "min_samples": 20,
        "required_config": ["y_column", "x_columns"],
        "optional_config": ["alpha"],
    },

    # SPC
    "i_mr_chart": {
        "name": "I-MR Control Chart",
        "category": "spc",
        "description": "Individuals and Moving Range chart for single measurements",
        "y_type": "continuous (time-ordered)",
        "x_type": None,
        "min_samples": 2,
        "required_config": ["column"],
        "optional_config": ["labels_column"],
    },
    "xbar_r_chart": {
        "name": "X-bar/R Control Chart",
        "category": "spc",
        "description": "Subgroup means and ranges chart",
        "y_type": "continuous (subgroups)",
        "x_type": None,
        "min_samples": 4,
        "required_config": ["column", "subgroup_size"],
        "optional_config": ["columns", "labels_column"],
    },
    "p_chart": {
        "name": "P Chart",
        "category": "spc",
        "description": "Proportion defective chart",
        "y_type": "count",
        "x_type": None,
        "min_samples": 2,
        "required_config": ["defects_column"],
        "optional_config": ["sample_size_column", "sample_size"],
    },
    "np_chart": {
        "name": "NP Chart",
        "category": "spc",
        "description": "Count defective chart (constant sample size)",
        "y_type": "count",
        "x_type": None,
        "min_samples": 2,
        "required_config": ["defects_column", "sample_size"],
        "optional_config": [],
    },
    "c_chart": {
        "name": "C Chart",
        "category": "spc",
        "description": "Defects per unit chart (constant opportunity)",
        "y_type": "count",
        "x_type": None,
        "min_samples": 2,
        "required_config": ["column"],
        "optional_config": [],
    },
    "u_chart": {
        "name": "U Chart",
        "category": "spc",
        "description": "Defects per unit chart (variable sample size)",
        "y_type": "count",
        "x_type": None,
        "min_samples": 2,
        "required_config": ["defects_column"],
        "optional_config": ["units_column", "units"],
    },

    # Capability
    "capability_normal": {
        "name": "Process Capability (Normal)",
        "category": "capability",
        "description": "Cp, Cpk, Pp, Ppk for normally distributed data",
        "y_type": "continuous (normal)",
        "x_type": None,
        "min_samples": 2,
        "required_config": ["column"],
        "optional_config": ["lsl", "usl", "target", "subgroup_size"],
    },
    "capability_nonnormal": {
        "name": "Process Capability (Non-Normal)",
        "category": "capability",
        "description": "Capability via Box-Cox transformation for non-normal data",
        "y_type": "continuous (non-normal)",
        "x_type": None,
        "min_samples": 3,
        "required_config": ["column"],
        "optional_config": ["lsl", "usl", "target"],
    },
    "msa_gage_rr": {
        "name": "Gage R&R (MSA)",
        "category": "capability",
        "description": "Measurement System Analysis — repeatability and reproducibility",
        "y_type": "continuous",
        "x_type": "part + operator",
        "min_samples": 8,
        "required_config": ["measurement_column", "part_column", "operator_column"],
        "optional_config": ["tolerance"],
    },

    # DOE
    "full_factorial": {
        "name": "Full Factorial Design",
        "category": "doe",
        "description": "Generate a 2^k full factorial design matrix",
        "y_type": None,
        "x_type": "factors with levels",
        "min_samples": 0,
        "required_config": ["factors"],
        "optional_config": ["center_points", "replicates"],
    },
    "fractional_factorial": {
        "name": "Fractional Factorial Design",
        "category": "doe",
        "description": "Generate a 2^(k-p) fractional factorial design",
        "y_type": None,
        "x_type": "factors with levels",
        "min_samples": 0,
        "required_config": ["factors", "fraction"],
        "optional_config": ["replicates"],
    },
    "doe_analysis": {
        "name": "DOE Analysis",
        "category": "doe",
        "description": "Analyze factorial experiment results with main effects and interactions",
        "y_type": "continuous",
        "x_type": "categorical factors",
        "min_samples": 4,
        "required_config": ["response_column", "factor_columns"],
        "optional_config": ["alpha"],
    },
}


# ---------------------------------------------------------------------------
# StatsEngine
# ---------------------------------------------------------------------------

class StatsEngine:
    """
    Central orchestrator for all statistical tests.

    Usage:
        engine = StatsEngine()
        result = engine.run_test("two_sample_t", df, {"y_column": "wait_time", "x_column": "shift"})
    """

    def run_test(self, test_type: str, df: pd.DataFrame, config: dict) -> AnalysisResult:
        """
        Execute a statistical test.

        Args:
            test_type: One of the registered test types (e.g., "two_sample_t")
            df: The dataset as a pandas DataFrame
            config: Test-specific configuration (columns, alpha, etc.)

        Returns:
            AnalysisResult with summary, details, charts, and interpretation context
        """
        if test_type not in _TEST_REGISTRY:
            return AnalysisResult(
                test_type=test_type,
                test_category="unknown",
                success=False,
                summary={},
                details={"error": f"Unknown test type: '{test_type}'", "available_tests": list(_TEST_REGISTRY.keys())},
                warnings=[f"Test type '{test_type}' is not registered"],
            )

        test_fn, category = _TEST_REGISTRY[test_type]

        start_time = time.time()
        try:
            result = test_fn(df, config)
        except Exception as e:
            elapsed = int((time.time() - start_time) * 1000)
            return AnalysisResult(
                test_type=test_type,
                test_category=category,
                success=False,
                summary={},
                details={"error": str(e), "duration_ms": elapsed},
                warnings=[f"Test execution failed: {e}"],
            )

        elapsed = int((time.time() - start_time) * 1000)

        # Inject timing into details
        if result.details:
            result.details["duration_ms"] = elapsed
        else:
            result.details = {"duration_ms": elapsed}

        return result

    def get_available_tests(self, dataset_profile: dict | None = None) -> list[dict]:
        """
        Return available tests, optionally filtered by dataset characteristics.

        Args:
            dataset_profile: Optional profile with column info to filter applicable tests

        Returns:
            List of test metadata dicts from TEST_CATALOG
        """
        tests = []
        for test_type, meta in TEST_CATALOG.items():
            entry = {"test_type": test_type, **meta}

            # If dataset profile provided, score applicability
            if dataset_profile:
                entry["applicable"] = self._check_applicability(meta, dataset_profile)

            tests.append(entry)

        return tests

    def get_test_info(self, test_type: str) -> dict | None:
        """Get metadata for a specific test type."""
        if test_type in TEST_CATALOG:
            return {"test_type": test_type, **TEST_CATALOG[test_type]}
        return None

    def get_categories(self) -> dict[str, list[str]]:
        """Return tests organized by category."""
        categories: dict[str, list[str]] = {}
        for test_type, meta in TEST_CATALOG.items():
            cat = meta["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(test_type)
        return categories

    def _check_applicability(self, meta: dict, profile: dict) -> bool:
        """Check if a test is applicable given the dataset profile."""
        columns = profile.get("columns", [])
        row_count = profile.get("row_count", 0)

        # Check minimum sample size
        if row_count < meta.get("min_samples", 0):
            return False

        # Check if we have the right column types
        numeric_cols = [c for c in columns if c.get("dtype", "").startswith(("int", "float", "num"))]
        categorical_cols = [c for c in columns if not c.get("dtype", "").startswith(("int", "float", "num"))]

        y_type = meta.get("y_type", "")
        if y_type and "continuous" in y_type and not numeric_cols:
            return False
        if y_type and "categorical" in y_type and not categorical_cols:
            return False

        return True
