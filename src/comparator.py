"""
comparator.py
-------------
Tools for comparing multiple materials side by side and ranking them
by whichever property matters most for a given job.

Materials engineering concept: MATERIAL SELECTION
----------------------------------------------------
Real engineers rarely pick a material based on one number. A part for
a Formula 1 wing needs high specific strength AND stiffness but cost
may not matter much. A part for a mass-produced car bumper needs to be
cheap and "good enough". Comparator functions here let you rank
materials by whatever property (or combination) is most relevant to
the task at hand.
"""

import pandas as pd

from src.calculations import add_calculated_columns


class MaterialComparator:
    """Compares materials using a table that already has engineering
    properties in it (density, strength, etc.)."""

    def __init__(self, materials_df: pd.DataFrame):
        # Pre-compute every derived engineering column once, up front,
        # so every comparison method below can just read a column
        # instead of recalculating the same formula repeatedly.
        self.data = add_calculated_columns(materials_df)

    def compare(self, names: list, properties: list = None) -> pd.DataFrame:
        """
        Return a small table containing only the requested materials
        and properties, side by side, for easy visual comparison.

        Parameters
        ----------
        names : list of material names to compare, e.g.
                ["Aluminum 6061-T6", "Titanium Ti-6Al-4V"]
        properties : which columns to include. Defaults to the most
                     commonly compared engineering properties.
        """
        if properties is None:
            properties = [
                "name",
                "category",
                "density_g_cm3",
                "tensile_strength_mpa",
                "strength_to_weight_ratio",
                "stiffness_to_weight_ratio",
            ]

        lower_names = [n.lower() for n in names]
        subset = self.data[self.data["name"].str.lower().isin(lower_names)]

        missing = set(lower_names) - set(subset["name"].str.lower())
        if missing:
            raise KeyError(f"Materials not found: {sorted(missing)}")

        return subset[properties].reset_index(drop=True)

    def rank_by(self, property_name: str, top_n: int = None, ascending: bool = False) -> pd.DataFrame:
        """
        Rank ALL materials in the database by a given property.

        Parameters
        ----------
        property_name : column to sort by, e.g. "strength_to_weight_ratio"
        top_n : if given, only return the top N results
        ascending : set True for properties where "lower is better"
                    (e.g. cost_per_unit_strength or density)
        """
        if property_name not in self.data.columns:
            raise KeyError(f"Unknown property '{property_name}'")

        ranked = self.data.sort_values(by=property_name, ascending=ascending).reset_index(drop=True)

        if top_n is not None:
            ranked = ranked.head(top_n)

        return ranked[["name", "category", property_name]]

    def best_strength_to_weight(self, top_n: int = 5) -> pd.DataFrame:
        """Convenience shortcut: the N best materials for strength-to-weight."""
        return self.rank_by("strength_to_weight_ratio", top_n=top_n, ascending=False)

    def best_value(self, top_n: int = 5) -> pd.DataFrame:
        """Convenience shortcut: cheapest cost per unit of strength."""
        return self.rank_by("cost_per_unit_strength", top_n=top_n, ascending=True)
