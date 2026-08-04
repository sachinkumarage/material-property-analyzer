"""
app.py
------
Version 5: a Streamlit web dashboard for the Material Property Analyzer.

This file is a thin UI layer on top of the existing project modules -
every calculation, filter, search, comparison, and chart already lives
in src/ (see database.py, calculations.py, comparator.py, search.py,
and visualizer.py). app.py just wires those same functions up to
interactive widgets instead of a terminal menu, so the underlying
engineering logic only exists in one place.

Run it from the project root with:
    streamlit run app.py

The original command-line tools (`python main.py` and
`python main.py --select`) keep working exactly as before - this is an
additional interface, not a replacement.
"""

import os

import pandas as pd
import streamlit as st

from src.database import MaterialDatabase
from src.comparator import MaterialComparator
from src.search import SearchEngine, CORROSION_RESISTANCE_ORDER, get_statistics
from src.visualizer import (
    plot_strength_to_weight_ranking,
    plot_strength_vs_density,
    plot_material_comparison,
)
from src.interactive_charts import ASHBY_CHARTS, build_ashby_figure, png_export_config

DATA_PATH = os.path.join("data", "materials.csv")
OUTPUT_DIR = "output"
MAX_COMPARE = 3

st.set_page_config(
    page_title="Material Property Analyzer",
    page_icon="\U0001FA9B",
    layout="wide",
)


@st.cache_data
def load_raw_data(csv_path: str) -> pd.DataFrame:
    """Load the materials CSV once per session (cached for speed)."""
    return MaterialDatabase(csv_path).data


raw_data = load_raw_data(DATA_PATH)
search_engine = SearchEngine(raw_data)      # adds specific strength/stiffness/etc.
comparator = MaterialComparator(raw_data)   # adds the same derived columns
enriched_data = search_engine.data          # full table incl. every derived column

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------
# Header + summary cards
# ---------------------------------------------------------------------
st.title("Material Property Analyzer")
st.caption(
    "Version 6 - an interactive dashboard for searching, comparing, and "
    "selecting engineering materials, with interactive Ashby charts. "
    "Prefer the terminal? `python main.py --select` still works."
)

stats = get_statistics(raw_data)
card1, card2, card3, card4 = st.columns(4)
card1.metric("Total Materials", stats["total_materials"])
card2.metric("Categories", len(stats["category_counts"]))
card3.metric("Average Density", f"{stats['average_density_g_cm3']:.2f} g/cm³")
card4.metric("Strongest Material", stats["strongest_material"])

st.divider()

# ---------------------------------------------------------------------
# Sidebar: search & filters
# ---------------------------------------------------------------------
st.sidebar.header("Search & Filter")

search_text = st.sidebar.text_input(
    "Search by name", placeholder="e.g. Titanium, Steel, Carbon Fiber"
)

category_options = ["All"] + sorted(raw_data["category"].unique())
selected_category = st.sidebar.selectbox("Category", category_options)

if selected_category == "All":
    subcategory_options = ["All"] + sorted(raw_data["subcategory"].unique())
else:
    subcategory_options = ["All"] + sorted(
        raw_data.loc[raw_data["category"] == selected_category, "subcategory"].unique()
    )
selected_subcategory = st.sidebar.selectbox("Subcategory", subcategory_options)

density_min, density_max = float(raw_data["density_g_cm3"].min()), float(raw_data["density_g_cm3"].max())
density_range = st.sidebar.slider(
    "Density (g/cm³)",
    min_value=density_min, max_value=density_max, value=(density_min, density_max),
    help="Mass per unit volume - lower means lighter.",
)

strength_min, strength_max = float(raw_data["tensile_strength_mpa"].min()), float(raw_data["tensile_strength_mpa"].max())
strength_range = st.sidebar.slider(
    "Tensile Strength (MPa)",
    min_value=strength_min, max_value=strength_max, value=(strength_min, strength_max),
    help="Stress at which the material breaks.",
)

cost_min, cost_max = float(raw_data["cost_usd_per_kg"].min()), float(raw_data["cost_usd_per_kg"].max())
cost_range = st.sidebar.slider(
    "Cost (USD/kg)",
    min_value=cost_min, max_value=cost_max, value=(cost_min, cost_max),
)

corrosion_choice = st.sidebar.selectbox(
    "Minimum Corrosion Resistance", ["Any"] + CORROSION_RESISTANCE_ORDER
)

results = search_engine.search(
    name=search_text or None,
    category=None if selected_category == "All" else selected_category,
    subcategory=None if selected_subcategory == "All" else selected_subcategory,
    corrosion_resistance=None if corrosion_choice == "Any" else corrosion_choice,
    density_range=density_range,
    tensile_strength_range=strength_range,
    relative_cost_range=cost_range,
)

st.sidebar.caption(f"{len(results)} of {len(raw_data)} materials match")

# ---------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------
tab_browse, tab_charts, tab_compare = st.tabs(
    ["Search Results", "Charts", "Compare Materials"]
)

with tab_browse:
    st.subheader("Search Results")
    st.caption("Click a column header to sort.")

    if results.empty:
        st.warning("No materials match the current filters - try loosening one in the sidebar.")
    else:
        st.dataframe(results, width="stretch", hide_index=True)

        st.subheader("Material Details")
        selected_material = st.selectbox("Select a material to view all properties", results["name"])
        detail_row = enriched_data.loc[enriched_data["name"] == selected_material].iloc[0]

        detail_col, ratio_col = st.columns([2, 1])

        with detail_col:
            properties = detail_row[MaterialDatabase.REQUIRED_COLUMNS].astype(str).rename("Value")
            st.table(properties)

        with ratio_col:
            st.markdown("**Engineering Ratios**")
            st.metric(
                "Specific Strength", f"{detail_row['strength_to_weight_ratio']:.1f}",
                help="Tensile strength / density (MPa per g/cm³). Higher = more "
                     "strength per unit weight.",
            )
            st.metric(
                "Specific Stiffness", f"{detail_row['stiffness_to_weight_ratio']:.1f}",
                help="Elastic modulus / density (MPa per g/cm³). Higher = more "
                     "rigidity per unit weight.",
            )
            st.metric(
                "Relative Cost Index", f"{detail_row['relative_cost_index']:.1f}x",
                help="Cost relative to plain carbon steel (~$1/kg baseline).",
            )

with tab_charts:
    st.subheader("Charts")

    if results.empty:
        st.warning("No materials match the current filters - charts need at least one match.")
    else:
        st.caption("Charts reflect the materials currently matching your sidebar filters.")
        top_n = min(10, len(results))

        fig1 = plot_strength_to_weight_ranking(
            results, os.path.join(OUTPUT_DIR, "strength_to_weight_ranking.png"), top_n=top_n
        )
        st.pyplot(fig1)

        fig2 = plot_strength_vs_density(
            results, os.path.join(OUTPUT_DIR, "strength_vs_density.png")
        )
        st.pyplot(fig2)

        st.divider()
        st.subheader("Interactive Ashby Charts")
        st.caption(
            "Version 6 - hover a point for its full properties, click a "
            "category in the legend to hide/show it (double-click to "
            "isolate one), and use the camera icon in the chart toolbar "
            "to export it as a PNG. Reflects the same sidebar search & "
            "filter selection as the charts above."
        )

        chart_col, axis_col = st.columns([2, 1])
        with chart_col:
            chart_key = st.selectbox(
                "Chart",
                options=list(ASHBY_CHARTS.keys()),
                format_func=lambda key: ASHBY_CHARTS[key]["label"],
            )
        with axis_col:
            log_x = st.checkbox("Log X axis", value=True)
            log_y = st.checkbox("Log Y axis", value=True)

        ashby_fig = build_ashby_figure(results, chart_key, log_x=log_x, log_y=log_y)
        st.plotly_chart(
            ashby_fig,
            width="stretch",
            config=png_export_config(chart_key),
        )

with tab_compare:
    st.subheader("Compare Materials")
    st.caption(f"Pick up to {MAX_COMPARE} materials to compare side by side.")

    compare_names = st.multiselect(
        "Materials to compare",
        options=sorted(raw_data["name"]),
        max_selections=MAX_COMPARE,
    )

    if len(compare_names) < 2:
        st.info("Select at least two materials to see a comparison.")
    else:
        comparison_table = comparator.compare(
            compare_names,
            properties=[
                "name", "category", "density_g_cm3", "tensile_strength_mpa",
                "elastic_modulus_gpa", "cost_usd_per_kg",
                "strength_to_weight_ratio", "stiffness_to_weight_ratio",
                "relative_cost_index",
            ],
        ).rename(columns={
            "strength_to_weight_ratio": "specific_strength",
            "stiffness_to_weight_ratio": "specific_stiffness",
        })
        st.dataframe(comparison_table, width="stretch", hide_index=True)

        fig3 = plot_material_comparison(
            raw_data, compare_names, os.path.join(OUTPUT_DIR, "material_comparison.png")
        )
        st.pyplot(fig3)
