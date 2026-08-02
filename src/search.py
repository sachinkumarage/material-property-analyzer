"""
search.py
---------
Version 4 upgrade: an advanced search, filtering, sorting, and
database-statistics module for the materials database.

Materials engineering concept: SEARCH VS. SELECT
---------------------------------------------------
selection_engine.py answers a narrow question - "what's the single
best material for this job?" - by filtering on hard requirements and
ranking the survivors with a weighted score. search.py answers a
broader, more exploratory question - "show me every material that
matches these criteria" - which is what an engineer wants when
browsing a catalog, double-checking a shortlist, or looking up a
specific alloy by name. It supports:

    - free-text search by name, category, or subcategory
    - range filters on any numeric property (density, strength,
      stiffness, thermal/electrical conductivity, melting point, cost)
    - a categorical filter on corrosion resistance
    - combining any number of the above at once
    - sorting the results by whichever property matters most

A separate `get_statistics` function summarizes the whole database
(category counts, averages, and the current "record holders" for
strength, lightness, and cost) - handy for getting your bearings
before you start searching.
"""

import pandas as pd

from src.calculations import add_calculated_columns

# Corrosion resistance is a qualitative rating, not a number, so it
# needs its own ordering (worst to best) to support "at least Good"
# style filters instead of a numeric range.
CORROSION_RESISTANCE_ORDER = ["Poor", "Fair", "Good", "Excellent"]

# Friendly sort key -> DataFrame column, plus whether "best" naturally
# means the smallest value (True) or the largest value (False). This
# lets sort_materials() pick a sensible default direction - e.g.
# density sorts ascending by default (lightest first) while strength
# sorts descending (strongest first) - without the caller having to
# remember which way is "better" for each property.
SORT_OPTIONS = {
    "density": ("density_g_cm3", True),
    "strength": ("tensile_strength_mpa", False),
    "stiffness": ("elastic_modulus_gpa", False),
    "cost": ("cost_usd_per_kg", True),
    "specific_strength": ("strength_to_weight_ratio", False),
    "specific_stiffness": ("stiffness_to_weight_ratio", False),
}

# Friendly range-filter keyword -> DataFrame column it restricts.
RANGE_FILTERS = {
    "density_range": "density_g_cm3",
    "yield_strength_range": "yield_strength_mpa",
    "tensile_strength_range": "tensile_strength_mpa",
    "elastic_modulus_range": "elastic_modulus_gpa",
    "thermal_conductivity_range": "thermal_conductivity_w_mk",
    "electrical_conductivity_range": "electrical_conductivity_percent_iacs",
    "melting_point_range": "melting_point_c",
    "relative_cost_range": "cost_usd_per_kg",
}

# Columns shown in search results: enough to identify and sanity-check
# a match, plus the two derived "specific" properties used for sorting.
RESULT_COLUMNS = [
    "name",
    "category",
    "subcategory",
    "density_g_cm3",
    "yield_strength_mpa",
    "tensile_strength_mpa",
    "elastic_modulus_gpa",
    "thermal_conductivity_w_mk",
    "electrical_conductivity_percent_iacs",
    "melting_point_c",
    "cost_usd_per_kg",
    "corrosion_resistance",
    "strength_to_weight_ratio",
    "stiffness_to_weight_ratio",
]


def _text_matches(series: pd.Series, query: str) -> pd.Series:
    """Case-insensitive substring match; NaN entries never match."""
    return series.str.contains(query, case=False, na=False, regex=False)


def search_by_text(
    df: pd.DataFrame,
    name: str = None,
    category: str = None,
    subcategory: str = None,
) -> pd.DataFrame:
    """
    Narrow the table down to rows whose name/category/subcategory
    contain the given text (case-insensitive substring match). Any
    term left as None is skipped. If more than one term is given, a
    row must match all of them (e.g. category="Steel" narrowed further
    by subcategory="Stainless").
    """
    result = df

    if name:
        result = result[_text_matches(result["name"], name)]
    if category:
        result = result[_text_matches(result["category"], category)]
    if subcategory:
        result = result[_text_matches(result["subcategory"], subcategory)]

    return result


def _apply_range(df: pd.DataFrame, column: str, value_range) -> pd.DataFrame:
    """Keep rows where column falls within (min, max); either side may be None."""
    if value_range is None:
        return df

    minimum, maximum = value_range
    if minimum is not None:
        df = df[df[column] >= minimum]
    if maximum is not None:
        df = df[df[column] <= maximum]
    return df


def filter_by_ranges(df: pd.DataFrame, corrosion_resistance: str = None, **ranges) -> pd.DataFrame:
    """
    Filter rows by numeric ranges and/or a minimum corrosion resistance
    rating. Combining several filters at once is just a matter of
    passing several keywords - each one further narrows the result.

    Parameters
    ----------
    corrosion_resistance : minimum acceptable rating ("Poor", "Fair",
                            "Good", or "Excellent"). A material rated
                            higher than this also passes, e.g.
                            corrosion_resistance="Good" keeps Good and
                            Excellent materials, but not Fair or Poor.
    **ranges : any of the keys in RANGE_FILTERS, each a (min, max)
               tuple where either side may be None for "no limit",
               e.g. density_range=(None, 3.0), melting_point_range=(500, 1500).
    """
    unknown = set(ranges) - set(RANGE_FILTERS)
    if unknown:
        raise ValueError(f"Unknown range filter(s): {sorted(unknown)}")

    result = df
    for filter_name, column in RANGE_FILTERS.items():
        result = _apply_range(result, column, ranges.get(filter_name))

    if corrosion_resistance is not None:
        if corrosion_resistance not in CORROSION_RESISTANCE_ORDER:
            raise ValueError(
                f"Unknown corrosion_resistance '{corrosion_resistance}'. "
                f"Choose from: {CORROSION_RESISTANCE_ORDER}"
            )
        min_rank = CORROSION_RESISTANCE_ORDER.index(corrosion_resistance)
        acceptable_ratings = CORROSION_RESISTANCE_ORDER[min_rank:]
        result = result[result["corrosion_resistance"].isin(acceptable_ratings)]

    return result


def sort_materials(df: pd.DataFrame, sort_by: str = None, ascending: bool = None) -> pd.DataFrame:
    """
    Sort results by a friendly key: "density", "strength", "stiffness",
    "cost", "specific_strength", or "specific_stiffness". Returns df
    unchanged (no sorting) if sort_by is None.

    ascending : True/False to force a direction, or leave as None to
                use the sensible default for that property (e.g.
                density and cost sort lowest-first by default, since
                lighter/cheaper is usually "better").
    """
    if sort_by is None:
        return df

    if sort_by not in SORT_OPTIONS:
        raise ValueError(f"Unknown sort key '{sort_by}'. Choose from: {sorted(SORT_OPTIONS)}")

    column, default_ascending = SORT_OPTIONS[sort_by]
    if ascending is None:
        ascending = default_ascending

    return df.sort_values(by=column, ascending=ascending)


class SearchEngine:
    """
    High-level entry point that ties text search, filtering, and
    sorting together over the materials database.
    """

    def __init__(self, materials_df: pd.DataFrame):
        # Pre-compute specific strength/stiffness once so repeated
        # searches don't repeat the same calculation every time.
        self.data = add_calculated_columns(materials_df)

    def search(
        self,
        name: str = None,
        category: str = None,
        subcategory: str = None,
        corrosion_resistance: str = None,
        sort_by: str = None,
        ascending: bool = None,
        top_n: int = None,
        **ranges,
    ) -> pd.DataFrame:
        """
        Search and filter the database, then sort the results.

        Parameters
        ----------
        name, category, subcategory : optional case-insensitive
            substring search terms (see search_by_text).
        corrosion_resistance, **ranges : optional filters (see
            filter_by_ranges) - e.g. max_cost via
            relative_cost_range=(None, 10), or
            tensile_strength_range=(200, None).
        sort_by, ascending : optional sort order (see sort_materials).
        top_n : if given, only return the top N results after sorting.
        """
        result = search_by_text(self.data, name=name, category=category, subcategory=subcategory)
        result = filter_by_ranges(result, corrosion_resistance=corrosion_resistance, **ranges)
        result = sort_materials(result, sort_by=sort_by, ascending=ascending)
        result = result.reset_index(drop=True)

        if top_n is not None:
            result = result.head(top_n)

        return result[RESULT_COLUMNS]


def get_statistics(materials_df: pd.DataFrame) -> dict:
    """
    Summarize the whole database: how many materials it holds, how
    they're distributed across categories, a couple of useful
    averages, and the current "record holders" for strength,
    lightness, and cost.
    """
    df = materials_df

    strongest = df.loc[df["tensile_strength_mpa"].idxmax()]
    lightest = df.loc[df["density_g_cm3"].idxmin()]
    cheapest = df.loc[df["cost_usd_per_kg"].idxmin()]

    return {
        "total_materials": len(df),
        "category_counts": df["category"].value_counts().to_dict(),
        "average_density_g_cm3": df["density_g_cm3"].mean(),
        "average_tensile_strength_mpa": df["tensile_strength_mpa"].mean(),
        "strongest_material": strongest["name"],
        "lightest_material": lightest["name"],
        "cheapest_material": cheapest["name"],
    }


def print_statistics(materials_df: pd.DataFrame) -> None:
    """Pretty-print get_statistics() output to the terminal."""
    stats = get_statistics(materials_df)

    print("\nMaterial Database Statistics")
    print("-" * 40)
    print(f"Total materials: {stats['total_materials']}")
    print(f"Average density: {stats['average_density_g_cm3']:.2f} g/cm3")
    print(f"Average tensile strength: {stats['average_tensile_strength_mpa']:.1f} MPa")
    print(f"Strongest material: {stats['strongest_material']}")
    print(f"Lightest material: {stats['lightest_material']}")
    print(f"Cheapest material: {stats['cheapest_material']}")

    print("\nMaterials per category:")
    for category, count in sorted(stats["category_counts"].items()):
        print(f"  {category}: {count}")
