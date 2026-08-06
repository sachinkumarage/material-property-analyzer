"""
Unit tests for src/calculations.py - the strength-to-weight,
stiffness-to-weight, cost-per-strength, and relative-cost formulas
every other module builds on.
"""

import pytest

from src.calculations import (
    BASELINE_COST_USD_PER_KG,
    add_calculated_columns,
    cost_per_unit_strength,
    stiffness_to_weight_ratio,
    strength_to_weight_ratio,
)


class TestStrengthToWeightRatio:
    def test_known_value(self):
        assert strength_to_weight_ratio(500, 8) == pytest.approx(62.5)

    def test_zero_density_raises(self):
        with pytest.raises(ValueError):
            strength_to_weight_ratio(500, 0)

    def test_negative_density_raises(self):
        with pytest.raises(ValueError):
            strength_to_weight_ratio(500, -1)


class TestStiffnessToWeightRatio:
    def test_known_value(self):
        # GPa is converted to MPa internally (x1000) before dividing.
        assert stiffness_to_weight_ratio(200, 8) == pytest.approx(25000.0)

    def test_zero_density_raises(self):
        with pytest.raises(ValueError):
            stiffness_to_weight_ratio(200, 0)

    def test_negative_density_raises(self):
        with pytest.raises(ValueError):
            stiffness_to_weight_ratio(200, -5)


class TestCostPerUnitStrength:
    def test_known_value(self):
        assert cost_per_unit_strength(2.0, 500) == pytest.approx(0.004)

    def test_zero_strength_raises(self):
        with pytest.raises(ValueError):
            cost_per_unit_strength(2.0, 0)

    def test_negative_strength_raises(self):
        with pytest.raises(ValueError):
            cost_per_unit_strength(2.0, -10)


class TestAddCalculatedColumns:
    def test_adds_expected_columns(self, sample_df):
        result = add_calculated_columns(sample_df)
        for column in (
            "strength_to_weight_ratio",
            "yield_to_weight_ratio",
            "stiffness_to_weight_ratio",
            "cost_per_unit_strength",
            "relative_cost_index",
        ):
            assert column in result.columns

    def test_does_not_mutate_input(self, sample_df):
        original_columns = list(sample_df.columns)
        add_calculated_columns(sample_df)
        assert list(sample_df.columns) == original_columns

    def test_returns_new_dataframe(self, sample_df):
        result = add_calculated_columns(sample_df)
        assert result is not sample_df

    def test_values_match_hand_calculation(self, sample_df):
        result = add_calculated_columns(sample_df).set_index("name")

        alpha = result.loc["Alpha Steel"]
        assert alpha["strength_to_weight_ratio"] == pytest.approx(62.5)
        assert alpha["yield_to_weight_ratio"] == pytest.approx(400 / 8.0)
        assert alpha["stiffness_to_weight_ratio"] == pytest.approx(25000.0)
        assert alpha["cost_per_unit_strength"] == pytest.approx(0.004)

        gamma = result.loc["Gamma Composite"]
        assert gamma["strength_to_weight_ratio"] == pytest.approx(600.0)
        assert gamma["stiffness_to_weight_ratio"] == pytest.approx(140 * 1000 / 1.5)
        assert gamma["cost_per_unit_strength"] == pytest.approx(20.0 / 900)

    def test_relative_cost_index_uses_baseline(self, sample_df):
        result = add_calculated_columns(sample_df).set_index("name")
        for name, row in result.iterrows():
            expected = row["cost_usd_per_kg"] / BASELINE_COST_USD_PER_KG
            assert row["relative_cost_index"] == pytest.approx(expected)
