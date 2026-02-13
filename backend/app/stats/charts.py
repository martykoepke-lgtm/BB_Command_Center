"""
Chart generation module — produces Plotly JSON specifications for all chart types.

Every function returns a PlotlyChart (or list of PlotlyChart) that can be:
- Rendered interactively on the frontend via plotly.js
- Serialized to JSON for storage in the statistical_analyses table
- Exported to static images via kaleido for PDF reports
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from app.stats import PlotlyChart


# ---------------------------------------------------------------------------
# Color palette (dark-mode friendly, consistent with UI design)
# ---------------------------------------------------------------------------

COLORS = {
    "primary": "#3B82F6",      # blue-500
    "secondary": "#8B5CF6",    # purple-500
    "success": "#22C55E",      # green-500
    "warning": "#F59E0B",      # amber-500
    "danger": "#EF4444",       # red-500
    "info": "#06B6D4",         # cyan-500
    "accent": "#14B8A6",       # teal-500
    "muted": "#6B7280",        # gray-500
}

PALETTE = [
    "#3B82F6", "#EF4444", "#22C55E", "#F59E0B", "#8B5CF6",
    "#06B6D4", "#EC4899", "#14B8A6", "#F97316", "#6366F1",
]

DARK_LAYOUT = {
    "paper_bgcolor": "#1F2937",
    "plot_bgcolor": "#111827",
    "font": {"color": "#E5E7EB", "family": "Inter, system-ui, sans-serif"},
    "xaxis": {"gridcolor": "#374151", "zerolinecolor": "#4B5563"},
    "yaxis": {"gridcolor": "#374151", "zerolinecolor": "#4B5563"},
    "legend": {"bgcolor": "rgba(0,0,0,0)"},
    "margin": {"l": 60, "r": 30, "t": 50, "b": 60},
}


def _base_layout(**overrides) -> dict:
    """Merge dark mode defaults with per-chart overrides."""
    layout = {**DARK_LAYOUT}
    for key, val in overrides.items():
        if isinstance(val, dict) and key in layout and isinstance(layout[key], dict):
            layout[key] = {**layout[key], **val}
        else:
            layout[key] = val
    return layout


# ---------------------------------------------------------------------------
# Histogram
# ---------------------------------------------------------------------------

def histogram(
    values: Sequence[float],
    name: str = "Data",
    title: str = "Histogram",
    xaxis_title: str = "",
    nbins: int | None = None,
    show_normal_curve: bool = False,
) -> PlotlyChart:
    """Histogram with optional normal overlay."""
    data: list[dict] = [{
        "type": "histogram",
        "x": list(values),
        "name": name,
        "marker": {"color": COLORS["primary"], "line": {"color": "#1E3A5F", "width": 1}},
        "opacity": 0.85,
    }]
    if nbins:
        data[0]["nbinsx"] = nbins

    if show_normal_curve and len(values) > 2:
        arr = np.array(values, dtype=float)
        arr = arr[~np.isnan(arr)]
        if len(arr) > 2:
            mu, sigma = float(np.mean(arr)), float(np.std(arr, ddof=1))
            if sigma > 0:
                x_range = np.linspace(mu - 4 * sigma, mu + 4 * sigma, 200)
                from scipy.stats import norm
                y_vals = norm.pdf(x_range, mu, sigma)
                # Scale to match histogram area
                bin_width = (arr.max() - arr.min()) / (nbins or int(np.sqrt(len(arr))))
                y_scaled = y_vals * len(arr) * bin_width
                data.append({
                    "type": "scatter",
                    "x": x_range.tolist(),
                    "y": y_scaled.tolist(),
                    "mode": "lines",
                    "name": "Normal Curve",
                    "line": {"color": COLORS["danger"], "width": 2, "dash": "dash"},
                })

    return PlotlyChart(
        chart_type="histogram",
        data=data,
        layout=_base_layout(
            title={"text": title},
            xaxis={"title": xaxis_title, "gridcolor": "#374151"},
            yaxis={"title": "Frequency", "gridcolor": "#374151"},
            bargap=0.05,
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Box Plot
# ---------------------------------------------------------------------------

def box_plot(
    data_groups: dict[str, Sequence[float]],
    title: str = "Box Plot",
    yaxis_title: str = "Value",
) -> PlotlyChart:
    """Box plot comparing multiple groups."""
    traces: list[dict] = []
    for i, (group_name, values) in enumerate(data_groups.items()):
        traces.append({
            "type": "box",
            "y": list(values),
            "name": group_name,
            "marker": {"color": PALETTE[i % len(PALETTE)]},
            "boxmean": "sd",
        })

    return PlotlyChart(
        chart_type="box",
        data=traces,
        layout=_base_layout(
            title={"text": title},
            yaxis={"title": yaxis_title, "gridcolor": "#374151"},
            showlegend=len(data_groups) > 1,
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Scatter Plot
# ---------------------------------------------------------------------------

def scatter(
    x: Sequence[float],
    y: Sequence[float],
    title: str = "Scatter Plot",
    xaxis_title: str = "X",
    yaxis_title: str = "Y",
    trendline: dict | None = None,
    name: str = "Data",
) -> PlotlyChart:
    """Scatter plot with optional regression trendline."""
    traces: list[dict] = [{
        "type": "scatter",
        "x": list(x),
        "y": list(y),
        "mode": "markers",
        "name": name,
        "marker": {"color": COLORS["primary"], "size": 8, "opacity": 0.7},
    }]

    if trendline:
        traces.append({
            "type": "scatter",
            "x": list(trendline["x"]),
            "y": list(trendline["y"]),
            "mode": "lines",
            "name": trendline.get("name", "Trend"),
            "line": {"color": COLORS["danger"], "width": 2},
        })

    return PlotlyChart(
        chart_type="scatter",
        data=traces,
        layout=_base_layout(
            title={"text": title},
            xaxis={"title": xaxis_title, "gridcolor": "#374151"},
            yaxis={"title": yaxis_title, "gridcolor": "#374151"},
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Bar Chart
# ---------------------------------------------------------------------------

def bar_chart(
    categories: Sequence[str],
    values: Sequence[float],
    title: str = "Bar Chart",
    xaxis_title: str = "",
    yaxis_title: str = "Value",
    orientation: str = "v",
    color: str | None = None,
) -> PlotlyChart:
    """Simple bar chart."""
    trace: dict = {
        "type": "bar",
        "marker": {"color": color or COLORS["primary"]},
    }
    if orientation == "h":
        trace["x"] = list(values)
        trace["y"] = list(categories)
        trace["orientation"] = "h"
    else:
        trace["x"] = list(categories)
        trace["y"] = list(values)

    return PlotlyChart(
        chart_type="bar",
        data=[trace],
        layout=_base_layout(
            title={"text": title},
            xaxis={"title": xaxis_title, "gridcolor": "#374151"},
            yaxis={"title": yaxis_title, "gridcolor": "#374151"},
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Pareto Chart
# ---------------------------------------------------------------------------

def pareto_chart(
    categories: Sequence[str],
    values: Sequence[float],
    title: str = "Pareto Chart",
    yaxis_title: str = "Count",
) -> PlotlyChart:
    """Pareto chart with bars + cumulative line."""
    sorted_pairs = sorted(zip(categories, values), key=lambda p: p[1], reverse=True)
    sorted_cats = [p[0] for p in sorted_pairs]
    sorted_vals = [p[1] for p in sorted_pairs]
    total = sum(sorted_vals) if sorted_vals else 1
    cumulative = []
    running = 0.0
    for v in sorted_vals:
        running += v
        cumulative.append(running / total * 100)

    traces: list[dict] = [
        {
            "type": "bar",
            "x": sorted_cats,
            "y": sorted_vals,
            "name": yaxis_title,
            "marker": {"color": COLORS["primary"]},
            "yaxis": "y",
        },
        {
            "type": "scatter",
            "x": sorted_cats,
            "y": cumulative,
            "name": "Cumulative %",
            "mode": "lines+markers",
            "line": {"color": COLORS["danger"], "width": 2},
            "marker": {"size": 6},
            "yaxis": "y2",
        },
    ]

    # Add 80% line
    traces.append({
        "type": "scatter",
        "x": [sorted_cats[0], sorted_cats[-1]] if sorted_cats else [],
        "y": [80, 80],
        "mode": "lines",
        "name": "80% Line",
        "line": {"color": COLORS["warning"], "width": 1, "dash": "dash"},
        "yaxis": "y2",
        "showlegend": True,
    })

    return PlotlyChart(
        chart_type="pareto",
        data=traces,
        layout=_base_layout(
            title={"text": title},
            xaxis={"title": "", "gridcolor": "#374151"},
            yaxis={"title": yaxis_title, "gridcolor": "#374151"},
            yaxis2={
                "title": "Cumulative %",
                "overlaying": "y",
                "side": "right",
                "range": [0, 105],
                "gridcolor": "#374151",
                "ticksuffix": "%",
            },
            legend={"x": 0.7, "y": 1.1, "orientation": "h", "bgcolor": "rgba(0,0,0,0)"},
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Normal Probability Plot (Q-Q)
# ---------------------------------------------------------------------------

def probability_plot(
    values: Sequence[float],
    title: str = "Normal Probability Plot",
) -> PlotlyChart:
    """Q-Q plot against normal distribution."""
    from scipy import stats

    arr = np.array(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    arr_sorted = np.sort(arr)
    n = len(arr_sorted)
    theoretical = stats.norm.ppf(np.arange(1, n + 1) / (n + 1))

    # Reference line
    slope, intercept = np.polyfit(theoretical, arr_sorted, 1)
    ref_x = [float(theoretical.min()), float(theoretical.max())]
    ref_y = [slope * ref_x[0] + intercept, slope * ref_x[1] + intercept]

    traces: list[dict] = [
        {
            "type": "scatter",
            "x": theoretical.tolist(),
            "y": arr_sorted.tolist(),
            "mode": "markers",
            "name": "Data",
            "marker": {"color": COLORS["primary"], "size": 6},
        },
        {
            "type": "scatter",
            "x": ref_x,
            "y": ref_y,
            "mode": "lines",
            "name": "Reference Line",
            "line": {"color": COLORS["danger"], "width": 2, "dash": "dash"},
        },
    ]

    return PlotlyChart(
        chart_type="probability",
        data=traces,
        layout=_base_layout(
            title={"text": title},
            xaxis={"title": "Theoretical Quantiles", "gridcolor": "#374151"},
            yaxis={"title": "Sample Quantiles", "gridcolor": "#374151"},
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Control Chart (generic)
# ---------------------------------------------------------------------------

def control_chart(
    values: Sequence[float],
    center_line: float,
    ucl: float,
    lcl: float,
    title: str = "Control Chart",
    yaxis_title: str = "Value",
    point_labels: Sequence[str] | None = None,
    violations: list[int] | None = None,
) -> PlotlyChart:
    """Generic control chart with center line, UCL, LCL, and violation markers."""
    n = len(values)
    x_vals = list(point_labels) if point_labels else list(range(1, n + 1))

    traces: list[dict] = [
        # Data points
        {
            "type": "scatter",
            "x": x_vals,
            "y": list(values),
            "mode": "lines+markers",
            "name": "Data",
            "line": {"color": COLORS["primary"], "width": 1.5},
            "marker": {"size": 5, "color": COLORS["primary"]},
        },
        # Center line
        {
            "type": "scatter",
            "x": [x_vals[0], x_vals[-1]] if x_vals else [],
            "y": [center_line, center_line],
            "mode": "lines",
            "name": f"CL = {center_line:.4f}",
            "line": {"color": COLORS["success"], "width": 2},
        },
        # UCL
        {
            "type": "scatter",
            "x": [x_vals[0], x_vals[-1]] if x_vals else [],
            "y": [ucl, ucl],
            "mode": "lines",
            "name": f"UCL = {ucl:.4f}",
            "line": {"color": COLORS["danger"], "width": 1.5, "dash": "dash"},
        },
        # LCL
        {
            "type": "scatter",
            "x": [x_vals[0], x_vals[-1]] if x_vals else [],
            "y": [lcl, lcl],
            "mode": "lines",
            "name": f"LCL = {lcl:.4f}",
            "line": {"color": COLORS["danger"], "width": 1.5, "dash": "dash"},
        },
    ]

    # Highlight violations
    if violations:
        viol_x = [x_vals[i] for i in violations if i < n]
        viol_y = [values[i] for i in violations if i < n]
        traces.append({
            "type": "scatter",
            "x": viol_x,
            "y": viol_y,
            "mode": "markers",
            "name": "Out of Control",
            "marker": {"color": COLORS["danger"], "size": 10, "symbol": "diamond"},
        })

    return PlotlyChart(
        chart_type="control_chart",
        data=traces,
        layout=_base_layout(
            title={"text": title},
            xaxis={"title": "Observation", "gridcolor": "#374151"},
            yaxis={"title": yaxis_title, "gridcolor": "#374151"},
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Heatmap (for correlation matrices)
# ---------------------------------------------------------------------------

def heatmap(
    matrix: list[list[float]],
    labels: Sequence[str],
    title: str = "Correlation Matrix",
    colorscale: str = "RdBu_r",
) -> PlotlyChart:
    """Heatmap for correlation or association matrices."""
    # Add text annotations
    text = [[f"{val:.3f}" for val in row] for row in matrix]

    traces: list[dict] = [{
        "type": "heatmap",
        "z": matrix,
        "x": list(labels),
        "y": list(labels),
        "text": text,
        "texttemplate": "%{text}",
        "colorscale": colorscale,
        "zmin": -1,
        "zmax": 1,
        "colorbar": {"title": "r"},
    }]

    return PlotlyChart(
        chart_type="heatmap",
        data=traces,
        layout=_base_layout(
            title={"text": title},
            xaxis={"gridcolor": "#374151", "side": "bottom"},
            yaxis={"gridcolor": "#374151", "autorange": "reversed"},
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Residual plots (for regression)
# ---------------------------------------------------------------------------

def residual_plots(
    fitted: Sequence[float],
    residuals: Sequence[float],
    title: str = "Residual Analysis",
) -> list[PlotlyChart]:
    """Generate residuals vs fitted and histogram of residuals."""
    charts = [
        scatter(
            x=fitted,
            y=residuals,
            title=f"{title} — Residuals vs Fitted",
            xaxis_title="Fitted Values",
            yaxis_title="Residuals",
            trendline={"x": [min(fitted), max(fitted)], "y": [0, 0], "name": "Zero Line"},
            name="Residuals",
        ),
        histogram(
            values=residuals,
            name="Residuals",
            title=f"{title} — Histogram of Residuals",
            xaxis_title="Residual",
            show_normal_curve=True,
        ),
    ]
    return charts


# ---------------------------------------------------------------------------
# Main Effects Plot (for DOE)
# ---------------------------------------------------------------------------

def main_effects_plot(
    factor_names: Sequence[str],
    factor_levels: dict[str, list],
    factor_means: dict[str, list[float]],
    title: str = "Main Effects Plot",
    yaxis_title: str = "Mean Response",
) -> PlotlyChart:
    """Main effects plot for factorial experiments."""
    traces: list[dict] = []
    for i, factor in enumerate(factor_names):
        levels = factor_levels[factor]
        means = factor_means[factor]
        traces.append({
            "type": "scatter",
            "x": [f"{factor}\n{lvl}" for lvl in levels],
            "y": means,
            "mode": "lines+markers",
            "name": factor,
            "line": {"color": PALETTE[i % len(PALETTE)], "width": 2},
            "marker": {"size": 8},
        })

    return PlotlyChart(
        chart_type="main_effects",
        data=traces,
        layout=_base_layout(
            title={"text": title},
            xaxis={"title": "Factor Levels", "gridcolor": "#374151"},
            yaxis={"title": yaxis_title, "gridcolor": "#374151"},
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Interaction Plot (for DOE / two-way ANOVA)
# ---------------------------------------------------------------------------

def interaction_plot(
    x_levels: Sequence[str],
    trace_levels: Sequence[str],
    means: dict[str, list[float]],
    title: str = "Interaction Plot",
    xaxis_title: str = "Factor A",
    yaxis_title: str = "Mean Response",
    trace_name: str = "Factor B",
) -> PlotlyChart:
    """Interaction plot for two-factor analysis."""
    traces: list[dict] = []
    for i, level in enumerate(trace_levels):
        traces.append({
            "type": "scatter",
            "x": list(x_levels),
            "y": means[level],
            "mode": "lines+markers",
            "name": f"{trace_name}={level}",
            "line": {"color": PALETTE[i % len(PALETTE)], "width": 2},
            "marker": {"size": 8},
        })

    return PlotlyChart(
        chart_type="interaction",
        data=traces,
        layout=_base_layout(
            title={"text": title},
            xaxis={"title": xaxis_title, "gridcolor": "#374151"},
            yaxis={"title": yaxis_title, "gridcolor": "#374151"},
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Capability Histogram
# ---------------------------------------------------------------------------

def capability_histogram(
    values: Sequence[float],
    lsl: float | None = None,
    usl: float | None = None,
    target: float | None = None,
    title: str = "Process Capability",
) -> PlotlyChart:
    """Histogram with specification limits for capability analysis."""
    chart = histogram(values, name="Process Data", title=title, show_normal_curve=True)

    # Add spec limit lines
    y_max_est = len(values) / 5  # rough estimate for line height
    if lsl is not None:
        chart.data.append({
            "type": "scatter",
            "x": [lsl, lsl],
            "y": [0, y_max_est],
            "mode": "lines",
            "name": f"LSL = {lsl}",
            "line": {"color": COLORS["danger"], "width": 2, "dash": "dot"},
        })
    if usl is not None:
        chart.data.append({
            "type": "scatter",
            "x": [usl, usl],
            "y": [0, y_max_est],
            "mode": "lines",
            "name": f"USL = {usl}",
            "line": {"color": COLORS["danger"], "width": 2, "dash": "dot"},
        })
    if target is not None:
        chart.data.append({
            "type": "scatter",
            "x": [target, target],
            "y": [0, y_max_est],
            "mode": "lines",
            "name": f"Target = {target}",
            "line": {"color": COLORS["success"], "width": 2, "dash": "dashdot"},
        })

    return chart
