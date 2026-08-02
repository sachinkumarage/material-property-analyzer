"""
main.py
-------
Entry point for the Material Property Analyzer.

Running this script will:
    1. Load the materials database (data/materials.csv)
    2. Calculate strength-to-weight ratio and other engineering ratios
    3. Print a ranking of the best materials by specific strength
    4. Compare a few hand-picked materials side by side
    5. Generate matplotlib charts into the output/ folder
    6. Run the advanced material selection engine (Part 2) as a demo
    7. Run the Version 4 search & filter tool and database statistics
       as a demo

Run it from the project's root folder with:
    python main.py

Or skip straight to the interactive CLI (material selector, search &
filter, and database statistics) with:
    python main.py --select
"""

import argparse
import os

from src.database import MaterialDatabase
from src.calculations import add_calculated_columns
from src.comparator import MaterialComparator
from src.visualizer import generate_all_charts
from src.selection_engine import SelectionEngine
from src.search import SearchEngine, print_statistics

DATA_PATH = os.path.join("data", "materials.csv")
OUTPUT_DIR = "output"

# Materials we want to compare directly in this demo run. Feel free to
# change this list to any material names found in data/materials.csv.
MATERIALS_TO_COMPARE = [
    "Aluminum 6061-T6",
    "Titanium Ti-6Al-4V",
    "Carbon Fiber Composite (CFRP)",
    "Structural Steel A36",
]


def print_table(df, title: str):
    """Pretty-print a small DataFrame with a title above it."""
    print(f"\n{title}")
    print("-" * len(title))
    print(df.to_string(index=False))


def run_selection_demo(db):
    """
    Demonstrate the Part 2 advanced selection engine: filter materials
    by a hard requirement (max cost) and rank the survivors for a
    "lightweight & strong" engineering goal using the weighted scoring
    system in src/scoring.py.
    """
    engine = SelectionEngine(db.data)
    shortlist = engine.select(
        goal="lightweight_strength",
        max_cost=25.0,
        top_n=5,
    )
    print_table(
        shortlist,
        "Selection Engine Demo: Best 'Lightweight & Strong' Materials Under $25/kg",
    )


def run_search_demo(db):
    """
    Demonstrate the Version 4 search & filter tool: search for
    stainless steels, filter to a density/cost range, and sort the
    matches by specific strength - then print the whole-database
    statistics summary.
    """
    engine = SearchEngine(db.data)
    matches = engine.search(
        category="Steel",
        density_range=(None, 8.5),
        relative_cost_range=(None, 15.0),
        sort_by="specific_strength",
        top_n=5,
    )
    print_table(
        matches[["name", "category", "subcategory", "density_g_cm3", "tensile_strength_mpa", "cost_usd_per_kg"]],
        "Search Demo: Steels Under 8.5 g/cm3 and $15/kg, Sorted by Specific Strength",
    )

    print_statistics(db.data)


def main():
    parser = argparse.ArgumentParser(description="Material Property Analyzer")
    parser.add_argument(
        "--select",
        action="store_true",
        help="Skip the demo report and launch the interactive CLI instead "
             "(material selector, search & filter, database statistics)",
    )
    args = parser.parse_args()

    if args.select:
        from src.cli import run

        run()
        return

    # Step 1: load the raw materials database from CSV.
    db = MaterialDatabase(DATA_PATH)
    print(f"Loaded {len(db.list_materials())} materials from {DATA_PATH}")

    # Step 2: calculate strength-to-weight ratio (specific strength) and
    # the other derived engineering properties for every material.
    enriched = add_calculated_columns(db.data)

    # Step 3: rank materials by strength-to-weight ratio using the
    # comparator, and show the top 5 - the materials that give the most
    # strength per gram of weight.
    comparator = MaterialComparator(db.data)
    top_specific_strength = comparator.best_strength_to_weight(top_n=5)
    print_table(top_specific_strength, "Top 5 Materials by Strength-to-Weight Ratio")

    top_value = comparator.best_value(top_n=5)
    print_table(top_value, "Top 5 Most Cost-Effective Materials (per unit of strength)")

    # Step 4: compare a handful of specific materials side by side.
    comparison = comparator.compare(MATERIALS_TO_COMPARE)
    print_table(comparison, "Direct Comparison: Aluminum vs. Titanium vs. Carbon Fiber vs. Steel")

    # Step 5: generate charts and save them to the output/ folder.
    generate_all_charts(db.data, OUTPUT_DIR, compare_names=MATERIALS_TO_COMPARE)
    print(f"\nCharts saved to '{OUTPUT_DIR}/':")
    print("  - strength_to_weight_ranking.png")
    print("  - strength_vs_density.png")
    print("  - material_comparison.png")

    # Step 6: demo the Part 2 advanced material selection engine.
    run_selection_demo(db)

    # Step 7: demo the Version 4 search & filter tool and database statistics.
    run_search_demo(db)

    print("\nTip: run 'python main.py --select' for the interactive CLI "
          "(material selector, search & filter, and database statistics).")


if __name__ == "__main__":
    main()
