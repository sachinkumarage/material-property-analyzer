"""
Unit tests for src/interactive_charts.py - the Plotly Ashby chart and
specific-strength-ranking chart builders used by the Streamlit
dashboard (Version 6/7).

These tests check the *figure structure* Plotly builds (trace count,
axis types, hover template, marker colors) rather than rendering
pixels - that's what actually matters for correctness, and it's fast
and deterministic.
"""

import pytest

from src.interactive_charts import (
    ASHBY_CHARTS,
    build_ashby_figure,
    build_specific_strength_ranking_figure,
    png_export_config,
)
from src.visualizer import CATEGORY_COLORS


class TestBuildAshbyFigure:
    @pytest.mark.parametrize("chart_key", list(ASHBY_CHARTS))
    def test_every_preset_builds_without_error(self, sample_df, chart_key):
        fig = build_ashby_figure(sample_df, chart_key)
        assert len(fig.data) > 0

    def test_one_trace_per_category(self, sample_df):
        fig = build_ashby_figure(sample_df, "strength_vs_density")
        assert len(fig.data) == sample_df["category"].nunique()

    def test_unknown_chart_key_raises(self, sample_df):
        with pytest.raises(ValueError):
            build_ashby_figure(sample_df, "not_a_real_chart")

    def test_log_axes_default_true(self, sample_df):
        fig = build_ashby_figure(sample_df, "strength_vs_density")
        assert fig.layout.xaxis.type == "log"
        assert fig.layout.yaxis.type == "log"

    def test_linear_axes_when_requested(self, sample_df):
        fig = build_ashby_figure(sample_df, "strength_vs_density", log_x=False, log_y=False)
        assert fig.layout.xaxis.type == "linear"
        assert fig.layout.yaxis.type == "linear"

    def test_trace_uses_category_color(self, sample_df):
        fig = build_ashby_figure(sample_df, "strength_vs_density")
        for trace in fig.data:
            assert trace.marker.color == CATEGORY_COLORS.get(trace.name, trace.marker.color)

    def test_hover_template_includes_all_fields(self, sample_df):
        fig = build_ashby_figure(sample_df, "strength_vs_density")
        template = fig.data[0].hovertemplate
        for label in ("Category", "Subcategory", "Density", "Yield strength",
                      "Tensile strength (UTS)", "Young's modulus", "Relative cost"):
            assert label in template

    def test_axis_titles_match_preset(self, sample_df):
        fig = build_ashby_figure(sample_df, "cost_vs_strength")
        spec = ASHBY_CHARTS["cost_vs_strength"]
        assert fig.layout.xaxis.title.text == spec["x_label"]
        assert fig.layout.yaxis.title.text == spec["y_label"]

    def test_customdata_row_count_matches_group_size(self, sample_df):
        fig = build_ashby_figure(sample_df, "strength_vs_density")
        total_points = sum(len(trace.x) for trace in fig.data)
        assert total_points == len(sample_df)


class TestBuildSpecificStrengthRankingFigure:
    def test_builds_without_error(self, sample_df):
        fig = build_specific_strength_ranking_figure(sample_df, top_n=10)
        assert len(fig.data) > 0

    def test_bars_are_horizontal(self, sample_df):
        fig = build_specific_strength_ranking_figure(sample_df, top_n=10)
        assert all(trace.orientation == "h" for trace in fig.data)

    def test_no_on_bar_text_labels(self, sample_df):
        # Regression check: bar labels used to duplicate the y-axis
        # material names and clutter the chart.
        fig = build_specific_strength_ranking_figure(sample_df, top_n=10)
        assert all(trace.textposition == "none" for trace in fig.data)

    def test_top_n_limits_bars(self, sample_df):
        fig = build_specific_strength_ranking_figure(sample_df, top_n=2)
        total_bars = sum(len(trace.x) for trace in fig.data)
        assert total_bars == 2

    def test_best_material_is_at_top_of_category_array(self, sample_df):
        fig = build_specific_strength_ranking_figure(sample_df, top_n=10)
        category_array = list(fig.layout.yaxis.categoryarray)
        # Gamma Composite has the highest strength_to_weight_ratio in
        # sample_df, and plotly bar charts draw the *last* categoryarray
        # entry at the top.
        assert category_array[-1] == "Gamma Composite"

    def test_log_x_axis_toggle(self, sample_df):
        fig = build_specific_strength_ranking_figure(sample_df, top_n=10, log_x=True)
        assert fig.layout.xaxis.type == "log"

    def test_linear_x_axis_by_default(self, sample_df):
        fig = build_specific_strength_ranking_figure(sample_df, top_n=10)
        assert fig.layout.xaxis.type == "linear"

    def test_hover_template_includes_specific_strength_line(self, sample_df):
        fig = build_specific_strength_ranking_figure(sample_df, top_n=10)
        assert "Specific strength" in fig.data[0].hovertemplate


class TestPngExportConfig:
    def test_returns_expected_shape(self):
        config = png_export_config("strength_vs_density")
        assert config["toImageButtonOptions"]["format"] == "png"
        assert "strength_vs_density" in config["toImageButtonOptions"]["filename"]
        assert config["displaylogo"] is False
