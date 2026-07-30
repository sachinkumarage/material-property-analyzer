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

Run it from the project's root folder with:
    python main.py
"""

import os

from src.database import MaterialDatabase
from src.calculations import add_calculated_columns
from src.comparator import MaterialComparator
from src.visualizer import generate_all_charts

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


def main():
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


if __name__ == "__main__":
    main()
