"""
Validation / edge-case tests: invalid data, empty results, formula
correctness across module boundaries, duplicate materials, and missing
values. These document how the system actually behaves at its edges -
not just its happy path - without changing any of that behavior.
"""

import numpy as np
import pandas as pd
import pytest

from src.calculations import add_calculated_columns, strength_to_weight_ratio
from src.comparator import MaterialComparator
from src.database import MaterialDatabase
from src.scoring import weighted_score
from src.search import SearchEngine, filter_by_ranges, search_by_text
from src.selection_engine import RESULT_COLUMNS, SelectionEngine


def _valid_row(**overrides) -> dict:
    """A single materials-CSV row satisfying every required column,
    with sensible defaults - override just the field(s) a test cares
    about breaking."""
    row = dict(
        name="Sample Material", category="Test Category", subcategory="Test Sub",
        density_g_cm3=5.0, yield_strength_mpa=200.0, tensile_strength_mpa=300.0,
        elastic_modulus_gpa=100.0, poisson_ratio=0.3, hardness_value=100.0,
        hardness_scale="HB", thermal_conductivity_w_mk=20.0,
        electrical_conductivity_percent_iacs=10.0, melting_point_c=1000,
        fatigue_strength_mpa=100.0, cost_usd_per_kg=5.0, corrosion_resistance="Good",
    )
    row.update(overrides)
    return row


# ---------------------------------------------------------------------
# Invalid data
# ---------------------------------------------------------------------

class TestInvalidData:
    def test_missing_required_column_raises_on_load(self, tmp_path):
        df = pd.DataFrame([_valid_row()]).drop(columns=["density_g_cm3"])
        path = tmp_path / "invalid.csv"
        df.to_csv(path, index=False)

        with pytest.raises(ValueError, match="density_g_cm3"):
            MaterialDatabase(str(path))

    def test_unparseable_csv_raises(self, tmp_path):
        path = tmp_path / "garbage.csv"
        path.write_bytes(b"\x00\x01\x02not,a,valid\ncsv\x00file")

        with pytest.raises(Exception):
            MaterialDatabase(str(path))

    def test_zero_density_rejected_by_formula(self):
        with pytest.raises(ValueError):
            strength_to_weight_ratio(100.0, 0.0)

    def test_negative_density_rejected_by_formula(self):
        with pytest.raises(ValueError):
            strength_to_weight_ratio(100.0, -3.0)

    def test_non_numeric_density_raises_type_error(self):
        with pytest.raises(TypeError):
            strength_to_weight_ratio(100.0, "not a number")


# ---------------------------------------------------------------------
# Empty search results
# ---------------------------------------------------------------------

class TestEmptyResults:
    def test_search_engine_returns_empty_frame_not_none(self, sample_df):
        engine = SearchEngine(sample_df)
        result = engine.search(name="Something That Does Not Exist")

        assert result is not None
        assert result.empty
        assert list(result.columns) == engine.search().columns.tolist()

    def test_selection_engine_returns_empty_frame_with_result_columns(self, sample_df):
        engine = SelectionEngine(sample_df)
        ranked = engine.select(goal="balanced", max_cost=0.0001)

        assert ranked.empty
        assert list(ranked.columns) == RESULT_COLUMNS

    def test_filter_by_ranges_on_impossible_range_is_empty_not_an_error(self, sample_df):
        result = filter_by_ranges(sample_df, density_range=(1000, 2000))
        assert result.empty

    def test_get_statistics_on_empty_dataframe_raises(self, sample_df):
        # Documents current behavior: idxmax/idxmin on an empty column
        # raise rather than silently returning a placeholder - callers
        # (search.py, the CLI) are expected to check for an empty
        # result *before* asking for statistics.
        from src.search import get_statistics

        empty = sample_df.iloc[0:0]
        with pytest.raises(ValueError):
            get_statistics(empty)


# ---------------------------------------------------------------------
# Formula correctness across module boundaries
# ---------------------------------------------------------------------

class TestFormulaCorrectnessEndToEnd:
    def test_calculated_columns_feed_correctly_into_scoring(self, sample_df):
        """
        density -> strength_to_weight_ratio (calculations.py)
                -> specific_strength_score  (scoring.py, min-max normalized)
                -> match_score              (scoring.py, weighted average)
        must all agree with a fully hand-computed chain for one row.
        """
        calculated = add_calculated_columns(sample_df).set_index("name")
        alpha_ratio = calculated.loc["Alpha Steel", "strength_to_weight_ratio"]
        assert alpha_ratio == pytest.approx(500 / 8.0)

        scored = weighted_score(sample_df, weights={"specific_strength_score": 1.0})
        scored = scored.set_index("name")

        ratios = calculated["strength_to_weight_ratio"]
        expected_alpha_score = 100 * (alpha_ratio - ratios.min()) / (ratios.max() - ratios.min())
        assert scored.loc["Alpha Steel", "specific_strength_score"] == pytest.approx(
            expected_alpha_score
        )
        assert scored.loc["Alpha Steel", "match_score"] == pytest.approx(expected_alpha_score)

    def test_relative_cost_index_is_a_pure_passthrough_at_baseline(self, sample_df):
        # BASELINE_COST_USD_PER_KG is 1.0, so relative_cost_index should
        # exactly equal cost_usd_per_kg for every row.
        result = add_calculated_columns(sample_df)
        pd.testing.assert_series_equal(
            result["relative_cost_index"], result["cost_usd_per_kg"],
            check_names=False,
        )


# ---------------------------------------------------------------------
# Duplicate materials
# ---------------------------------------------------------------------

class TestDuplicateMaterials:
    @pytest.fixture
    def duplicate_csv_path(self, tmp_path):
        rows = [
            _valid_row(name="Duplicate Steel", cost_usd_per_kg=1.0),
            _valid_row(name="Duplicate Steel", cost_usd_per_kg=99.0),
            _valid_row(name="Unique Alloy"),
        ]
        path = tmp_path / "duplicates.csv"
        pd.DataFrame(rows).to_csv(path, index=False)
        return str(path)

    def test_database_loads_both_duplicate_rows(self, duplicate_csv_path):
        db = MaterialDatabase(duplicate_csv_path)
        assert db.list_materials().count("Duplicate Steel") == 2

    def test_get_material_returns_first_duplicate(self, duplicate_csv_path):
        db = MaterialDatabase(duplicate_csv_path)
        row = db.get_material("Duplicate Steel")
        assert row["cost_usd_per_kg"] == pytest.approx(1.0)

    def test_search_finds_all_duplicates(self, duplicate_csv_path):
        db = MaterialDatabase(duplicate_csv_path)
        result = search_by_text(db.data, name="Duplicate Steel")
        assert len(result) == 2

    def test_comparator_returns_all_rows_matching_a_duplicated_name(self, duplicate_csv_path):
        db = MaterialDatabase(duplicate_csv_path)
        comparator = MaterialComparator(db.data)
        table = comparator.compare(["Duplicate Steel"])
        assert len(table) == 2


# ---------------------------------------------------------------------
# Missing values
# ---------------------------------------------------------------------

class TestMissingValues:
    @pytest.fixture
    def missing_values_df(self):
        rows = [
            _valid_row(name="Complete Material"),
            _valid_row(name="Missing Cost", cost_usd_per_kg=np.nan),
            _valid_row(name="Missing Corrosion", corrosion_resistance=np.nan),
            _valid_row(name="Missing Subcategory", subcategory=np.nan),
        ]
        return pd.DataFrame(rows)

    def test_missing_numeric_value_propagates_as_nan_not_a_crash(self, missing_values_df):
        result = add_calculated_columns(missing_values_df).set_index("name")
        assert pd.isna(result.loc["Missing Cost", "cost_per_unit_strength"])
        assert pd.isna(result.loc["Missing Cost", "relative_cost_index"])
        # Every other row's calculation is unaffected.
        assert not pd.isna(result.loc["Complete Material", "cost_per_unit_strength"])

    def test_missing_corrosion_resistance_is_excluded_by_minimum_filter(self, missing_values_df):
        result = filter_by_ranges(missing_values_df, corrosion_resistance="Poor")
        assert "Missing Corrosion" not in set(result["name"])
        assert "Complete Material" in set(result["name"])

    def test_missing_subcategory_never_matches_a_text_search(self, missing_values_df):
        result = search_by_text(missing_values_df, subcategory="Test")
        assert "Missing Subcategory" not in set(result["name"])
        assert "Complete Material" in set(result["name"])

    def test_missing_value_does_not_break_full_search_pipeline(self, missing_values_df):
        engine = SearchEngine(missing_values_df)
        result = engine.search()
        assert len(result) == len(missing_values_df)
