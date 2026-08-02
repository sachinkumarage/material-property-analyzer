"""
cli.py
------
An interactive command-line interface for the material property
analyzer. From one menu, a user can:

    1. Run the Part 2 material selector - answer a few plain-English
       questions about an engineering goal and get a ranked shortlist.
    2. Run the Version 4 search & filter tool - look up materials by
       name/category/subcategory, filter by property ranges, and sort
       the results.
    3. View Version 4 database statistics - a quick summary of the
       whole materials catalog.

No Python knowledge required. Run it directly with:
    python -m src.cli
or through the main program with:
    python main.py --select
"""

from src.database import MaterialDatabase
from src.selection_engine import SelectionEngine, GOAL_PRESETS
from src.search import SearchEngine, RANGE_FILTERS, SORT_OPTIONS, CORROSION_RESISTANCE_ORDER, print_statistics

DATA_PATH = "data/materials.csv"

# Plain-English explanations shown next to each goal preset, so a user
# doesn't need to already know what "specific stiffness" means.
GOAL_DESCRIPTIONS = {
    "lightweight_strength": (
        "Lightweight & strong - best strength-to-weight ratio "
        "(e.g. aircraft parts, drones, bike frames)"
    ),
    "rigid_structure": (
        "Rigid & stiff - best stiffness-to-weight ratio "
        "(e.g. beams, brackets, tooling that must resist bending)"
    ),
    "budget_friendly": (
        "Budget-friendly - most strength for the lowest cost "
        "(e.g. mass-produced or cost-sensitive parts)"
    ),
    "balanced": "Balanced - an even mix of strength, stiffness, and cost",
}

# Plain-English prompts for each range filter Version 4 supports, keyed
# by the same names SearchEngine.search() expects as keyword arguments.
RANGE_FILTER_PROMPTS = {
    "density_range": "Density (g/cm3)",
    "yield_strength_range": "Yield strength (MPa)",
    "tensile_strength_range": "Tensile strength (MPa)",
    "elastic_modulus_range": "Elastic modulus / stiffness (GPa)",
    "thermal_conductivity_range": "Thermal conductivity (W/m*K)",
    "electrical_conductivity_range": "Electrical conductivity (%IACS)",
    "melting_point_range": "Melting point (C)",
    "relative_cost_range": "Cost (USD/kg)",
}


# ---------------------------------------------------------------------
# Small shared input helpers
# ---------------------------------------------------------------------

def ask_choice(prompt: str, options: list) -> str:
    """Show a numbered list of options and return the one the user picks."""
    print(f"\n{prompt}")
    for i, option in enumerate(options, start=1):
        print(f"  {i}. {option}")

    while True:
        choice = input(f"Choose (1-{len(options)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Please enter a number from the list above.")


def ask_float(prompt: str):
    """Ask for an optional number. An empty answer means 'no limit'."""
    raw = input(prompt).strip()
    if raw == "":
        return None
    try:
        return float(raw)
    except ValueError:
        print("That's not a number - skipping this filter.")
        return None


def ask_text(prompt: str):
    """Ask for optional free text. An empty answer means 'skip'."""
    raw = input(prompt).strip()
    return raw or None


def ask_range(label: str):
    """Ask for an optional (min, max) pair. Blank on either side = no limit."""
    minimum = ask_float(f"  {label} - minimum (blank = no limit): ")
    maximum = ask_float(f"  {label} - maximum (blank = no limit): ")
    if minimum is None and maximum is None:
        return None
    return (minimum, maximum)


def ask_categories(available_categories: list):
    """Ask which material categories to include (blank = all of them)."""
    print(f"\nAvailable categories: {', '.join(available_categories)}")
    raw = input("Limit to which categories? (comma-separated, blank = all): ").strip()
    if raw == "":
        return None
    return [c.strip() for c in raw.split(",") if c.strip()]


# ---------------------------------------------------------------------
# Part 2: goal-based material selector
# ---------------------------------------------------------------------

def print_selection_results(ranked) -> None:
    """Print a ranked shortlist from the selection engine."""
    if ranked.empty:
        print("\nNo materials matched those requirements - try loosening a filter.")
        return

    print("\nTop matches:")
    print("-" * 60)
    for rank, row in enumerate(ranked.itertuples(index=False), start=1):
        print(f"{rank}. {row.name} ({row.category}) - match score {row.match_score:.1f}/100")
        print(
            f"     density {row.density_g_cm3:.2f} g/cm3, "
            f"tensile strength {row.tensile_strength_mpa:.0f} MPa, "
            f"cost ${row.cost_usd_per_kg:.2f}/kg"
        )


def run_selector(db) -> None:
    """Interactive loop for the goal-based material selection engine."""
    engine = SelectionEngine(db.data)
    categories = sorted(db.data["category"].unique())

    while True:
        goals = list(GOAL_PRESETS.keys())
        goal_labels = [GOAL_DESCRIPTIONS[g] for g in goals]
        goal = goals[goal_labels.index(ask_choice("What matters most for your part?", goal_labels))]

        selected_categories = ask_categories(categories)
        max_density = ask_float("Maximum density in g/cm3 (blank = no limit): ")
        max_cost = ask_float("Maximum cost in USD/kg (blank = no limit): ")
        min_tensile_strength = ask_float("Minimum tensile strength in MPa (blank = no limit): ")

        ranked = engine.select(
            goal=goal,
            top_n=5,
            categories=selected_categories,
            max_density=max_density,
            max_cost=max_cost,
            min_tensile_strength=min_tensile_strength,
        )
        print_selection_results(ranked)

        if input("\nRun another selection? (y/n): ").strip().lower() != "y":
            break


# ---------------------------------------------------------------------
# Version 4: search, filter & sort
# ---------------------------------------------------------------------

def print_search_results(results) -> None:
    """Print a table of search results in a friendly, readable format."""
    if results.empty:
        print("\nNo materials matched your search - try loosening a filter.")
        return

    print(f"\nFound {len(results)} matching material(s):")
    print("-" * 60)
    for rank, row in enumerate(results.itertuples(index=False), start=1):
        print(f"{rank}. {row.name} ({row.category} / {row.subcategory})")
        print(
            f"     density {row.density_g_cm3:.2f} g/cm3, "
            f"tensile strength {row.tensile_strength_mpa:.0f} MPa, "
            f"stiffness {row.elastic_modulus_gpa:.0f} GPa, "
            f"cost ${row.cost_usd_per_kg:.2f}/kg, "
            f"corrosion resistance {row.corrosion_resistance}"
        )


def run_search(db) -> None:
    """Interactive loop for the Version 4 search & filter tool."""
    engine = SearchEngine(db.data)

    while True:
        print("\n--- Search ---")
        name = ask_text("Search by name (blank = skip): ")
        category = ask_text("Search by category (blank = skip): ")
        subcategory = ask_text("Search by subcategory (blank = skip): ")

        print("\n--- Filters (leave both blank on a filter to skip it) ---")
        ranges = {}
        if input("Add property range filters? (y/n): ").strip().lower() == "y":
            for filter_name, label in RANGE_FILTER_PROMPTS.items():
                value_range = ask_range(label)
                if value_range is not None:
                    ranges[filter_name] = value_range

        corrosion_resistance = None
        if input("Require a minimum corrosion resistance? (y/n): ").strip().lower() == "y":
            corrosion_resistance = ask_choice(
                "Minimum acceptable corrosion resistance:", CORROSION_RESISTANCE_ORDER
            )

        sort_by = None
        if input("Sort the results? (y/n): ").strip().lower() == "y":
            sort_by = ask_choice("Sort by:", sorted(SORT_OPTIONS))

        results = engine.search(
            name=name,
            category=category,
            subcategory=subcategory,
            corrosion_resistance=corrosion_resistance,
            sort_by=sort_by,
            **ranges,
        )
        print_search_results(results)

        if input("\nRun another search? (y/n): ").strip().lower() != "y":
            break


# ---------------------------------------------------------------------
# Version 4: database statistics
# ---------------------------------------------------------------------

def run_statistics(db) -> None:
    """Show a one-shot summary of the whole materials database."""
    print_statistics(db.data)


# ---------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------

MENU_OPTIONS = [
    "Material selector (pick the best material for a goal)",
    "Search & filter materials",
    "Database statistics",
    "Quit",
]


def run() -> None:
    """Main interactive menu tying together every CLI feature."""
    print("=" * 60)
    print("Material Property Analyzer - Version 4")
    print("=" * 60)

    db = MaterialDatabase(DATA_PATH)

    while True:
        choice = ask_choice("What would you like to do?", MENU_OPTIONS)

        if choice == MENU_OPTIONS[0]:
            run_selector(db)
        elif choice == MENU_OPTIONS[1]:
            run_search(db)
        elif choice == MENU_OPTIONS[2]:
            run_statistics(db)
        else:
            break

    print("\nGoodbye!")


if __name__ == "__main__":
    run()
