"""
Integration tests - these exercise several modules together against
the *real* project database (data/materials.csv), not the synthetic
sample used by the unit tests. Each test covers one end-to-end
workflow a user of this project actually performs:

    load -> search -> filter -> rank -> compare

Unlike the unit tests, these intentionally avoid asserting exact
values baked into the current CSV (row counts, specific materials
winning a ranking, ...) where that would make the suite brittle to
future data changes - they check the *contracts* between modules
instead: every filter constraint is actually honored, sorting actually
sorts, comparison actually returns the materials asked for, and so on.
"""

import pandas as pd
import pytest

from src.comparator import MaterialComparator
from src.database import MaterialDatabase
from src.search import SearchEngine
from src.selection_engine import SelectionEngine


class TestLoadDatabaseIntegration:
    def test_loads_real_csv(self, real_data_path):
        db = MaterialDatabase(real_data_path)
        assert len(db.data) > 0
        for column in MaterialDatabase.REQUIRED_COLUMNS:
            assert column in db.data.columns

    def test_list_and_get_material_agree(self, real_database):
        names = real_database.list_materials()
        assert len(names) == len(real_database.data)

        first_name = names[0]
        row = real_database.get_material(first_name)
        assert row["name"] == first_name


class TestSearchWorkflowIntegration:
    def test_search_by_category_only_returns_that_category(self, real_database):
        engine = SearchEngine(real_database.data)
        results = engine.search(category="Steel")
        assert not results.empty
        assert results["category"].str.contains("Steel", case=False).all()

    def test_range_filter_is_honored(self, real_database):
        engine = SearchEngine(real_database.data)
        results = engine.search(density_range=(None, 3.0))
        assert not results.empty
        assert (results["density_g_cm3"] <= 3.0).all()

    def test_sort_by_specific_strength_is_descending(self, real_database):
        engine = SearchEngine(real_database.data)
        results = engine.search(sort_by="specific_strength")
        ratios = list(results["strength_to_weight_ratio"])
        assert ratios == sorted(ratios, reverse=True)

    def test_chained_filter_sort_and_top_n(self, real_database):
        engine = SearchEngine(real_database.data)
        results = engine.search(
            relative_cost_range=(None, 15.0),
            sort_by="specific_strength",
            top_n=5,
        )
        assert len(results) <= 5
        assert (results["cost_usd_per_kg"] <= 15.0).all()
        ratios = list(results["strength_to_weight_ratio"])
        assert ratios == sorted(ratios, reverse=True)


class TestFilteringWorkflowIntegration:
    def test_selection_engine_filter_honors_every_constraint(self, real_database):
        engine = SelectionEngine(real_database.data)
        ranked = engine.select(
            goal="balanced",
            max_cost=20.0,
            max_density=5.0,
            top_n=50,
        )
        assert not ranked.empty
        assert (ranked["cost_usd_per_kg"] <= 20.0).all()
        assert (ranked["density_g_cm3"] <= 5.0).all()

    def test_category_filter_narrows_to_requested_categories(self, real_database):
        engine = SelectionEngine(real_database.data)
        ranked = engine.select(
            goal="balanced", categories=["Aluminum Alloys"], top_n=50,
        )
        assert not ranked.empty
        assert (ranked["category"] == "Aluminum Alloys").all()


class TestRankingWorkflowIntegration:
    def test_lightweight_strength_ranking_is_sorted_descending(self, real_database):
        engine = SelectionEngine(real_database.data)
        ranked = engine.select(goal="lightweight_strength", top_n=10)

        scores = list(ranked["match_score"])
        assert scores == sorted(scores, reverse=True)

    def test_different_goals_can_change_the_winner(self, real_database):
        engine = SelectionEngine(real_database.data)
        lightweight_winner = engine.select(goal="lightweight_strength", top_n=1).iloc[0]["name"]
        budget_winner = engine.select(goal="budget_friendly", top_n=1).iloc[0]["name"]

        # Not a hard requirement that they differ (data could coincidentally
        # agree), but both must at least be valid materials from the table.
        assert lightweight_winner in real_database.data["name"].values
        assert budget_winner in real_database.data["name"].values


class TestComparisonWorkflowIntegration:
    COMPARE_NAMES = [
        "Aluminum 6061-T6",
        "Titanium Ti-6Al-4V",
        "Carbon Fiber Composite (CFRP)",
        "Structural Steel A36",
    ]

    def test_compare_matches_individual_lookups(self, real_database):
        comparator = MaterialComparator(real_database.data)
        table = comparator.compare(self.COMPARE_NAMES)

        assert len(table) == len(self.COMPARE_NAMES)
        for name in self.COMPARE_NAMES:
            row = table[table["name"] == name].iloc[0]
            db_row = real_database.get_material(name)
            assert row["density_g_cm3"] == pytest.approx(db_row["density_g_cm3"])
            assert row["tensile_strength_mpa"] == pytest.approx(db_row["tensile_strength_mpa"])

    def test_full_pipeline_search_then_compare(self, real_database):
        """A realistic user flow: search for a handful of materials,
        then compare exactly the ones found."""
        engine = SearchEngine(real_database.data)
        found = engine.search(category="Titanium Alloys", top_n=2)
        assert len(found) == 2

        comparator = MaterialComparator(real_database.data)
        table = comparator.compare(list(found["name"]))
        assert set(table["name"]) == set(found["name"])


class TestSearchEngineDerivedColumnsMatchComparator:
    """Both SearchEngine and MaterialComparator compute their derived
    columns via the same add_calculated_columns() - this test pins
    down that they never drift apart."""

    def test_specific_strength_matches_between_modules(self, real_database):
        search_value = SearchEngine(real_database.data).data.set_index("name")[
            "strength_to_weight_ratio"
        ]
        comparator_value = MaterialComparator(real_database.data).data.set_index("name")[
            "strength_to_weight_ratio"
        ]
        pd.testing.assert_series_equal(
            search_value.sort_index(), comparator_value.sort_index(), check_names=False,
        )
