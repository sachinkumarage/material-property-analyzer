"""
calculations.py
----------------
Core materials-engineering formulas used throughout this project.

Materials engineering concept: SPECIFIC STRENGTH
--------------------------------------------------
When engineers pick a material for something that needs to be both
strong AND light (an airplane wing, a bike frame, a rocket body), raw
strength alone is not enough - a material can be strong but so dense
that the final part is too heavy to be useful.

The "strength-to-weight ratio" (also called SPECIFIC STRENGTH) solves
this by dividing a material's strength by its density:

    specific_strength = strength / density

A higher number means you get more strength for every gram of material
you carry around. This is why carbon fiber (very strong, quite light)
is prized in aerospace even though steel is "stronger" in absolute
terms - steel is much denser, so per kilogram it delivers less
strength.

Materials engineering concept: SPECIFIC STIFFNESS
---------------------------------------------------
Strength tells you when a material breaks or permanently deforms.
Stiffness (measured by the elastic modulus, a.k.a. Young's modulus)
tells you how much a material bends/stretches under load *before* it
reaches that point. Dividing stiffness by density gives "specific
stiffness" - useful for parts where you care about resisting bending
(like an airplane wing again) more than avoiding outright fracture.
"""

import pandas as pd

# Materials engineering concept: RELATIVE COST
# -----------------------------------------------
# Raw material prices swing with the market, but engineers usually only
# care about relative cost when comparing options: "how many times more
# expensive is titanium than plain steel?" We answer that by dividing
# every material's cost by a fixed baseline - the approximate price of
# ordinary structural carbon steel (about $1/kg). A relative_cost_index
# of 20 means "about 20x the price of basic carbon steel", regardless of
# which materials happen to be in the current table.
BASELINE_COST_USD_PER_KG = 1.0


def strength_to_weight_ratio(strength_mpa: float, density_g_cm3: float) -> float:
    """
    Calculate specific strength (strength-to-weight ratio).

    Parameters
    ----------
    strength_mpa : the material's strength in megapascals (MPa).
                    Usually tensile strength, sometimes yield strength.
    density_g_cm3 : the material's density in grams per cubic cm.

    Returns
    -------
    A ratio in MPa per (g/cm3). Bigger is better: more strength per
    unit of weight.
    """
    if density_g_cm3 <= 0:
        raise ValueError("density_g_cm3 must be a positive number")
    return strength_mpa / density_g_cm3


def stiffness_to_weight_ratio(elastic_modulus_gpa: float, density_g_cm3: float) -> float:
    """
    Calculate specific stiffness (elastic modulus divided by density).

    Elastic modulus (a.k.a. Young's modulus) measures how much a
    material resists stretching/bending elastically - i.e. how "stiff"
    it is. A higher specific stiffness means a lighter part can be made
    just as rigid.
    """
    if density_g_cm3 <= 0:
        raise ValueError("density_g_cm3 must be a positive number")
    # Elastic modulus is given in GPa (1 GPa = 1000 MPa), so convert to
    # MPa first to keep units consistent with strength_to_weight_ratio.
    return (elastic_modulus_gpa * 1000) / density_g_cm3


def cost_per_unit_strength(cost_usd_per_kg: float, strength_mpa: float) -> float:
    """
    How many dollars you pay per MPa of strength you get - useful when
    budget matters as much as performance. Lower is more cost-effective.
    """
    if strength_mpa <= 0:
        raise ValueError("strength_mpa must be a positive number")
    return cost_usd_per_kg / strength_mpa


def add_calculated_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Take the raw materials table and add derived engineering columns:
        - strength_to_weight_ratio (using tensile strength)
        - yield_to_weight_ratio    (using yield strength)
        - stiffness_to_weight_ratio
        - cost_per_unit_strength
        - relative_cost_index      (cost relative to plain carbon steel)

    Returns a NEW DataFrame (the original is left untouched), which is
    a safer habit than modifying data in place.
    """
    result = df.copy()

    result["strength_to_weight_ratio"] = result.apply(
        lambda row: strength_to_weight_ratio(
            row["tensile_strength_mpa"], row["density_g_cm3"]
        ),
        axis=1,
    )

    result["yield_to_weight_ratio"] = result.apply(
        lambda row: strength_to_weight_ratio(
            row["yield_strength_mpa"], row["density_g_cm3"]
        ),
        axis=1,
    )

    result["stiffness_to_weight_ratio"] = result.apply(
        lambda row: stiffness_to_weight_ratio(
            row["elastic_modulus_gpa"], row["density_g_cm3"]
        ),
        axis=1,
    )

    result["cost_per_unit_strength"] = result.apply(
        lambda row: cost_per_unit_strength(
            row["cost_usd_per_kg"], row["tensile_strength_mpa"]
        ),
        axis=1,
    )

    result["relative_cost_index"] = result["cost_usd_per_kg"] / BASELINE_COST_USD_PER_KG

    return result
