"""
Unit tests for src/search.py - text search, range/corrosion filters,
sorting, the SearchEngine facade, and database statistics.
"""

import pytest

from src.search import (
    RESULT_COLUMNS,
    SearchEngine,
    filter_by_ranges,
    get_statistics,
    print_statistics,
    search_by_text,
    sort_materials,
)


class TestSearchByText:
    def test_name_substring_match(self, sample_df):
        result = search_by_text(sample_df, name="Alpha")
        assert list(result["name"]) == ["Alpha Steel"]

    def test_is_case_insensitive(self, sample_df):
        result = search_by_text(sample_df, name="alpha")
        assert len(result) == 1

    def test_category_substring_matches_all(self, sample_df):
        result = search_by_text(sample_df, category="Test")
        assert len(result) == 4

    def test_subcategory_is_its_own_field(self, sample_df):
        # "Alloy" is in Beta Alloy's *name* and *category*, but only
        # Alpha Steel's *subcategory* actually says "Alloy".
        result = search_by_text(sample_df, subcategory="Alloy")
        assert list(result["name"]) == ["Alpha Steel"]

    def test_combined_filters_are_and_not_or(self, sample_df):
        result = search_by_text(sample_df, category="Test", name="Beta")
        assert list(result["name"]) == ["Beta Alloy"]

    def test_no_terms_returns_everything(self, sample_df):
        result = search_by_text(sample_df)
        assert len(result) == len(sample_df)


class TestFilterByRanges:
    def test_min_and_max_density(self, sample_df):
        result = filter_by_ranges(sample_df, density_range=(2.0, 8.0))
        assert set(result["name"]) == {"Alpha Steel", "Beta Alloy"}

    def test_max_only(self, sample_df):
        result = filter_by_ranges(sample_df, density_range=(None, 2.0))
        assert set(result["name"]) == {"Beta Alloy", "Gamma Composite", "Delta Polymer"}

    def test_min_only(self, sample_df):
        result = filter_by_ranges(sample_df, density_range=(8.0, None))
        assert list(result["name"]) == ["Alpha Steel"]

    def test_corrosion_resistance_minimum(self, sample_df):
        result = filter_by_ranges(sample_df, corrosion_resistance="Good")
        assert set(result["name"]) == {"Beta Alloy", "Gamma Composite", "Delta Polymer"}

    def test_corrosion_resistance_excellent_only(self, sample_df):
        result = filter_by_ranges(sample_df, corrosion_resistance="Excellent")
        assert set(result["name"]) == {"Gamma Composite", "Delta Polymer"}

    def test_unknown_corrosion_value_raises(self, sample_df):
        with pytest.raises(ValueError):
            filter_by_ranges(sample_df, corrosion_resistance="Superb")

    def test_unknown_range_filter_key_raises(self, sample_df):
        with pytest.raises(ValueError):
            filter_by_ranges(sample_df, not_a_real_filter=(1, 2))

    def test_combining_range_and_corrosion(self, sample_df):
        result = filter_by_ranges(
            sample_df, density_range=(None, 2.0), corrosion_resistance="Excellent",
        )
        assert set(result["name"]) == {"Gamma Composite", "Delta Polymer"}


class TestSortMaterials:
    def test_density_default_ascending(self, sample_df):
        result = sort_materials(sample_df, sort_by="density")
        assert list(result["name"]) == [
            "Delta Polymer", "Gamma Composite", "Beta Alloy", "Alpha Steel",
        ]

    def test_strength_default_descending(self, sample_df):
        result = sort_materials(sample_df, sort_by="strength")
        assert list(result["name"]) == [
            "Gamma Composite", "Alpha Steel", "Beta Alloy", "Delta Polymer",
        ]

    def test_explicit_ascending_overrides_default(self, sample_df):
        result = sort_materials(sample_df, sort_by="density", ascending=False)
        assert list(result["name"])[0] == "Alpha Steel"

    def test_none_returns_unchanged(self, sample_df):
        result = sort_materials(sample_df, sort_by=None)
        assert list(result["name"]) == list(sample_df["name"])

    def test_unknown_sort_key_raises(self, sample_df):
        with pytest.raises(ValueError):
            sort_materials(sample_df, sort_by="not_a_real_key")


class TestSearchEngine:
    def test_search_with_no_args_returns_everything(self, sample_df):
        engine = SearchEngine(sample_df)
        result = engine.search()
        assert len(result) == 4
        assert list(result.columns) == RESULT_COLUMNS

    def test_search_by_name(self, sample_df):
        engine = SearchEngine(sample_df)
        result = engine.search(name="Beta")
        assert len(result) == 1

    def test_search_sort_by_specific_strength(self, sample_df):
        engine = SearchEngine(sample_df)
        result = engine.search(category="Test", sort_by="specific_strength")
        assert list(result["name"]) == [
            "Gamma Composite", "Beta Alloy", "Alpha Steel", "Delta Polymer",
        ]

    def test_search_top_n(self, sample_df):
        engine = SearchEngine(sample_df)
        result = engine.search(top_n=2)
        assert len(result) == 2

    def test_search_impossible_range_returns_empty_with_correct_columns(self, sample_df):
        engine = SearchEngine(sample_df)
        result = engine.search(density_range=(100, 200))
        assert result.empty
        assert list(result.columns) == RESULT_COLUMNS

    def test_search_invalid_corrosion_raises(self, sample_df):
        engine = SearchEngine(sample_df)
        with pytest.raises(ValueError):
            engine.search(corrosion_resistance="Superb")


class TestGetStatistics:
    def test_statistics_values(self, sample_df):
        stats = get_statistics(sample_df)

        assert stats["total_materials"] == 4
        assert stats["average_density_g_cm3"] == pytest.approx((8 + 2 + 1.5 + 1.2) / 4)
        assert stats["average_tensile_strength_mpa"] == pytest.approx((500 + 400 + 900 + 50) / 4)
        assert stats["strongest_material"] == "Gamma Composite"
        assert stats["lightest_material"] == "Delta Polymer"
        assert stats["cheapest_material"] == "Delta Polymer"

    def test_category_counts(self, sample_df):
        stats = get_statistics(sample_df)
        assert stats["category_counts"] == {
            "Test Steels": 1, "Test Alloys": 1, "Test Composites": 1, "Test Polymers": 1,
        }


class TestPrintStatistics:
    def test_prints_expected_summary(self, sample_df, capsys):
        print_statistics(sample_df)
        output = capsys.readouterr().out

        assert "Total materials: 4" in output
        assert "Gamma Composite" in output
        assert "Delta Polymer" in output
