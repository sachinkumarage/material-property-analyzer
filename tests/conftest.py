"""
conftest.py
-----------
Shared pytest fixtures for the whole test suite.

Two kinds of data are used throughout these tests:

- A small, hand-built "sample" dataset (see `sample_records` /
  `sample_df`) with round numbers chosen so every derived ratio can be
  checked by hand (e.g. strength_to_weight_ratio = 500 / 8 = 62.5).
  Unit tests use this - it's fast, deterministic, and independent of
  the real materials database ever changing.
- The project's real `data/materials.csv`, exposed via `real_data_path`
  / `real_database`, for integration tests that want to exercise the
  full stack against production data.
"""

import sys
from pathlib import Path

import matplotlib
import pandas as pd
import pytest

# Make sure `import src...` and `import app` work no matter how pytest
# is invoked (`pytest`, `python -m pytest`, from a subdirectory, ...).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force a non-interactive backend before anything imports pyplot, so
# running the test suite never tries to pop up a GUI window.
matplotlib.use("Agg")

REQUIRED_COLUMNS = [
    "name",
    "category",
    "subcategory",
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


@pytest.fixture
def sample_records() -> list:
    """
    Four synthetic materials with deliberately round numbers so every
    derived ratio (strength/density, modulus/density, cost/strength...)
    can be verified by hand in assertions instead of re-deriving the
    formula under test.

    strength_to_weight_ratio  = tensile_strength_mpa / density_g_cm3
        Alpha Steel:      500 / 8.0 = 62.5
        Beta Alloy:       400 / 2.0 = 200.0
        Gamma Composite:  900 / 1.5 = 600.0
        Delta Polymer:     50 / 1.2 = 41.666...
    stiffness_to_weight_ratio = elastic_modulus_gpa * 1000 / density_g_cm3
        Alpha Steel:      200 * 1000 / 8.0 = 25000.0
        Beta Alloy:        70 * 1000 / 2.0 = 35000.0
        Gamma Composite:  140 * 1000 / 1.5 = 93333.33...
        Delta Polymer:      2.5 * 1000 / 1.2 = 2083.33...
    cost_per_unit_strength = cost_usd_per_kg / tensile_strength_mpa
        Alpha Steel:      2.0 / 500 = 0.004
        Beta Alloy:       4.0 / 400 = 0.01
        Gamma Composite: 20.0 / 900 = 0.02222...
        Delta Polymer:    1.5 / 50  = 0.03
    """
    return [
        dict(
            name="Alpha Steel", category="Test Steels", subcategory="Alloy",
            density_g_cm3=8.0, yield_strength_mpa=400.0, tensile_strength_mpa=500.0,
            elastic_modulus_gpa=200.0, poisson_ratio=0.30, hardness_value=150.0,
            hardness_scale="HB", thermal_conductivity_w_mk=50.0,
            electrical_conductivity_percent_iacs=10.0, melting_point_c=1500,
            fatigue_strength_mpa=250.0, cost_usd_per_kg=2.0, corrosion_resistance="Poor",
        ),
        dict(
            name="Beta Alloy", category="Test Alloys", subcategory="Light",
            density_g_cm3=2.0, yield_strength_mpa=300.0, tensile_strength_mpa=400.0,
            elastic_modulus_gpa=70.0, poisson_ratio=0.33, hardness_value=60.0,
            hardness_scale="HB", thermal_conductivity_w_mk=150.0,
            electrical_conductivity_percent_iacs=35.0, melting_point_c=650,
            fatigue_strength_mpa=150.0, cost_usd_per_kg=4.0, corrosion_resistance="Good",
        ),
        dict(
            name="Gamma Composite", category="Test Composites", subcategory="Fiber",
            density_g_cm3=1.5, yield_strength_mpa=600.0, tensile_strength_mpa=900.0,
            elastic_modulus_gpa=140.0, poisson_ratio=0.28, hardness_value=80.0,
            hardness_scale="HB", thermal_conductivity_w_mk=5.0,
            electrical_conductivity_percent_iacs=0.0, melting_point_c=300,
            fatigue_strength_mpa=400.0, cost_usd_per_kg=20.0, corrosion_resistance="Excellent",
        ),
        dict(
            name="Delta Polymer", category="Test Polymers", subcategory="Thermoplastic",
            density_g_cm3=1.2, yield_strength_mpa=40.0, tensile_strength_mpa=50.0,
            elastic_modulus_gpa=2.5, poisson_ratio=0.40, hardness_value=70.0,
            hardness_scale="Shore D", thermal_conductivity_w_mk=0.3,
            electrical_conductivity_percent_iacs=0.0, melting_point_c=180,
            fatigue_strength_mpa=20.0, cost_usd_per_kg=1.5, corrosion_resistance="Excellent",
        ),
    ]


@pytest.fixture
def sample_df(sample_records) -> pd.DataFrame:
    """The sample_records fixture as a DataFrame - the shape every
    module in src/ expects as input."""
    return pd.DataFrame(sample_records)


@pytest.fixture
def sample_csv_path(tmp_path, sample_records) -> str:
    """Write the sample dataset to a temporary CSV file and return its
    path, for tests that exercise MaterialDatabase's file I/O."""
    path = tmp_path / "sample_materials.csv"
    pd.DataFrame(sample_records).to_csv(path, index=False)
    return str(path)


@pytest.fixture
def real_data_path() -> str:
    """Path to the project's real materials database."""
    return str(PROJECT_ROOT / "data" / "materials.csv")


@pytest.fixture
def real_database(real_data_path):
    """A MaterialDatabase loaded from the real project data - used by
    integration tests that want to exercise the full stack against
    production data rather than the small synthetic sample."""
    from src.database import MaterialDatabase

    return MaterialDatabase(real_data_path)
