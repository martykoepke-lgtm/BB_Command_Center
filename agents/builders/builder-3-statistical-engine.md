# Builder 3: Statistical Engine Agent

## Ownership
You own:
- `backend/app/stats/` — All statistical test implementations
- `backend/app/services/stats_engine.py` — The stats engine service that Builder 2's routes call

## Mission
Build the embedded Minitab replacement. Every statistical test a Lean Six Sigma Black Belt needs, implemented in Python, with Plotly chart generation and structured output that the AI Stats Advisor can interpret in plain language.

## Tech Stack (locked)
- scipy.stats — hypothesis tests, distributions, normality
- statsmodels — regression, ANOVA, DOE, time series
- pandas — data manipulation, descriptive statistics
- numpy — numerical computation
- plotly — chart generation (JSON specs consumed by frontend)

## What You Build

### Service Interface
Implement the interface defined by Builder 2:

```python
class StatsEngine:
    async def profile_dataset(self, dataset_id: UUID) -> DatasetProfile:
        """Auto-profile an uploaded dataset: column types, descriptive stats, quality issues."""

    async def run_test(self, test_type: str, config: dict, dataset_id: UUID) -> AnalysisResult:
        """Execute a statistical test and return structured results with charts."""

    async def get_available_tests(self, dataset_profile: DatasetProfile) -> list[TestRecommendation]:
        """Given a dataset profile, return which tests are applicable and why."""
```

### Test Implementations

Organize by category. Each test module must:
1. Accept a standardized config dict
2. Validate assumptions before running (normality, equal variance, sample size)
3. Return an `AnalysisResult` with summary stats, detailed output, charts, and interpretation context
4. Include assumption violation warnings in the result

#### `stats/descriptive.py`
```python
def descriptive_summary(df, columns) -> AnalysisResult:
    # mean, median, mode, std, range, Q1/Q3, IQR, skewness, kurtosis
    # Charts: histogram with normal overlay, box plot

def normality_test(df, column, method='shapiro') -> AnalysisResult:
    # Shapiro-Wilk (n < 5000) or Anderson-Darling
    # Charts: histogram with normal curve, probability plot (Q-Q)
    # interpretation_context: { "is_normal": bool, "p_value": float, "recommendation": str }
```

#### `stats/comparison.py`
```python
def one_sample_t(df, column, hypothesized_mean, alpha=0.05) -> AnalysisResult:
def two_sample_t(df, y_column, group_column, alpha=0.05) -> AnalysisResult:
def paired_t(df, before_column, after_column, alpha=0.05) -> AnalysisResult:
def one_way_anova(df, y_column, factor_column, alpha=0.05) -> AnalysisResult:
    # Include Tukey HSD post-hoc if significant
def two_way_anova(df, y_column, factor1, factor2, alpha=0.05) -> AnalysisResult:
    # Include interaction effects
def mann_whitney(df, y_column, group_column, alpha=0.05) -> AnalysisResult:
def kruskal_wallis(df, y_column, factor_column, alpha=0.05) -> AnalysisResult:
def chi_square_association(df, column1, column2, alpha=0.05) -> AnalysisResult:
def chi_square_goodness(df, column, expected_distribution, alpha=0.05) -> AnalysisResult:
```

#### `stats/correlation.py`
```python
def correlation_matrix(df, columns, method='pearson') -> AnalysisResult:
    # Pearson and Spearman
    # Charts: correlation heatmap, scatter matrix
def simple_regression(df, y_column, x_column) -> AnalysisResult:
    # R-squared, coefficients, p-values, residual analysis
    # Charts: scatter with regression line, residual plots (fitted vs residual, normal probability, histogram)
def multiple_regression(df, y_column, x_columns) -> AnalysisResult:
    # Adjusted R-squared, VIF for multicollinearity, coefficients table
    # Charts: actual vs predicted, residual plots, coefficient bar chart
def logistic_regression(df, y_column, x_columns) -> AnalysisResult:
    # Odds ratios, ROC curve, confusion matrix
```

#### `stats/spc.py` (Statistical Process Control)
```python
def i_mr_chart(df, value_column, timestamp_column=None) -> AnalysisResult:
    # Individual and Moving Range chart
    # UCL, LCL, CL calculated from data
    # Out-of-control points flagged (Western Electric rules)
    # Charts: I chart + MR chart stacked

def xbar_r_chart(df, value_column, subgroup_column, timestamp_column=None) -> AnalysisResult:
    # X-bar and R chart for subgrouped data
    # Charts: X-bar chart + R chart stacked

def p_chart(df, defective_column, sample_size_column) -> AnalysisResult:
def np_chart(df, defective_column, sample_size) -> AnalysisResult:
def c_chart(df, defect_count_column) -> AnalysisResult:
def u_chart(df, defect_count_column, unit_column) -> AnalysisResult:
```

#### `stats/capability.py`
```python
def capability_normal(df, column, lsl=None, usl=None, target=None) -> AnalysisResult:
    # Cp, Cpk, Pp, Ppk, sigma level
    # Charts: capability histogram with spec limits, normal curve overlay
    # interpretation_context: { "cp": float, "cpk": float, "sigma_level": float,
    #   "ppm_out_of_spec": float, "recommendation": str }

def capability_nonnormal(df, column, lsl=None, usl=None, distribution='weibull') -> AnalysisResult:
    # Fit best distribution, calculate equivalent capability
```

#### `stats/doe.py` (Design of Experiments)
```python
def generate_factorial_design(factors: dict, design_type='full') -> pd.DataFrame:
    # Generate the experimental design matrix
    # factors: { "Temperature": [150, 200], "Pressure": [10, 20], "Speed": [100, 150] }

def analyze_factorial(df, y_column, factor_columns) -> AnalysisResult:
    # Main effects, interaction effects, significance
    # Charts: main effects plot, interaction plot, Pareto of effects, normal probability of effects
```

#### `stats/other.py`
```python
def pareto_analysis(df, category_column, value_column=None) -> AnalysisResult:
    # Pareto chart with cumulative line
    # Vital few identification (80/20)
    # Charts: Pareto bar + cumulative line

def msa_gage_rr(df, part_column, operator_column, measurement_column) -> AnalysisResult:
    # Repeatability, reproducibility, part-to-part variation
    # %GRR, number of distinct categories
    # Charts: components of variation, R chart by operator, Xbar chart by operator
```

### Chart Generation

All charts must be generated as Plotly JSON specifications:

```python
def create_plotly_chart(chart_type, data, layout_overrides=None) -> dict:
    """Return a dict with 'data' and 'layout' keys consumable by Plotly.js on the frontend."""
    return {
        "type": chart_type,  # histogram, scatter, box, bar, heatmap, line
        "data": [...],       # Plotly trace objects
        "layout": {          # Plotly layout object
            "template": "plotly_dark",  # match app dark mode
            "font": {"family": "Inter, sans-serif"},
            ...layout_overrides
        }
    }
```

### Test Selection Logic

```python
def recommend_tests(profile: DatasetProfile, context: dict = None) -> list[TestRecommendation]:
    """
    Given a dataset profile and optional project context, recommend applicable statistical tests.

    Logic:
    - Count continuous vs categorical columns
    - Check sample sizes
    - Consider data distributions (normal vs non-normal)
    - If context provides Y and X variables, narrow recommendations

    Returns ranked list with reasoning for each recommendation.
    """
```

Each `TestRecommendation` includes:
```python
class TestRecommendation(BaseModel):
    test_type: str           # matches test catalog in CLAUDE.md
    test_name: str           # human-readable name
    category: str            # comparison, correlation, spc, etc.
    reasoning: str           # why this test is appropriate
    confidence: str          # high, medium, low
    requirements: dict       # { "min_sample_size": 30, "y_type": "continuous", "x_type": "categorical" }
    configuration_template: dict  # pre-filled config for the test
```

### Assumption Checking

Before running any test, validate assumptions and include warnings:

```python
ASSUMPTION_CHECKS = {
    "two_sample_t": ["normality_both_groups", "equal_variance", "independence", "min_sample_size_5"],
    "one_way_anova": ["normality_all_groups", "equal_variance", "independence", "min_sample_size_per_group_3"],
    "chi_square": ["expected_count_min_5", "independence"],
    "regression": ["normality_residuals", "homoscedasticity", "independence", "no_multicollinearity"],
    "capability": ["normality", "process_stability"],
}
```

If assumptions are violated, include in the result:
```python
result.warnings = [
    "Shapiro-Wilk test rejected normality for Group B (p=0.02). Consider Mann-Whitney U as a non-parametric alternative.",
    "Levene's test shows unequal variances (p=0.04). Using Welch's t-test instead of pooled."
]
```

## AnalysisResult Format (must match CLAUDE.md)

```python
class AnalysisResult(BaseModel):
    test_type: str
    test_category: str
    success: bool
    summary: dict            # key numbers: statistic, p_value, effect_size, confidence_interval
    details: dict            # full output: group means, coefficients, ANOVA table, etc.
    charts: list[dict]       # Plotly JSON specs
    interpretation_context: dict  # structured data for AI to generate plain-language interpretation
    warnings: list[str]      # assumption violations, data quality issues
```

## What You Do NOT Build
- API endpoints (Builder 2 calls your service interface)
- AI agent logic (Builder 4's Stats Advisor calls your `recommend_tests` and `run_test`)
- Frontend chart rendering (Builder 1 takes your Plotly JSON and renders it)
- Dashboard aggregation (Builder 5)

## Dependencies
- **Builder 2** defines the `Dataset` model and provides data access
- **Builder 4** calls your `recommend_tests()` and `run_test()` through the Stats Advisor agent
- Your Plotly chart specs must be compatible with Plotly.js on the frontend (Builder 1)
