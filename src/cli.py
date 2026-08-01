"""
cli.py
------
An interactive command-line interface for the material selection
engine. Instead of writing Python, a user can answer a few plain-
English questions about their engineering goal and requirements, and
get back a ranked shortlist of materials.

Run it directly with:
    python -m src.cli
or through the main program with:
    python main.py --select
"""

from src.database import MaterialDatabase
from src.selection_engine import SelectionEngine, GOAL_PRESETS

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


def ask_goal() -> str:
    """Show the available selection goals and get the user's choice."""
    print("\nWhat matters most for your part?")
    goals = list(GOAL_PRESETS.keys())
    for i, goal in enumerate(goals, start=1):
        print(f"  {i}. {GOAL_DESCRIPTIONS[goal]}")

    while True:
        choice = input(f"Choose a goal (1-{len(goals)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(goals):
            return goals[int(choice) - 1]
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


def ask_categories(available_categories: list):
    """Ask which material categories to include (blank = all of them)."""
    print(f"\nAvailable categories: {', '.join(available_categories)}")
    raw = input("Limit to which categories? (comma-separated, blank = all): ").strip()
    if raw == "":
        return None
    return [c.strip() for c in raw.split(",") if c.strip()]


def print_results(ranked) -> None:
    """Print a ranked shortlist in a friendly, readable format."""
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


def run() -> None:
    """Main interactive loop for the material selection CLI."""
    print("=" * 60)
    print("Material Property Analyzer - Interactive Material Selector")
    print("=" * 60)

    db = MaterialDatabase(DATA_PATH)
    engine = SelectionEngine(db.data)
    categories = sorted(db.data["category"].unique())

    while True:
        goal = ask_goal()
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
        print_results(ranked)

        again = input("\nRun another search? (y/n): ").strip().lower()
        if again != "y":
            break

    print("\nGoodbye!")


if __name__ == "__main__":
    run()
