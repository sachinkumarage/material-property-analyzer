"""
visualizer.py
-------------
Turns the numbers in our materials table into charts, using matplotlib.

A picture of a bar chart tells you in one glance what a table of
numbers takes a minute to read - especially useful when comparing many
materials at once.

Color choices below follow a simple rule: one fixed color per material
category (so "Titanium Alloys" is always the same color across charts),
and a single blue hue shaded light-to-dark for "ranking" charts where we
are showing one continuous quantity from best to worst.

With 17 categories, no single flat palette stays easy to read - human
color vision reliably tells apart roughly 8 hues side by side, not 17.
Instead, categories are grouped by material family and given shades of
the SAME hue: every steel is a shade of blue, every light structural
metal (aluminum/titanium/magnesium) is a shade of teal/green, and so
on. The legend then reads as clusters of related materials rather than
17 arbitrary colors.
"""

import os

import matplotlib.pyplot as plt

from src.calculations import add_calculated_columns

# Fixed color per material category, so the same category always reads
# as the same color across every chart in this project (identity should
# never shift just because a filter changed which categories are shown).
# Grouped by material family (see module docstring above):
CATEGORY_COLORS = {
    # Ferrous metals (iron-based) -> blue family
    "Carbon Steels": "#1f4e8c",
    "Stainless Steels": "#3d7ebf",
    "Tool Steels": "#6badd6",
    "Cast Irons": "#9fcae1",
    # Light structural metals -> teal/green family
    "Aluminum Alloys": "#1b9e77",
    "Titanium Alloys": "#3fbf9f",
    "Magnesium Alloys": "#7fd8c5",
    # Copper & nickel alloys -> warm brass/copper family
    "Copper Alloys": "#d2691e",
    "Nickel Alloys": "#b8860b",
    # Hard, brittle inorganics -> purple family
    "Ceramics": "#7b3fa0",
    "Glass": "#b39ddb",
    # Organic-chemistry solids -> pink/magenta family
    "Polymers": "#e0559b",
    "Elastomers": "#f4a6c6",
    # Engineered fiber/matrix materials -> red (stands alone: distinct
    # performance role from every other family)
    "Composites": "#d62728",
    # Naturally occurring / mineral-aggregate materials -> brown/gray family
    "Wood": "#8c5a2b",
    "Concrete": "#9e9e9e",
    "Natural Materials": "#c9a066",
}
DEFAULT_COLOR = "#898781"  # muted gray fallback for any unlisted category

# Single-hue blue ramp (light -> dark) used for "best to worst" bar charts,
# where color encodes rank rather than category identity.
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# Shared chart styling so every figure in this project looks consistent.
GRID_COLOR = "#e1e0d9"
AXIS_COLOR = "#c3c2b7"
TEXT_COLOR = "#0b0b0b"
MUTED_TEXT = "#52514e"


def _category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, DEFAULT_COLOR)


def _style_axes(ax):
    """Apply the shared, low-key grid/axis styling used across charts."""
    ax.set_facecolor("#fcfcfb")
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(AXIS_COLOR)
    ax.tick_params(colors=MUTED_TEXT)


def plot_strength_to_weight_ranking(df, output_path: str, top_n: int = 10):
    """
    Horizontal bar chart ranking materials by strength-to-weight ratio
    (specific strength), best at the top.

    This is the single most useful chart for picking a material when
    weight matters - a quick visual answer to "what gives me the most
    strength per gram?".
    """
    data = add_calculated_columns(df)
    ranked = data.sort_values("strength_to_weight_ratio", ascending=True).tail(top_n)

    fig, ax = plt.subplots(figsize=(9, max(4, top_n * 0.5)))

    # Shade bars light-to-dark along the blue ramp so the eye reads the
    # gradient as "rank", from lowest (light) to highest (dark).
    n = len(ranked)
    colors = [BLUE_RAMP[min(int(i / n * len(BLUE_RAMP)), len(BLUE_RAMP) - 1)] for i in range(n)]

    bars = ax.barh(ranked["name"], ranked["strength_to_weight_ratio"], color=colors, zorder=3)
    ax.bar_label(bars, fmt="%.0f", padding=4, color=TEXT_COLOR, fontsize=9)

    ax.set_xlabel("Strength-to-weight ratio  (MPa per g/cm³)", color=MUTED_TEXT)
    ax.set_title("Specific Strength: Which Material Gives the Most\nStrength Per Unit of Weight?",
                 color=TEXT_COLOR, fontsize=13, fontweight="bold", loc="left")
    _style_axes(ax)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return fig


def plot_strength_vs_density(df, output_path: str, max_labels: int = 30):
    """
    Scatter plot of tensile strength vs. density, one dot per material,
    colored by category.

    Materials in the upper-left of this chart (high strength, low
    density) have the best specific strength - this is the classic
    "materials selection chart" engineers use (inspired by Ashby charts).

    Parameters
    ----------
    max_labels : with a database of 100+ materials, printing every
                 material's name next to its dot makes the chart
                 unreadable. Point labels are only drawn when there are
                 max_labels or fewer materials being plotted; above that,
                 dots are still colored and grouped by category, just
                 without individual name labels.
    """
    data = df.copy()

    fig, ax = plt.subplots(figsize=(10, 7))

    # Plot one series per category so the legend lists identities, not
    # a single generic "materials" blob - keeps color tied to category.
    for category, group in data.groupby("category"):
        ax.scatter(
            group["density_g_cm3"],
            group["tensile_strength_mpa"],
            label=category,
            color=_category_color(category),
            s=50,
            edgecolors="white",
            linewidths=0.6,
            zorder=3,
        )

    # Label each point with its material name so individual materials
    # are identifiable without hovering (this is a static image) - but
    # only when there are few enough points for labels to stay readable.
    if len(data) <= max_labels:
        for _, row in data.iterrows():
            ax.annotate(
                row["name"],
                (row["density_g_cm3"], row["tensile_strength_mpa"]),
                textcoords="offset points",
                xytext=(6, 4),
                fontsize=7,
                color=MUTED_TEXT,
            )

    ax.set_xlabel("Density (g/cm³) - lower is lighter", color=MUTED_TEXT)
    ax.set_ylabel("Tensile strength (MPa) - higher is stronger", color=MUTED_TEXT)
    ax.set_title("Materials Selection Chart: Strength vs. Density",
                 color=TEXT_COLOR, fontsize=13, fontweight="bold", loc="left")
    _style_axes(ax)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8, zorder=0)

    # With up to 17 categories in the legend, place it outside the plot
    # area so it never overlaps data points.
    legend = ax.legend(
        title="Category", frameon=False, loc="upper left",
        bbox_to_anchor=(1.01, 1.0), fontsize=8,
    )
    legend.get_title().set_color(MUTED_TEXT)
    for text in legend.get_texts():
        text.set_color(MUTED_TEXT)

    fig.tight_layout()
    # bbox_inches="tight" makes sure the legend (placed outside the axes
    # above) is fully included in the saved image instead of being cut off.
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return fig


def plot_material_comparison(df, names: list, output_path: str):
    """
    Grouped bar chart comparing a handful of hand-picked materials
    across three properties: strength-to-weight, stiffness-to-weight,
    and cost per unit strength (each normalized to 0-100 so they can
    share one axis fairly).

    Normalizing (scaling each property to the same range) is necessary
    here because the three properties have very different units and
    magnitudes - without it, one property would visually dominate the
    chart even if it isn't more "important".
    """
    data = add_calculated_columns(df)
    lower_names = [n.lower() for n in names]
    subset = data[data["name"].str.lower().isin(lower_names)].copy()

    properties = {
        "Specific strength": "strength_to_weight_ratio",
        "Specific stiffness": "stiffness_to_weight_ratio",
        "Cost efficiency": "cost_per_unit_strength",  # lower raw value is better
    }

    # Normalize each property to a 0-100 scale so very different units
    # (MPa per g/cm3 vs. USD per MPa) can share one chart fairly.
    normalized = {}
    for label, column in properties.items():
        values = subset[column]
        if label == "Cost efficiency":
            # Lower cost-per-strength is better, so invert the scale:
            # the cheapest material should score highest.
            normalized[label] = 100 * (values.max() - values) / (values.max() - values.min())
        else:
            normalized[label] = 100 * (values - values.min()) / (values.max() - values.min())

    fig, ax = plt.subplots(figsize=(9, 6))

    bar_width = 0.25
    x_positions = range(len(subset))
    colors = ["#2a78d6", "#1baf7a", "#eda100"]

    for i, label in enumerate(properties):
        offsets = [x + (i - 1) * bar_width for x in x_positions]
        ax.bar(offsets, normalized[label], width=bar_width, label=label,
               color=colors[i], zorder=3)

    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(subset["name"], rotation=15, ha="right", color=MUTED_TEXT)
    ax.set_ylabel("Normalized score (0-100, higher is better)", color=MUTED_TEXT)
    ax.set_title("Side-by-Side Material Comparison",
                 color=TEXT_COLOR, fontsize=13, fontweight="bold", loc="left")
    _style_axes(ax)

    legend = ax.legend(frameon=False, loc="upper right")
    for text in legend.get_texts():
        text.set_color(MUTED_TEXT)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return fig


def generate_all_charts(df, output_dir: str, compare_names: list = None):
    """Convenience function: generate every chart this project supports
    and save them into output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    plot_strength_to_weight_ranking(
        df, os.path.join(output_dir, "strength_to_weight_ranking.png")
    )
    plot_strength_vs_density(
        df, os.path.join(output_dir, "strength_vs_density.png")
    )

    if compare_names:
        plot_material_comparison(
            df, compare_names, os.path.join(output_dir, "material_comparison.png")
        )
