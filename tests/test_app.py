"""
Streamlit AppTest tests for app.py - the web dashboard.

AppTest runs the actual script (app.py) in a simulated Streamlit
session: every st.tabs() block executes on every run regardless of
which tab is visually selected in a browser (tabs are a client-side
display concern only), so setting a sidebar filter or a widget value
and calling `.run()` again exercises the Search Results, Charts, and
Compare Materials tabs together.

Widgets without an explicit `key=` in app.py are looked up by their
visible label via `_by_label()`, since Streamlit doesn't expose a
stable key for them; the five checkboxes on the Charts tab share only
two labels ("Log X axis" / "Log Y axis") but do have explicit keys, so
those are looked up with `at.checkbox(key=...)` instead.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "app.py")
TIMEOUT = 30


def _by_label(elements, label):
    for element in elements:
        if element.label == label:
            return element
    raise AssertionError(f"No element found with label {label!r}")


@pytest.fixture
def at() -> AppTest:
    """A freshly run AppTest instance - one per test, since Streamlit
    session state isn't meant to be shared across tests."""
    app_test = AppTest.from_file(APP_PATH)
    app_test.run(timeout=TIMEOUT)
    return app_test


class TestDashboardLoading:
    def test_loads_without_exception(self, at):
        assert not at.exception

    def test_title_is_shown(self, at):
        assert at.title[0].value == "Material Property Analyzer"

    def test_summary_cards_present(self, at):
        labels = {m.label for m in at.metric}
        assert {"Total Materials", "Categories", "Average Density", "Strongest Material"} <= labels

    def test_all_three_tabs_present(self, at):
        tab_labels = [tab.label for tab in at.tabs]
        assert tab_labels == ["Search Results", "Charts", "Compare Materials"]

    def test_sidebar_filters_present(self, at):
        assert _by_label(at.sidebar.text_input, "Search by name") is not None
        assert _by_label(at.sidebar.selectbox, "Category") is not None
        assert _by_label(at.sidebar.selectbox, "Subcategory") is not None
        assert _by_label(at.sidebar.selectbox, "Minimum Corrosion Resistance") is not None

    def test_results_table_shown_by_default(self, at):
        assert len(at.dataframe) >= 1


class TestSearch:
    def test_search_by_name_narrows_results(self, at):
        total_before = int(at.sidebar.caption[0].value.split(" of ")[1].split(" ")[0])

        _by_label(at.sidebar.text_input, "Search by name").input("Titanium").run(timeout=TIMEOUT)

        assert not at.exception
        matched, total_after = at.sidebar.caption[0].value.split(" of ")
        assert int(matched) < total_before
        assert total_after.startswith(str(total_before))

        results_table = at.dataframe[0].value
        assert results_table["name"].str.contains("titanium", case=False).all()

    def test_category_filter_narrows_results(self, at):
        category_select = _by_label(at.sidebar.selectbox, "Category")
        target_category = category_select.options[1]  # index 0 is "All"

        category_select.select(target_category).run(timeout=TIMEOUT)

        assert not at.exception
        results_table = at.dataframe[0].value
        assert (results_table["category"] == target_category).all()

    def test_no_matches_shows_warning_not_an_exception(self, at):
        _by_label(at.sidebar.text_input, "Search by name").input(
            "Definitely Not A Real Material Name"
        ).run(timeout=TIMEOUT)

        assert not at.exception
        assert any("No materials match" in w.value for w in at.warning)

    def test_corrosion_resistance_filter(self, at):
        corrosion_select = _by_label(at.sidebar.selectbox, "Minimum Corrosion Resistance")

        corrosion_select.select("Excellent").run(timeout=TIMEOUT)

        assert not at.exception
        results_table = at.dataframe[0].value
        assert (results_table["corrosion_resistance"] == "Excellent").all()


class TestMaterialDetails:
    def test_default_selection_shows_engineering_ratios(self, at):
        labels = {m.label for m in at.metric}
        assert {"Specific Strength", "Specific Stiffness", "Relative Cost Index"} <= labels

    def test_selecting_a_different_material_updates_the_metrics(self, at):
        detail_select = _by_label(at.selectbox, "Select a material to view all properties")
        before = {m.label: m.value for m in at.metric}

        # Pick an option different from the current default.
        other_material = next(o for o in detail_select.options if o != detail_select.value)
        detail_select.select(other_material).run(timeout=TIMEOUT)

        assert not at.exception
        after = {m.label: m.value for m in at.metric}
        assert before["Specific Strength"] != after["Specific Strength"]

    def test_detail_table_matches_selected_material(self, at):
        detail_select = _by_label(at.selectbox, "Select a material to view all properties")
        target = detail_select.options[0]
        detail_select.select(target).run(timeout=TIMEOUT)

        detail_table = at.table[0].value
        assert detail_table.loc["name", "Value"] == target


class TestComparison:
    def test_fewer_than_two_selections_shows_info_message(self, at):
        assert any("at least two materials" in info.value for info in at.info)

    def test_two_materials_produces_comparison_table(self, at):
        compare_widget = at.multiselect[0]
        first, second = compare_widget.options[0], compare_widget.options[1]

        compare_widget.select(first).select(second).run(timeout=TIMEOUT)

        assert not at.exception
        comparison_table = at.dataframe[-1].value
        assert len(comparison_table) == 2
        assert set(comparison_table["name"]) == {first, second}
        assert "specific_strength" in comparison_table.columns

    def test_max_three_materials_allowed(self, at):
        compare_widget = at.multiselect[0]
        three = compare_widget.options[:3]
        result = compare_widget
        for name in three:
            result = result.select(name)
        result.run(timeout=TIMEOUT)

        assert not at.exception
        comparison_table = at.dataframe[-1].value
        assert len(comparison_table) == 3


class TestChartsTab:
    def test_charts_render_without_exception_on_default_filters(self, at):
        # st.tabs content all executes regardless of visual selection,
        # so a plain run already exercises the Charts tab's code path.
        assert not at.exception

    def test_charts_tab_warns_when_no_materials_match(self, at):
        _by_label(at.sidebar.text_input, "Search by name").input(
            "Definitely Not A Real Material Name"
        ).run(timeout=TIMEOUT)

        assert not at.exception
        assert any("charts need at least one match" in w.value for w in at.warning)

    def test_switching_the_ashby_chart_preset(self, at):
        chart_select = _by_label(at.selectbox, "Chart")
        other_option = next(o for o in chart_select.options if o != chart_select.value)

        chart_select.select(other_option).run(timeout=TIMEOUT)

        assert not at.exception

    def test_toggling_log_axis_checkboxes(self, at):
        for key in ("rank_log_x", "density_log_x", "density_log_y", "ashby_log_x", "ashby_log_y"):
            checkbox = at.checkbox(key=key)
            checkbox.set_value(not checkbox.value).run(timeout=TIMEOUT)
            assert not at.exception
