"""
Correlation and regression analysis.

Tests:
  - correlation: Pearson and Spearman correlation matrix
  - simple_regression: Single-predictor linear regression
  - multiple_regression: Multiple-predictor regression
  - logistic_regression: Binary outcome prediction
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from app.stats import AnalysisResult, PlotlyChart
from app.stats import charts


# ---------------------------------------------------------------------------
# Correlation Matrix
# ---------------------------------------------------------------------------

def correlation(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Compute Pearson and Spearman correlation matrices.

    Config:
        columns: list[str]  — columns to include (default: all numeric)
        method: str         — "pearson" | "spearman" | "both" (default: "both")
    """
    columns = config.get("columns")
    method = config.get("method", "both")

    if columns:
        numeric_df = df[columns].select_dtypes(include=["number"])
    else:
        numeric_df = df.select_dtypes(include=["number"])

    if numeric_df.shape[1] < 2:
        return AnalysisResult(
            test_type="correlation", test_category="correlation", success=False,
            summary={}, details={"error": "Need at least 2 numeric columns"},
        )

    clean = numeric_df.dropna()
    warnings: list[str] = []

    if len(clean) < 3:
        return AnalysisResult(
            test_type="correlation", test_category="correlation", success=False,
            summary={}, details={"error": "Need at least 3 complete observations"},
        )

    results: dict = {"n": len(clean)}
    chart_list: list[PlotlyChart] = []
    col_names = clean.columns.tolist()

    if method in ("pearson", "both"):
        pearson_matrix = clean.corr(method="pearson")
        # P-values for Pearson
        p_matrix = np.zeros((len(col_names), len(col_names)))
        for i, c1 in enumerate(col_names):
            for j, c2 in enumerate(col_names):
                if i == j:
                    p_matrix[i][j] = 0.0
                else:
                    _, p = sp_stats.pearsonr(clean[c1], clean[c2])
                    p_matrix[i][j] = p

        results["pearson"] = {
            "correlations": pearson_matrix.values.tolist(),
            "p_values": p_matrix.tolist(),
        }
        chart_list.append(charts.heatmap(
            matrix=pearson_matrix.values.tolist(),
            labels=col_names,
            title="Pearson Correlation Matrix",
        ))

    if method in ("spearman", "both"):
        spearman_matrix = clean.corr(method="spearman")
        p_matrix = np.zeros((len(col_names), len(col_names)))
        for i, c1 in enumerate(col_names):
            for j, c2 in enumerate(col_names):
                if i == j:
                    p_matrix[i][j] = 0.0
                else:
                    _, p = sp_stats.spearmanr(clean[c1], clean[c2])
                    p_matrix[i][j] = p

        results["spearman"] = {
            "correlations": spearman_matrix.values.tolist(),
            "p_values": p_matrix.tolist(),
        }
        chart_list.append(charts.heatmap(
            matrix=spearman_matrix.values.tolist(),
            labels=col_names,
            title="Spearman Correlation Matrix",
        ))

    # Find strongest correlations
    strong_pairs = []
    for method_name in ("pearson", "spearman"):
        if method_name not in results:
            continue
        corr = results[method_name]["correlations"]
        for i in range(len(col_names)):
            for j in range(i + 1, len(col_names)):
                r = corr[i][j]
                if abs(r) >= 0.5:
                    strong_pairs.append({
                        "var1": col_names[i], "var2": col_names[j],
                        "r": round(r, 4), "method": method_name,
                    })
    strong_pairs.sort(key=lambda x: abs(x["r"]), reverse=True)

    summary = {
        "columns": col_names,
        "n": len(clean),
        "strong_correlations": strong_pairs[:10],
    }

    return AnalysisResult(
        test_type="correlation",
        test_category="correlation",
        success=True,
        summary=summary,
        details={"columns": col_names, **results},
        charts=chart_list,
        interpretation_context={
            "test_name": "Correlation Analysis",
            "n": len(clean),
            "column_count": len(col_names),
            "strong_pairs": strong_pairs[:5],
            "methods_used": method,
        },
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Simple Linear Regression
# ---------------------------------------------------------------------------

def simple_regression(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        y_column: str  — response variable
        x_column: str  — predictor variable
        alpha: float   — significance level (default: 0.05)
    """
    y_col = config.get("y_column")
    x_col = config.get("x_column")
    alpha = config.get("alpha", 0.05)

    if not y_col or y_col not in df.columns:
        return AnalysisResult(test_type="simple_regression", test_category="regression", success=False,
                              summary={}, details={"error": f"Y column '{y_col}' not found"})
    if not x_col or x_col not in df.columns:
        return AnalysisResult(test_type="simple_regression", test_category="regression", success=False,
                              summary={}, details={"error": f"X column '{x_col}' not found"})

    clean = df[[y_col, x_col]].dropna()
    y = clean[y_col].astype(float).values
    x = clean[x_col].astype(float).values
    n = len(y)
    warnings: list[str] = []

    if n < 3:
        return AnalysisResult(test_type="simple_regression", test_category="regression", success=False,
                              summary={}, details={"error": "Need at least 3 observations"})

    try:
        import statsmodels.api as sm

        X = sm.add_constant(x)
        model = sm.OLS(y, X).fit()

        fitted = model.fittedvalues
        residuals = model.resid

        summary_dict = {
            "r_squared": float(model.rsquared),
            "adj_r_squared": float(model.rsquared_adj),
            "f_statistic": float(model.fvalue),
            "f_p_value": float(model.f_pvalue),
            "significant": float(model.f_pvalue) < alpha,
            "intercept": float(model.params[0]),
            "slope": float(model.params[1]),
            "slope_p_value": float(model.pvalues[1]),
            "slope_ci_lower": float(model.conf_int(alpha)[1][0]),
            "slope_ci_upper": float(model.conf_int(alpha)[1][1]),
            "n": n,
            "durbin_watson": float(sm.stats.stattools.durbin_watson(residuals)),
        }

        # Trendline for scatter plot
        x_sorted = np.sort(x)
        y_trend = model.params[0] + model.params[1] * x_sorted

        chart_list = [
            charts.scatter(
                x=x.tolist(), y=y.tolist(),
                title=f"{y_col} vs {x_col}",
                xaxis_title=x_col, yaxis_title=y_col,
                trendline={"x": x_sorted.tolist(), "y": y_trend.tolist(), "name": "Regression Line"},
            ),
        ]
        chart_list.extend(charts.residual_plots(
            fitted=fitted.tolist(), residuals=residuals.tolist(),
            title=f"{y_col} ~ {x_col}",
        ))

        # Equation
        equation = f"{y_col} = {summary_dict['intercept']:.4f} + {summary_dict['slope']:.4f} × {x_col}"

        return AnalysisResult(
            test_type="simple_regression",
            test_category="regression",
            success=True,
            summary=summary_dict,
            details={
                "y_column": y_col, "x_column": x_col, "alpha": alpha,
                "equation": equation,
                "coefficients": {
                    "const": {"value": float(model.params[0]), "std_err": float(model.bse[0]),
                              "t_stat": float(model.tvalues[0]), "p_value": float(model.pvalues[0])},
                    x_col: {"value": float(model.params[1]), "std_err": float(model.bse[1]),
                             "t_stat": float(model.tvalues[1]), "p_value": float(model.pvalues[1])},
                },
                "aic": float(model.aic),
                "bic": float(model.bic),
            },
            charts=chart_list,
            interpretation_context={
                "test_name": "Simple Linear Regression",
                "equation": equation,
                "r_squared": float(model.rsquared),
                "r_squared_pct": round(float(model.rsquared) * 100, 1),
                "slope": float(model.params[1]),
                "slope_p_value": float(model.pvalues[1]),
                "significant": float(model.f_pvalue) < alpha,
                "alpha": alpha,
                "y_column": y_col, "x_column": x_col,
                "interpretation": (
                    f"For every 1-unit increase in {x_col}, {y_col} changes by {model.params[1]:.4f} units. "
                    f"The model explains {model.rsquared * 100:.1f}% of the variation in {y_col}."
                ),
            },
            warnings=warnings,
        )

    except Exception as e:
        return AnalysisResult(test_type="simple_regression", test_category="regression", success=False,
                              summary={}, details={"error": str(e)}, warnings=[str(e)])


# ---------------------------------------------------------------------------
# Multiple Linear Regression
# ---------------------------------------------------------------------------

def multiple_regression(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        y_column: str        — response variable
        x_columns: list[str] — predictor variables
        alpha: float         — significance level (default: 0.05)
    """
    y_col = config.get("y_column")
    x_cols = config.get("x_columns", [])
    alpha = config.get("alpha", 0.05)

    if not y_col or y_col not in df.columns:
        return AnalysisResult(test_type="multiple_regression", test_category="regression", success=False,
                              summary={}, details={"error": f"Y column '{y_col}' not found"})

    missing = [c for c in x_cols if c not in df.columns]
    if missing:
        return AnalysisResult(test_type="multiple_regression", test_category="regression", success=False,
                              summary={}, details={"error": f"X columns not found: {missing}"})

    if len(x_cols) < 1:
        return AnalysisResult(test_type="multiple_regression", test_category="regression", success=False,
                              summary={}, details={"error": "Need at least 1 predictor column"})

    clean = df[[y_col] + x_cols].dropna()
    n = len(clean)
    warnings: list[str] = []

    if n < len(x_cols) + 2:
        return AnalysisResult(test_type="multiple_regression", test_category="regression", success=False,
                              summary={}, details={"error": f"Need at least {len(x_cols) + 2} observations, got {n}"})

    if n < 10 * len(x_cols):
        warnings.append(
            f"Sample size ({n}) is less than 10× the number of predictors ({len(x_cols)}). "
            "Results may be unreliable."
        )

    try:
        import statsmodels.api as sm

        y = clean[y_col].astype(float).values
        X = sm.add_constant(clean[x_cols].astype(float).values)
        model = sm.OLS(y, X).fit()

        fitted = model.fittedvalues
        residuals = model.resid

        # VIF for multicollinearity
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        vif_data = {}
        for i, col in enumerate(x_cols):
            vif = variance_inflation_factor(X, i + 1)  # +1 because index 0 is constant
            vif_data[col] = float(vif)
            if vif > 10:
                warnings.append(f"High multicollinearity detected for '{col}' (VIF = {vif:.1f})")

        # Build coefficients
        coeff_names = ["const"] + x_cols
        coefficients = {}
        for i, name in enumerate(coeff_names):
            ci = model.conf_int(alpha)
            coefficients[name] = {
                "value": float(model.params[i]),
                "std_err": float(model.bse[i]),
                "t_stat": float(model.tvalues[i]),
                "p_value": float(model.pvalues[i]),
                "ci_lower": float(ci[i][0]),
                "ci_upper": float(ci[i][1]),
                "significant": float(model.pvalues[i]) < alpha,
            }

        significant_predictors = [name for name, c in coefficients.items()
                                  if name != "const" and c["significant"]]

        summary_dict = {
            "r_squared": float(model.rsquared),
            "adj_r_squared": float(model.rsquared_adj),
            "f_statistic": float(model.fvalue),
            "f_p_value": float(model.f_pvalue),
            "significant": float(model.f_pvalue) < alpha,
            "n": n,
            "predictor_count": len(x_cols),
            "significant_predictors": significant_predictors,
        }

        chart_list = charts.residual_plots(
            fitted=fitted.tolist(), residuals=residuals.tolist(),
            title=f"Multiple Regression: {y_col}",
        )

        return AnalysisResult(
            test_type="multiple_regression",
            test_category="regression",
            success=True,
            summary=summary_dict,
            details={
                "y_column": y_col, "x_columns": x_cols, "alpha": alpha,
                "coefficients": coefficients,
                "vif": vif_data,
                "aic": float(model.aic),
                "bic": float(model.bic),
                "durbin_watson": float(sm.stats.stattools.durbin_watson(residuals)),
            },
            charts=chart_list,
            interpretation_context={
                "test_name": "Multiple Linear Regression",
                "r_squared": float(model.rsquared),
                "r_squared_pct": round(float(model.rsquared) * 100, 1),
                "adj_r_squared": float(model.rsquared_adj),
                "significant": float(model.f_pvalue) < alpha,
                "significant_predictors": significant_predictors,
                "predictor_count": len(x_cols),
                "alpha": alpha,
                "y_column": y_col,
            },
            warnings=warnings,
        )

    except Exception as e:
        return AnalysisResult(test_type="multiple_regression", test_category="regression", success=False,
                              summary={}, details={"error": str(e)}, warnings=[str(e)])


# ---------------------------------------------------------------------------
# Logistic Regression
# ---------------------------------------------------------------------------

def logistic_regression(df: pd.DataFrame, config: dict) -> AnalysisResult:
    """
    Config:
        y_column: str        — binary response variable (0/1 or categorical with 2 levels)
        x_columns: list[str] — predictor variables
        alpha: float         — significance level (default: 0.05)
    """
    y_col = config.get("y_column")
    x_cols = config.get("x_columns", [])
    alpha = config.get("alpha", 0.05)

    if not y_col or y_col not in df.columns:
        return AnalysisResult(test_type="logistic_regression", test_category="regression", success=False,
                              summary={}, details={"error": f"Y column '{y_col}' not found"})

    missing = [c for c in x_cols if c not in df.columns]
    if missing:
        return AnalysisResult(test_type="logistic_regression", test_category="regression", success=False,
                              summary={}, details={"error": f"X columns not found: {missing}"})

    clean = df[[y_col] + x_cols].dropna()
    warnings: list[str] = []

    # Encode binary Y
    y_values = clean[y_col].unique()
    if len(y_values) != 2:
        return AnalysisResult(test_type="logistic_regression", test_category="regression", success=False,
                              summary={}, details={"error": f"Y must have exactly 2 levels, found {len(y_values)}: {list(y_values)}"},
                              warnings=["Logistic regression requires a binary outcome variable"])

    # Map to 0/1
    if set(y_values) == {0, 1} or set(y_values) == {0.0, 1.0}:
        y = clean[y_col].astype(float).values
    else:
        mapping = {y_values[0]: 0, y_values[1]: 1}
        y = clean[y_col].map(mapping).astype(float).values
        warnings.append(f"Mapped '{y_values[0]}' → 0 and '{y_values[1]}' → 1")

    n = len(y)
    if n < len(x_cols) + 10:
        warnings.append(f"Small sample ({n}) for {len(x_cols)} predictors. Results may be unreliable.")

    try:
        import statsmodels.api as sm

        X = sm.add_constant(clean[x_cols].astype(float).values)
        model = sm.Logit(y, X).fit(disp=0)

        coeff_names = ["const"] + x_cols
        coefficients = {}
        for i, name in enumerate(coeff_names):
            ci = model.conf_int(alpha)
            coefficients[name] = {
                "value": float(model.params[i]),
                "odds_ratio": float(np.exp(model.params[i])),
                "std_err": float(model.bse[i]),
                "z_stat": float(model.tvalues[i]),
                "p_value": float(model.pvalues[i]),
                "ci_lower": float(ci[i][0]),
                "ci_upper": float(ci[i][1]),
                "significant": float(model.pvalues[i]) < alpha,
            }

        # Classification metrics
        predicted_probs = model.predict(X)
        predicted_class = (predicted_probs >= 0.5).astype(int)
        accuracy = float(np.mean(predicted_class == y))
        confusion = {
            "true_positive": int(((predicted_class == 1) & (y == 1)).sum()),
            "true_negative": int(((predicted_class == 0) & (y == 0)).sum()),
            "false_positive": int(((predicted_class == 1) & (y == 0)).sum()),
            "false_negative": int(((predicted_class == 0) & (y == 1)).sum()),
        }

        significant_predictors = [name for name, c in coefficients.items()
                                  if name != "const" and c["significant"]]

        summary_dict = {
            "pseudo_r_squared": float(model.prsquared),
            "log_likelihood": float(model.llf),
            "aic": float(model.aic),
            "bic": float(model.bic),
            "accuracy": accuracy,
            "n": n,
            "significant_predictors": significant_predictors,
        }

        return AnalysisResult(
            test_type="logistic_regression",
            test_category="regression",
            success=True,
            summary=summary_dict,
            details={
                "y_column": y_col, "x_columns": x_cols, "alpha": alpha,
                "coefficients": coefficients,
                "confusion_matrix": confusion,
                "accuracy": accuracy,
            },
            charts=[],
            interpretation_context={
                "test_name": "Logistic Regression",
                "y_column": y_col,
                "pseudo_r_squared": float(model.prsquared),
                "accuracy": accuracy,
                "accuracy_pct": round(accuracy * 100, 1),
                "significant_predictors": significant_predictors,
                "odds_ratios": {name: c["odds_ratio"] for name, c in coefficients.items() if name != "const"},
                "alpha": alpha,
            },
            warnings=warnings,
        )

    except Exception as e:
        return AnalysisResult(test_type="logistic_regression", test_category="regression", success=False,
                              summary={}, details={"error": str(e)}, warnings=[str(e)])
