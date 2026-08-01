"""
selection_engine.py
--------------------
The Part 2 upgrade: an advanced material selection system that filters
the database down to materials that meet an engineer's hard
requirements, then ranks the survivors using the weighted scoring
system in scoring.py.

Materials engineering concept: THE SELECTION FUNNEL
---------------------------------------------------
Real material selection is a two-step funnel:

    1. FILTER - throw out anything that flat-out can't do the job
       (too heavy, too weak, too expensive, wrong category). These are
       hard "must have" requirements, not preferences.
    2. RANK   - among whatever survives filtering, find the best
       trade-off between competing goals (strength vs. stiffness vs.
       cost) using a weighted score.

This mirrors how professional engineers actually work: narrow the
field with hard limits first, then use judgment (expressed here as
weights) to pick the best of what's left.
"""

import pandas as pd

from src.scoring import DEFAULT_WEIGHTS, weighted_score

# Ready-made weight presets for common material-selection goals, so a
# user doesn't need to invent good weight values from scratch. Each
# preset is just a set of weights handed straight to weighted_score().
GOAL_PRESETS = {
    "lightweight_strength": {
        "specific_strength_score": 0.7,
        "specific_stiffness_score": 0.2,
        "cost_score": 0.1,
    },
    "rigid_structure": {
        "specific_strength_score": 0.2,
        "specific_stiffness_score": 0.7,
        "cost_score": 0.1,
    },
    "budget_friendly": {
        "specific_strength_score": 0.25,
        "specific_stiffness_score": 0.15,
        "cost_score": 0.6,
    },
    "balanced": DEFAULT_WEIGHTS,
}

# Columns shown in the final ranked shortlist: enough raw properties to
# sanity-check the recommendation, plus every score that went into it.
RESULT_COLUMNS = [
    "name",
    "category",
    "density_g_cm3",
    "tensile_strength_mpa",
    "elastic_modulus_gpa",
    "cost_usd_per_kg",
    "specific_strength_score",
    "specific_stiffness_score",
    "cost_score",
    "match_score",
]


def filter_materials(
    df: pd.DataFrame,
    categories: list = None,
    max_density: float = None,
    min_tensile_strength: float = None,
    min_yield_strength: float = None,
    min_elastic_modulus: float = None,
    max_cost: float = None,
) -> pd.DataFrame:
    """
    Narrow the materials table down to rows that meet every requirement
    given. Any requirement left as None is skipped (no restriction).

    Parameters
    ----------
    categories : only keep materials in these categories, e.g.
                 ["Metal", "Composite"].
    max_density : reject anything denser than this (g/cm3) - use when
                  weight is a hard constraint (e.g. a drone part).
    min_tensile_strength : reject anything weaker than this (MPa).
    min_yield_strength : reject anything that yields below this (MPa).
    min_elastic_modulus : reject anything less stiff than this (GPa).
    max_cost : reject anything pricier than this (USD/kg).
    """
    result = df.copy()

    if categories:
        lower_categories = [c.lower() for c in categories]
        result = result[result["category"].str.lower().isin(lower_categories)]

    if max_density is not None:
        result = result[result["density_g_cm3"] <= max_density]

    if min_tensile_strength is not None:
        result = result[result["tensile_strength_mpa"] >= min_tensile_strength]

    if min_yield_strength is not None:
        result = result[result["yield_strength_mpa"] >= min_yield_strength]

    if min_elastic_modulus is not None:
        result = result[result["elastic_modulus_gpa"] >= min_elastic_modulus]

    if max_cost is not None:
        result = result[result["cost_usd_per_kg"] <= max_cost]

    return result.reset_index(drop=True)


class SelectionEngine:
    """
    High-level entry point that ties filtering and scoring together to
    answer: "given these hard requirements and this goal, what's the
    best material for the job?"
    """

    def __init__(self, materials_df: pd.DataFrame):
        self.data = materials_df

    def select(
        self,
        weights: dict = None,
        goal: str = None,
        top_n: int = 5,
        **filter_kwargs,
    ) -> pd.DataFrame:
        """
        Filter the database by filter_kwargs (see filter_materials for
        the full list), then rank the survivors by a weighted score and
        return the top_n best matches.

        Parameters
        ----------
        goal : picks a ready-made weight preset from GOAL_PRESETS
               (e.g. "lightweight_strength", "rigid_structure",
               "budget_friendly", "balanced").
        weights : supply custom weights instead of a preset, e.g.
                  {"specific_strength_score": 0.5, "cost_score": 0.5}.
                  Ignored if `goal` is also given.
        top_n : how many top-ranked materials to return.
        **filter_kwargs : hard requirements passed straight through to
                           filter_materials(), e.g. max_cost=10,
                           categories=["Metal"].
        """
        if goal is not None:
            if goal not in GOAL_PRESETS:
                raise ValueError(
                    f"Unknown goal '{goal}'. Choose from: {sorted(GOAL_PRESETS)}"
                )
            weights = GOAL_PRESETS[goal]

        filtered = filter_materials(self.data, **filter_kwargs)

        if filtered.empty:
            # Nothing survived the filter - return an empty table with
            # the right columns rather than raising an error, so
            # callers (like the CLI) can show a friendly message.
            return pd.DataFrame(columns=RESULT_COLUMNS)

        scored = weighted_score(filtered, weights)
        ranked = scored.sort_values("match_score", ascending=False).reset_index(drop=True)

        return ranked[RESULT_COLUMNS].head(top_n)
