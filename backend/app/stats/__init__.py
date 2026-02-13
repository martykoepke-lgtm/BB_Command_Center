"""
Statistical engine for BB Enabled Command.

Provides a unified interface for running statistical tests, generating charts,
and returning structured results that can be interpreted by the AI Stats Advisor.

All test functions accept a pandas DataFrame and a configuration dict,
and return an AnalysisResult.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlotlyChart(BaseModel):
    """A single Plotly chart specification."""
    chart_type: str  # histogram, box, scatter, control_chart, pareto, probability, bar, heatmap, etc.
    data: list[dict] = Field(default_factory=list)  # Plotly trace objects
    layout: dict = Field(default_factory=dict)  # Plotly layout object
    title: str = ""


class AnalysisResult(BaseModel):
    """Standardized result from any statistical test."""
    test_type: str
    test_category: str  # descriptive, comparison, correlation, regression, spc, capability, doe
    success: bool
    summary: dict  # { "statistic": 4.23, "p_value": 0.003, "effect_size": 0.45, ... }
    details: dict  # test-specific detailed output
    charts: list[PlotlyChart] = Field(default_factory=list)
    interpretation_context: dict = Field(default_factory=dict)  # passed to AI for plain-language interpretation
    warnings: list[str] = Field(default_factory=list)
