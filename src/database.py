"""
database.py
------------
Loads the materials CSV file into a table (a pandas DataFrame) and
provides simple, beginner-friendly ways to read and update it.

Think of this file as the "librarian" for our materials data: it knows
how to fetch a book (a material), list every book on the shelf, or add
a new one. It does not know anything about engineering formulas -
that logic lives in calculations.py.
"""

import pandas as pd


class MaterialDatabase:
    """
    Wraps a CSV file of material properties.

    The CSV is expected to have these columns:
        name                 - material name, e.g. "Aluminum 6061-T6"
        category             - Metal, Composite, Wood, Ceramic, Polymer, ...
        density_g_cm3        - density in grams per cubic centimetre
        tensile_strength_mpa - ultimate tensile strength in megapascals
        yield_strength_mpa   - yield strength in megapascals
        elastic_modulus_gpa  - stiffness (Young's modulus) in gigapascals
        cost_usd_per_kg      - approximate raw material cost
    """

    # Columns every valid materials CSV must contain.
    REQUIRED_COLUMNS = [
        "name",
        "category",
        "density_g_cm3",
        "tensile_strength_mpa",
        "yield_strength_mpa",
        "elastic_modulus_gpa",
        "cost_usd_per_kg",
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
                name="Bamboo",
                category="Wood",
                density_g_cm3=0.7,
                tensile_strength_mpa=140,
                yield_strength_mpa=100,
                elastic_modulus_gpa=20,
                cost_usd_per_kg=1.2,
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
