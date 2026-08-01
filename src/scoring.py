"""
scoring.py
----------
Turns raw engineering ratios into comparable 0-100 scores, then blends
those scores together into a single "how good is this match" number.

Materials engineering concept: NORMALIZED SCORING
----------------------------------------------------
You can't fairly compare "strength-to-weight ratio" (measured in MPa
per g/cm3) with "cost per unit strength" (measured in USD per MPa) -
they live on completely different scales. Normalization fixes this by
rescaling every property onto the same 0-100 range, where 100 always
means "the best material in this group for that property" and 0 always
means "the worst". Once every property speaks the same "score"
language, they can be combined.

Materials engineering concept: WEIGHTED DECISION MATRIX
-------------------------------------------------------
Engineers rarely optimize for just one property. A bicycle frame cares
a lot about specific strength, a little about specific stiffness, and
not much about cost. A weighted decision matrix captures this: give
each property a "weight" (how much it matters, as a fraction of 100%),
multiply each material's score by that weight, and add the results up
into one overall match score. Change the weights and the ranking
changes with it - which is exactly how real engineers trade off
competing goals.
"""

import pandas as pd

from src.calculations import add_calculated_columns

# Every score this module can calculate: which derived column it reads
# from, and whether a bigger raw number is better (True) or worse
# (False). cost_per_unit_strength is a "lower is better" property, so
# it's flagged False - normalize_column() takes care of flipping it.
SCORABLE_PROPERTIES = {
    "specific_strength_score": ("strength_to_weight_ratio", True),
    "specific_stiffness_score": ("stiffness_to_weight_ratio", True),
    "cost_score": ("cost_per_unit_strength", False),
}

# A sensible "no strong opinion" starting point: strength matters most,
# stiffness next, cost least. Callers are free to override this.
DEFAULT_WEIGHTS = {
    "specific_strength_score": 0.4,
    "specific_stiffness_score": 0.3,
    "cost_score": 0.3,
}


def normalize_column(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    """
    Rescale a column of numbers onto a common 0-100 scale.

    The best value in the column becomes 100, the worst becomes 0, and
    everything else lands proportionally in between. This is called
    "min-max normalization".

    Parameters
    ----------
    series : the raw numbers to rescale (e.g. a column of density
             values).
    higher_is_better : True if a bigger raw number should score higher
                        (e.g. strength). False if a smaller raw number
                        should score higher (e.g. cost).
    """
    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        # Every material ties on this property (or there's only one
        # material) - there's nothing to rank, so score everyone equally.
        return pd.Series(100.0, index=series.index)

    if higher_is_better:
        return 100 * (series - minimum) / (maximum - minimum)
    return 100 * (maximum - series) / (maximum - minimum)


def add_score_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add one normalized 0-100 score column per entry in
    SCORABLE_PROPERTIES (specific_strength_score, specific_stiffness_score,
    cost_score), on top of the raw engineering columns.
    """
    result = add_calculated_columns(df)

    for score_name, (source_column, higher_is_better) in SCORABLE_PROPERTIES.items():
        result[score_name] = normalize_column(result[source_column], higher_is_better)

    return result


def weighted_score(df: pd.DataFrame, weights: dict = None) -> pd.DataFrame:
    """
    Combine the individual 0-100 scores into one overall "match_score"
    using a weighted average - the weighted decision matrix described
    above.

    Parameters
    ----------
    df : materials table (raw columns only - the score columns are
         added here).
    weights : dict mapping a score name (from SCORABLE_PROPERTIES) to
              how much it matters, e.g. {"specific_strength_score": 0.7,
              "specific_stiffness_score": 0.2, "cost_score": 0.1}.
              Weights don't need to add up to exactly 1 - they're
              automatically normalized so they always do. Defaults to
              DEFAULT_WEIGHTS.
    """
    weights = weights or DEFAULT_WEIGHTS

    unknown = set(weights) - set(SCORABLE_PROPERTIES)
    if unknown:
        raise ValueError(f"Unknown scoring criteria: {sorted(unknown)}")

    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("Weights must add up to a positive number")

    result = add_score_columns(df)

    # Build the weighted average one property at a time. Dividing each
    # weight by total_weight means the caller's weights don't have to
    # sum to 1.0 themselves - e.g. weights of {strength: 2, cost: 1}
    # behave the same as {strength: 0.67, cost: 0.33}.
    result["match_score"] = 0.0
    for score_name, weight in weights.items():
        result["match_score"] += result[score_name] * (weight / total_weight)

    return result
