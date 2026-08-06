"""
Unit tests for src/selection_engine.py - the hard-requirement filter
funnel and the goal-based SelectionEngine built on top of scoring.py.
"""

import pytest

from src.selection_engine import RESULT_COLUMNS, GOAL_PRESETS, SelectionEngine, filter_materials


class TestFilterMaterials:
    def test_no_filters_returns_everything(self, sample_df):
        result = filter_materials(sample_df)
        assert len(result) == len(sample_df)

    def test_categories_filter(self, sample_df):
        result = filter_materials(sample_df, categories=["Test Steels", "Test Alloys"])
        assert set(result["name"]) == {"Alpha Steel", "Beta Alloy"}

    def test_max_density(self, sample_df):
        result = filter_materials(sample_df, max_density=2.0)
        assert set(result["name"]) == {"Beta Alloy", "Gamma Composite", "Delta Polymer"}

    def test_min_tensile_strength(self, sample_df):
        result = filter_materials(sample_df, min_tensile_strength=500)
        assert set(result["name"]) == {"Alpha Steel", "Gamma Composite"}

    def test_min_yield_strength(self, sample_df):
        result = filter_materials(sample_df, min_yield_strength=400)
        assert set(result["name"]) == {"Alpha Steel", "Gamma Composite"}

    def test_min_elastic_modulus(self, sample_df):
        result = filter_materials(sample_df, min_elastic_modulus=100)
        assert set(result["name"]) == {"Alpha Steel", "Gamma Composite"}

    def test_max_cost(self, sample_df):
        result = filter_materials(sample_df, max_cost=2.0)
        assert set(result["name"]) == {"Alpha Steel", "Delta Polymer"}

    def test_combined_filters(self, sample_df):
        result = filter_materials(sample_df, max_density=2.0, min_tensile_strength=100)
        assert set(result["name"]) == {"Beta Alloy", "Gamma Composite"}

    def test_impossible_filter_returns_empty(self, sample_df):
        result = filter_materials(sample_df, max_cost=0.01)
        assert result.empty

    def test_index_is_reset(self, sample_df):
        result = filter_materials(sample_df, categories=["Test Steels"])
        assert list(result.index) == [0]


@pytest.fixture
def engine(sample_df):
    return SelectionEngine(sample_df)


class TestSelectionEngine:
    def test_lightweight_strength_favors_best_specific_strength(self, engine):
        ranked = engine.select(goal="lightweight_strength", top_n=5)
        assert ranked.iloc[0]["name"] == "Gamma Composite"

    def test_budget_friendly_favors_cheapest_per_strength(self, engine):
        ranked = engine.select(goal="budget_friendly", top_n=5)
        assert ranked.iloc[0]["name"] == "Alpha Steel"

    def test_unknown_goal_raises(self, engine):
        with pytest.raises(ValueError):
            engine.select(goal="not_a_real_goal")

    def test_custom_weights_without_goal(self, engine):
        ranked = engine.select(weights={"cost_score": 1.0}, top_n=5)
        assert ranked.iloc[0]["name"] == "Alpha Steel"

    def test_goal_overrides_weights_when_both_given(self, engine):
        # If `weights` were used instead of `goal`, Gamma Composite
        # (best specific strength) would win - but budget_friendly
        # should take precedence and pick the cheapest-per-strength
        # material instead.
        ranked = engine.select(
            goal="budget_friendly",
            weights={"specific_strength_score": 1.0},
            top_n=5,
        )
        assert ranked.iloc[0]["name"] == "Alpha Steel"

    def test_top_n_limits_results(self, engine):
        ranked = engine.select(goal="balanced", top_n=2)
        assert len(ranked) == 2

    def test_empty_filter_result_returns_empty_with_correct_columns(self, engine):
        ranked = engine.select(goal="balanced", max_cost=0.01)
        assert ranked.empty
        assert list(ranked.columns) == RESULT_COLUMNS

    def test_filter_kwargs_pass_through(self, engine):
        ranked = engine.select(goal="balanced", categories=["Test Steels"], top_n=5)
        assert list(ranked["name"]) == ["Alpha Steel"]

    def test_result_is_sorted_descending_by_match_score(self, engine):
        ranked = engine.select(goal="balanced", top_n=5)
        scores = list(ranked["match_score"])
        assert scores == sorted(scores, reverse=True)

    def test_all_goal_presets_are_usable(self, engine):
        for goal in GOAL_PRESETS:
            ranked = engine.select(goal=goal, top_n=5)
            assert list(ranked.columns) == RESULT_COLUMNS
