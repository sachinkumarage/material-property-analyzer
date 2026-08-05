"""
interactive_charts.py
----------------------
Version 6 upgrade: interactive Plotly "Ashby charts" for the Streamlit
dashboard.

Materials engineering concept: ASHBY CHARTS
-----------------------------------------------
An Ashby chart (named after materials scientist Mike Ashby) plots one
material property against another - usually on log-log axes, since
properties like density and strength span several orders of magnitude
across material families - so that whole classes of materials cluster
into visible regions. Engineers scan the chart for the region that
matches their constraints (e.g. "upper-left = strong and light") instead
of comparing numbers row by row in a table.

visualizer.py already draws one static version of this chart with
matplotlib for the CLI. This module reimplements the same idea with
Plotly so the Streamlit dashboard gets hover tooltips, clickable
legend entries (to hide/show a category), a log/linear axis toggle,
and a built-in PNG export button - without touching the matplotlib
code the CLI depends on.

Every chart here is built from the same underlying materials table and
color palette used elsewhere in the project (see CATEGORY_COLORS in
visualizer.py), so a category reads as the same color whether you're
looking at a static chart from `python main.py` or an interactive one
in the dashboard.
"""

import pandas as pd
import plotly.graph_objects as go

from src.calculations import add_calculated_columns
from src.visualizer import CATEGORY_COLORS, DEFAULT_COLOR, TEXT_COLOR, AXIS_COLOR

# The hover tooltip always renders on a light box (see HOVERLABEL below)
# regardless of Streamlit's light/dark theme, so its text must be a
# fixed dark color rather than inheriting the page's theme color -
# otherwise dark-theme white text lands on the same white box and
# disappears. Reuses the same ink/border colors as the static
# matplotlib charts (visualizer.TEXT_COLOR / AXIS_COLOR) so the
# tooltip matches the rest of the project.
HOVERLABEL = dict(
    bgcolor="#fcfcfb",
    bordercolor=AXIS_COLOR,
    font=dict(color=TEXT_COLOR, size=12),
)

# Columns shown in every tooltip, in order, alongside the material name.
# (label, column, format spec, unit)
HOVER_FIELDS = [
    ("Category", "category", None, ""),
    ("Subcategory", "subcategory", None, ""),
    ("Density", "density_g_cm3", ".2f", " g/cm³"),
    ("Yield strength", "yield_strength_mpa", ".0f", " MPa"),
    ("Tensile strength (UTS)", "tensile_strength_mpa", ".0f", " MPa"),
    ("Young's modulus", "elastic_modulus_gpa", ".0f", " GPa"),
    ("Relative cost", "relative_cost_index", ".1f", "x carbon steel"),
]

# The six engineering charts this module supports, keyed by a short slug.
# Following the same "Y vs. X" naming/axis convention as
# visualizer.plot_strength_vs_density: the first-named property is the
# y-axis, the second is the x-axis.
ASHBY_CHARTS = {
    "strength_vs_density": {
        "label": "Strength vs. Density",
        "x": "density_g_cm3",
        "y": "tensile_strength_mpa",
        "x_label": "Density (g/cm³)",
        "y_label": "Tensile Strength (MPa)",
    },
    "modulus_vs_density": {
        "label": "Young's Modulus vs. Density",
        "x": "density_g_cm3",
        "y": "elastic_modulus_gpa",
        "x_label": "Density (g/cm³)",
        "y_label": "Young's Modulus (GPa)",
    },
    "thermal_conductivity_vs_density": {
        "label": "Thermal Conductivity vs. Density",
        "x": "density_g_cm3",
        "y": "thermal_conductivity_w_mk",
        "x_label": "Density (g/cm³)",
        "y_label": "Thermal Conductivity (W/m·K)",
    },
    "cost_vs_strength": {
        "label": "Cost vs. Strength",
        "x": "tensile_strength_mpa",
        "y": "cost_usd_per_kg",
        "x_label": "Tensile Strength (MPa)",
        "y_label": "Cost (USD/kg)",
    },
    "specific_strength_vs_cost": {
        "label": "Specific Strength vs. Cost",
        "x": "cost_usd_per_kg",
        "y": "strength_to_weight_ratio",
        "x_label": "Cost (USD/kg)",
        "y_label": "Specific Strength (MPa per g/cm³)",
    },
    "specific_stiffness_vs_cost": {
        "label": "Specific Stiffness vs. Cost",
        "x": "cost_usd_per_kg",
        "y": "stiffness_to_weight_ratio",
        "x_label": "Cost (USD/kg)",
        "y_label": "Specific Stiffness (MPa per g/cm³)",
    },
}


def _category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, DEFAULT_COLOR)


def _hover_template(extra_lines: list = None) -> str:
    """
    Build the shared "<b>name</b> / property list" hover template.

    extra_lines : optional lines inserted right after the bold name -
        e.g. the one value a chart's axis already encodes (specific
        strength for the ranking bars) but that isn't otherwise in
        HOVER_FIELDS.
    """
    lines = ["<b>%{text}</b>"]
    if extra_lines:
        lines.extend(extra_lines)
    for i, (label, _column, fmt, unit) in enumerate(HOVER_FIELDS):
        value = f"%{{customdata[{i}]{':' + fmt if fmt else ''}}}"
        lines.append(f"{label}: {value}{unit}")
    lines.append("<extra></extra>")
    return "<br>".join(lines)


def build_ashby_figure(
    df: pd.DataFrame,
    chart_key: str,
    log_x: bool = True,
    log_y: bool = True,
) -> go.Figure:
    """
    Build an interactive Plotly Ashby chart for one of the presets in
    ASHBY_CHARTS.

    One trace is created per material category so that Plotly's legend
    doubles as a show/hide control for free: clicking a category name
    toggles that category's points, double-clicking isolates it.

    Parameters
    ----------
    df : the (already filtered) materials table to plot - reuse
         whatever SearchEngine.search() returned so the chart always
         matches the current search/filter selection.
    chart_key : one of the keys in ASHBY_CHARTS.
    log_x, log_y : whether each axis uses a logarithmic scale. Ashby
        charts are conventionally log-log, since properties like
        density and strength span several orders of magnitude across
        material families - but every value in this database is
        strictly positive, so a linear view is also safe if preferred.
    """
    if chart_key not in ASHBY_CHARTS:
        raise ValueError(f"Unknown chart '{chart_key}'. Choose from: {sorted(ASHBY_CHARTS)}")

    spec = ASHBY_CHARTS[chart_key]
    data = add_calculated_columns(df)
    hover_columns = [column for _label, column, _fmt, _unit in HOVER_FIELDS]
    hover_template = _hover_template()

    fig = go.Figure()

    for category in sorted(data["category"].unique()):
        group = data[data["category"] == category]
        fig.add_trace(
            go.Scatter(
                x=group[spec["x"]],
                y=group[spec["y"]],
                mode="markers",
                name=category,
                text=group["name"],
                customdata=group[hover_columns].to_numpy(),
                hovertemplate=hover_template,
                marker=dict(
                    size=11,
                    color=_category_color(category),
                    line=dict(width=1, color="white"),
                    opacity=0.85,
                ),
            )
        )

    fig.update_layout(
        title=dict(text=f"Ashby Chart: {spec['label']}", x=0.0, xanchor="left"),
        xaxis_title=spec["x_label"],
        yaxis_title=spec["y_label"],
        legend_title_text="Category<br><sup>click to hide/show</sup>",
        template="plotly_white",
        height=650,
        margin=dict(t=60, r=40, b=60, l=60),
        hoverlabel=HOVERLABEL,
    )
    fig.update_xaxes(type="log" if log_x else "linear", gridcolor="#e1e0d9")
    fig.update_yaxes(type="log" if log_y else "linear", gridcolor="#e1e0d9")

    return fig


def build_specific_strength_ranking_figure(
    df: pd.DataFrame,
    top_n: int = 10,
    log_x: bool = False,
) -> go.Figure:
    """
    Interactive counterpart to visualizer.plot_strength_to_weight_ranking:
    a horizontal bar chart ranking materials by strength-to-weight ratio
    (specific strength), best at the top.

    Same treatment as build_ashby_figure - one trace per category (so
    the legend doubles as a show/hide control), full-property hover
    tooltips, and a log/linear x-axis toggle.
    """
    data = add_calculated_columns(df)
    ranked = data.sort_values("strength_to_weight_ratio", ascending=True).tail(top_n)
    name_order = ranked["name"].tolist()

    hover_columns = [column for _label, column, _fmt, _unit in HOVER_FIELDS]
    hover_template = _hover_template(["Specific strength: %{x:.1f} MPa per g/cm³"])

    fig = go.Figure()

    for category in sorted(ranked["category"].unique()):
        group = ranked[ranked["category"] == category]
        fig.add_trace(
            go.Bar(
                x=group["strength_to_weight_ratio"],
                y=group["name"],
                orientation="h",
                name=category,
                text=group["name"],
                textposition="none",
                customdata=group[hover_columns].to_numpy(),
                hovertemplate=hover_template,
                marker=dict(
                    color=_category_color(category),
                    line=dict(width=1, color="white"),
                ),
            )
        )

    fig.update_layout(
        title=dict(
            text=f"Specific Strength Ranking (Top {len(ranked)})",
            x=0.0,
            xanchor="left",
        ),
        xaxis_title="Strength-to-weight ratio (MPa per g/cm³)",
        legend_title_text="Category<br><sup>click to hide/show</sup>",
        template="plotly_white",
        height=max(400, len(ranked) * 45),
        margin=dict(t=60, r=40, b=60, l=60),
        hoverlabel=HOVERLABEL,
        yaxis=dict(categoryorder="array", categoryarray=name_order),
        barmode="overlay",
    )
    fig.update_xaxes(type="log" if log_x else "linear", gridcolor="#e1e0d9")

    return fig


def png_export_config(chart_key: str) -> dict:
    """
    Plotly config that customizes the chart toolbar's built-in
    "Download plot as a png" button (requirement: exporting charts as
    PNG). No extra dependency needed - Plotly renders the PNG in the
    browser via the toolbar camera icon.
    """
    return {
        "toImageButtonOptions": {
            "format": "png",
            "filename": f"ashby_{chart_key}",
            "scale": 2,
        },
        "displaylogo": False,
    }
