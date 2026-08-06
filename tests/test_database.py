"""
Unit tests for src/database.py - loading, reading, adding to, and
saving the materials CSV.
"""

import pandas as pd
import pytest

from src.database import MaterialDatabase


class TestLoad:
    def test_loads_all_rows(self, sample_csv_path):
        db = MaterialDatabase(sample_csv_path)
        assert len(db.data) == 4

    def test_has_required_columns(self, sample_csv_path):
        db = MaterialDatabase(sample_csv_path)
        for column in MaterialDatabase.REQUIRED_COLUMNS:
            assert column in db.data.columns

    def test_missing_column_raises_value_error(self, tmp_path, sample_records):
        df = pd.DataFrame(sample_records).drop(columns=["cost_usd_per_kg"])
        path = tmp_path / "broken.csv"
        df.to_csv(path, index=False)

        with pytest.raises(ValueError, match="cost_usd_per_kg"):
            MaterialDatabase(str(path))

    def test_missing_multiple_columns_all_named_in_error(self, tmp_path, sample_records):
        df = pd.DataFrame(sample_records).drop(columns=["cost_usd_per_kg", "hardness_scale"])
        path = tmp_path / "broken.csv"
        df.to_csv(path, index=False)

        with pytest.raises(ValueError) as excinfo:
            MaterialDatabase(str(path))
        assert "cost_usd_per_kg" in str(excinfo.value)
        assert "hardness_scale" in str(excinfo.value)


class TestListMaterials:
    def test_returns_all_names(self, sample_csv_path):
        db = MaterialDatabase(sample_csv_path)
        names = db.list_materials()
        assert names == ["Alpha Steel", "Beta Alloy", "Gamma Composite", "Delta Polymer"]


class TestGetMaterial:
    def test_returns_matching_row(self, sample_csv_path):
        db = MaterialDatabase(sample_csv_path)
        row = db.get_material("Beta Alloy")
        assert row["density_g_cm3"] == pytest.approx(2.0)

    def test_case_insensitive(self, sample_csv_path):
        db = MaterialDatabase(sample_csv_path)
        row = db.get_material("beta ALLOY")
        assert row["name"] == "Beta Alloy"

    def test_unknown_name_raises_key_error(self, sample_csv_path):
        db = MaterialDatabase(sample_csv_path)
        with pytest.raises(KeyError):
            db.get_material("Unobtainium")


class TestAddMaterial:
    def test_appends_row(self, sample_csv_path, sample_records):
        db = MaterialDatabase(sample_csv_path)
        new_material = dict(sample_records[0])
        new_material["name"] = "Epsilon Alloy"

        db.add_material(**new_material)

        assert len(db.data) == 5
        assert "Epsilon Alloy" in db.list_materials()

    def test_missing_property_raises_value_error(self, sample_csv_path, sample_records):
        db = MaterialDatabase(sample_csv_path)
        incomplete = dict(sample_records[0])
        incomplete.pop("cost_usd_per_kg")

        with pytest.raises(ValueError, match="cost_usd_per_kg"):
            db.add_material(**incomplete)

    def test_add_material_does_not_affect_original_row_count_until_called(
        self, sample_csv_path, sample_records
    ):
        db = MaterialDatabase(sample_csv_path)
        original_len = len(db.data)
        new_material = dict(sample_records[0])
        new_material["name"] = "Zeta Compound"
        db.add_material(**new_material)
        assert len(db.data) == original_len + 1


class TestSave:
    def test_save_round_trips(self, sample_csv_path, tmp_path):
        db = MaterialDatabase(sample_csv_path)
        out_path = tmp_path / "saved.csv"

        db.save(str(out_path))
        reloaded = MaterialDatabase(str(out_path))

        assert reloaded.list_materials() == db.list_materials()

    def test_save_defaults_to_original_path(self, sample_csv_path, sample_records):
        db = MaterialDatabase(sample_csv_path)
        new_material = dict(sample_records[0])
        new_material["name"] = "Eta Alloy"
        db.add_material(**new_material)

        db.save()

        reloaded = MaterialDatabase(sample_csv_path)
        assert "Eta Alloy" in reloaded.list_materials()
