"""
Unit tests for src/comparator.py - side-by-side comparison and
whole-database ranking.
"""

import pytest

from src.comparator import MaterialComparator


@pytest.fixture
def comparator(sample_df):
    return MaterialComparator(sample_df)


class TestCompare:
    def test_default_properties(self, comparator):
        result = comparator.compare(["Alpha Steel", "Beta Alloy"])
        assert list(result.columns) == [
            "name", "category", "density_g_cm3", "tensile_strength_mpa",
            "strength_to_weight_ratio", "stiffness_to_weight_ratio",
        ]
        assert set(result["name"]) == {"Alpha Steel", "Beta Alloy"}

    def test_custom_properties(self, comparator):
        result = comparator.compare(["Alpha Steel"], properties=["name", "cost_usd_per_kg"])
        assert list(result.columns) == ["name", "cost_usd_per_kg"]
        assert result.iloc[0]["cost_usd_per_kg"] == pytest.approx(2.0)

    def test_case_insensitive_matching(self, comparator):
        result = comparator.compare(["alpha steel", "BETA ALLOY"])
        assert len(result) == 2

    def test_unknown_material_raises_key_error(self, comparator):
        with pytest.raises(KeyError):
            comparator.compare(["Alpha Steel", "Unobtainium"])

    def test_index_is_reset(self, comparator):
        result = comparator.compare(["Alpha Steel", "Beta Alloy"])
        assert list(result.index) == [0, 1]


class TestRankBy:
    def test_descending_by_default(self, comparator):
        ranked = comparator.rank_by("strength_to_weight_ratio")
        assert list(ranked["name"]) == [
            "Gamma Composite", "Beta Alloy", "Alpha Steel", "Delta Polymer",
        ]

    def test_ascending_when_requested(self, comparator):
        ranked = comparator.rank_by("cost_per_unit_strength", ascending=True)
        assert ranked.iloc[0]["name"] == "Alpha Steel"  # cheapest per unit strength

    def test_top_n_limits_results(self, comparator):
        ranked = comparator.rank_by("strength_to_weight_ratio", top_n=2)
        assert len(ranked) == 2
        assert list(ranked["name"]) == ["Gamma Composite", "Beta Alloy"]

    def test_unknown_property_raises_key_error(self, comparator):
        with pytest.raises(KeyError):
            comparator.rank_by("not_a_real_column")

    def test_returned_columns(self, comparator):
        ranked = comparator.rank_by("density_g_cm3")
        assert list(ranked.columns) == ["name", "category", "density_g_cm3"]


class TestConvenienceShortcuts:
    def test_best_strength_to_weight(self, comparator):
        result = comparator.best_strength_to_weight(top_n=1)
        assert result.iloc[0]["name"] == "Gamma Composite"

    def test_best_value(self, comparator):
        result = comparator.best_value(top_n=1)
        assert result.iloc[0]["name"] == "Alpha Steel"
