"""
Unit tests for src/scoring.py - min-max normalization and the
weighted-decision-matrix match score.

A dedicated fixture (`scorable_df`) is used instead of the shared
sample_df: its density is fixed at 1.0 for every row so
strength-to-weight and stiffness-to-weight ratios come out to the same
round numbers as the raw inputs, making every expected 0-100 score and
weighted average easy to verify by hand instead of re-deriving the
formula under test.
"""

import pandas as pd
import pytest

from src.scoring import (
    DEFAULT_WEIGHTS,
    SCORABLE_PROPERTIES,
    add_score_columns,
    normalize_column,
    weighted_score,
)

REQUIRED_EXTRAS = dict(
    yield_strength_mpa=0, poisson_ratio=0.3, hardness_value=100, hardness_scale="HB",
    thermal_conductivity_w_mk=10, electrical_conductivity_percent_iacs=5,
    melting_point_c=1000, fatigue_strength_mpa=50, corrosion_resistance="Good",
)


@pytest.fixture
def scorable_df() -> pd.DataFrame:
    """
    Three rows engineered so every normalized score lands on 0, 50, or
    100:
        Row1: tensile=50,  modulus=10, cost=0.5  -> cost/strength=0.01 (cheapest)
        Row2: tensile=100, modulus=20, cost=2.0  -> cost/strength=0.02 (middle)
        Row3: tensile=150, modulus=30, cost=4.5  -> cost/strength=0.03 (priciest)
    Density is 1.0 for every row, so strength/stiffness ratios equal
    the raw tensile/modulus values directly.
    """
    rows = []
    for name, tensile, modulus, cost in [
        ("Row1", 50, 10, 0.5),
        ("Row2", 100, 20, 2.0),
        ("Row3", 150, 30, 4.5),
    ]:
        rows.append(dict(
            name=name, category="Test", subcategory="Test",
            density_g_cm3=1.0, tensile_strength_mpa=tensile,
            elastic_modulus_gpa=modulus, cost_usd_per_kg=cost,
            **REQUIRED_EXTRAS,
        ))
    return pd.DataFrame(rows)


class TestNormalizeColumn:
    def test_higher_is_better(self):
        result = normalize_column(pd.Series([10, 20, 30]), higher_is_better=True)
        assert list(result) == pytest.approx([0.0, 50.0, 100.0])

    def test_lower_is_better(self):
        result = normalize_column(pd.Series([10, 20, 30]), higher_is_better=False)
        assert list(result) == pytest.approx([100.0, 50.0, 0.0])

    def test_constant_column_scores_everyone_100(self):
        result = normalize_column(pd.Series([5, 5, 5]))
        assert list(result) == [100.0, 100.0, 100.0]

    def test_single_value_scores_100(self):
        result = normalize_column(pd.Series([42]))
        assert list(result) == [100.0]


class TestAddScoreColumns:
    def test_adds_all_score_columns(self, scorable_df):
        result = add_score_columns(scorable_df)
        for score_name in SCORABLE_PROPERTIES:
            assert score_name in result.columns

    def test_score_values(self, scorable_df):
        result = add_score_columns(scorable_df).set_index("name")

        assert result.loc["Row1", "specific_strength_score"] == pytest.approx(0.0)
        assert result.loc["Row2", "specific_strength_score"] == pytest.approx(50.0)
        assert result.loc["Row3", "specific_strength_score"] == pytest.approx(100.0)

        assert result.loc["Row1", "specific_stiffness_score"] == pytest.approx(0.0)
        assert result.loc["Row3", "specific_stiffness_score"] == pytest.approx(100.0)

        # Cost is "lower is better" - the cheapest-per-strength row scores 100.
        assert result.loc["Row1", "cost_score"] == pytest.approx(100.0)
        assert result.loc["Row2", "cost_score"] == pytest.approx(50.0)
        assert result.loc["Row3", "cost_score"] == pytest.approx(0.0)


class TestWeightedScore:
    def test_default_weights(self, scorable_df):
        result = weighted_score(scorable_df).set_index("name")
        # match_score = 0.4*strength + 0.3*stiffness + 0.3*cost
        assert result.loc["Row1", "match_score"] == pytest.approx(30.0)
        assert result.loc["Row2", "match_score"] == pytest.approx(50.0)
        assert result.loc["Row3", "match_score"] == pytest.approx(70.0)

    def test_none_uses_default_weights(self, scorable_df):
        explicit = weighted_score(scorable_df, DEFAULT_WEIGHTS)
        implicit = weighted_score(scorable_df, None)
        assert list(explicit["match_score"]) == pytest.approx(list(implicit["match_score"]))

    def test_weights_need_not_sum_to_one(self, scorable_df):
        # {strength: 2, cost: 1} behaves like {strength: 2/3, cost: 1/3}.
        result = weighted_score(
            scorable_df, {"specific_strength_score": 2, "cost_score": 1}
        ).set_index("name")

        assert result.loc["Row1", "match_score"] == pytest.approx(0 * 2 / 3 + 100 * 1 / 3)
        assert result.loc["Row3", "match_score"] == pytest.approx(100 * 2 / 3 + 0 * 1 / 3)

    def test_unknown_scoring_criteria_raises(self, scorable_df):
        with pytest.raises(ValueError):
            weighted_score(scorable_df, {"not_a_real_score": 1.0})

    def test_zero_total_weight_raises(self, scorable_df):
        with pytest.raises(ValueError):
            weighted_score(scorable_df, {"cost_score": 0})

    def test_negative_total_weight_raises(self, scorable_df):
        with pytest.raises(ValueError):
            weighted_score(scorable_df, {"cost_score": -1})
