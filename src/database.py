"""
database.py
------------
Loads the materials CSV file into a table (a pandas DataFrame) and
provides simple, beginner-friendly ways to read and update it.

Think of this file as the "librarian" for our materials data: it knows
how to fetch a book (a material), list every book on the shelf, or add
a new one. It does not know anything about engineering formulas -
that logic lives in calculations.py.

Materials engineering concept: WHY SO MANY COLUMNS?
-----------------------------------------------------
A real material datasheet reports far more than "strength" - different
jobs stress different properties. A heat sink cares about thermal
conductivity, a spring cares about fatigue strength, a boat hull cares
about corrosion resistance. Storing all of these properties side by
side (instead of just density/strength/stiffness) is what lets the
rest of this project answer more interesting engineering questions.
See README.md for a full explanation of every column and the
approximate nature of the reference data used here.
"""

import pandas as pd


class MaterialDatabase:
    """
    Wraps a CSV file of material properties.

    The CSV is expected to have these columns (see README.md for units,
    typical value ranges, and where the numbers come from):
        name                                  - material name, e.g. "Aluminum 6061-T6"
        category                              - one of 17 material families, e.g.
                                                 "Aluminum Alloys", "Ceramics", "Wood"
        density_g_cm3                         - density in grams per cubic centimetre
        yield_strength_mpa                    - stress at which the material starts
                                                 to permanently deform (megapascals)
        tensile_strength_mpa                  - ultimate tensile strength: the stress
                                                 at which the material breaks (MPa)
        elastic_modulus_gpa                   - stiffness (Young's modulus), in
                                                 gigapascals
        poisson_ratio                         - how much a material narrows sideways
                                                 when stretched lengthwise (unitless)
        hardness_value                        - resistance to surface indentation
        hardness_scale                        - which hardness scale hardness_value
                                                 uses (HB, HRC, HV, Shore A, Shore D,
                                                 Mohs, Janka, or Barcol - see README.md)
        thermal_conductivity_w_mk             - how well the material conducts heat,
                                                 in watts per metre-kelvin
        electrical_conductivity_percent_iacs  - electrical conductivity relative to
                                                 pure annealed copper (copper = 100%,
                                                 electrical insulators ~= 0%)
        melting_point_c                       - melting point in degrees Celsius (or,
                                                 for materials that don't have a sharp
                                                 melting point, an approximate
                                                 softening/decomposition temperature -
                                                 see README.md)
        fatigue_strength_mpa                  - approximate stress the material can
                                                 survive for ~10 million load cycles
                                                 without breaking
        cost_usd_per_kg                       - approximate raw material cost
        corrosion_resistance                  - a rough rating: Poor, Fair, Good, or
                                                 Excellent
    """

    # Columns every valid materials CSV must contain.
    REQUIRED_COLUMNS = [
        "name",
        "category",
        "density_g_cm3",
        "yield_strength_mpa",
        "tensile_strength_mpa",
        "elastic_modulus_gpa",
        "poisson_ratio",
        "hardness_value",
        "hardness_scale",
        "thermal_conductivity_w_mk",
        "electrical_conductivity_percent_iacs",
        "melting_point_c",
        "fatigue_strength_mpa",
        "cost_usd_per_kg",
        "corrosion_resistance",
    ]

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.data = self._load(csv_path)

    def _load(self, csv_path: str) -> pd.DataFrame:
        """Read the CSV file and make sure it has the columns we need."""
        df = pd.read_csv(csv_path)

        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"materials CSV is missing required columns: {missing}")

        return df

    def list_materials(self) -> list:
        """Return every material name in the database, e.g. for a menu."""
        return self.data["name"].tolist()

    def get_material(self, name: str) -> pd.Series:
        """
        Return a single material's row (a pandas Series) by name.
        Raises a clear error if the name isn't found, instead of
        silently returning nothing.
        """
        matches = self.data[self.data["name"].str.lower() == name.lower()]
        if matches.empty:
            raise KeyError(f"Material '{name}' not found in database.")
        return matches.iloc[0]

    def add_material(self, **properties) -> None:
        """
        Add a new material to the in-memory table.

        Usage:
            db.add_material(
                name="Rattan (Bamboo Cane)",
                category="Wood",
                density_g_cm3=0.7,
                yield_strength_mpa=100,
                tensile_strength_mpa=140,
                elastic_modulus_gpa=20,
                poisson_ratio=0.3,
                hardness_value=1000,
                hardness_scale="Janka",
                thermal_conductivity_w_mk=0.15,
                electrical_conductivity_percent_iacs=0,
                melting_point_c=300,
                fatigue_strength_mpa=40,
                cost_usd_per_kg=1.2,
                corrosion_resistance="Fair",
            )
        """
        missing = [col for col in self.REQUIRED_COLUMNS if col not in properties]
        if missing:
            raise ValueError(f"Missing properties for new material: {missing}")

        new_row = pd.DataFrame([properties])
        self.data = pd.concat([self.data, new_row], ignore_index=True)

    def save(self, csv_path: str = None) -> None:
        """Write the current table back out to CSV (defaults to original file)."""
        path = csv_path or self.csv_path
        self.data.to_csv(path, index=False)
