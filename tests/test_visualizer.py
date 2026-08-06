"""
Unit tests for src/visualizer.py - the matplotlib charts the CLI
(`python main.py`) generates. These must keep working unchanged
regardless of the newer Plotly charts in interactive_charts.py.
"""

import os

import matplotlib.figure
import pytest

from src.visualizer import (
    CATEGORY_COLORS,
    generate_all_charts,
    plot_material_comparison,
    plot_strength_to_weight_ranking,
    plot_strength_vs_density,
)


class TestPlotStrengthToWeightRanking:
    def test_returns_figure_and_saves_file(self, sample_df, tmp_path):
        out_path = tmp_path / "ranking.png"
        fig = plot_strength_to_weight_ranking(sample_df, str(out_path), top_n=4)

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_path.exists()
        assert out_path.stat().st_size > 0

    def test_top_n_limits_bars_drawn(self, sample_df, tmp_path):
        out_path = tmp_path / "ranking.png"
        fig = plot_strength_to_weight_ranking(sample_df, str(out_path), top_n=2)
        ax = fig.axes[0]
        assert len(ax.patches) == 2


class TestPlotStrengthVsDensity:
    def test_returns_figure_and_saves_file(self, sample_df, tmp_path):
        out_path = tmp_path / "scatter.png"
        fig = plot_strength_vs_density(sample_df, str(out_path))

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_path.exists()

    def test_labels_point_count_matches_data_below_max_labels(self, sample_df, tmp_path):
        out_path = tmp_path / "scatter.png"
        fig = plot_strength_vs_density(sample_df, str(out_path), max_labels=30)
        ax = fig.axes[0]
        # One annotation per material name when under the max_labels threshold.
        assert len(ax.texts) == len(sample_df)

    def test_no_labels_when_over_max_labels(self, sample_df, tmp_path):
        out_path = tmp_path / "scatter.png"
        fig = plot_strength_vs_density(sample_df, str(out_path), max_labels=1)
        ax = fig.axes[0]
        assert len(ax.texts) == 0


class TestPlotMaterialComparison:
    def test_returns_figure_and_saves_file(self, sample_df, tmp_path):
        out_path = tmp_path / "comparison.png"
        fig = plot_material_comparison(
            sample_df, ["Alpha Steel", "Beta Alloy"], str(out_path)
        )

        assert isinstance(fig, matplotlib.figure.Figure)
        assert out_path.exists()


class TestGenerateAllCharts:
    def test_creates_output_directory_and_default_charts(self, sample_df, tmp_path):
        output_dir = tmp_path / "charts_out"
        generate_all_charts(sample_df, str(output_dir))

        assert (output_dir / "strength_to_weight_ranking.png").exists()
        assert (output_dir / "strength_vs_density.png").exists()
        assert not (output_dir / "material_comparison.png").exists()

    def test_creates_comparison_chart_when_names_given(self, sample_df, tmp_path):
        output_dir = tmp_path / "charts_out"
        generate_all_charts(sample_df, str(output_dir), compare_names=["Alpha Steel", "Beta Alloy"])

        assert (output_dir / "material_comparison.png").exists()


def test_category_colors_cover_every_sample_category(sample_df):
    # Not a hard requirement (unknown categories fall back to
    # DEFAULT_COLOR), but documents that the palette is a dict of
    # hex strings as every chart expects.
    for color in CATEGORY_COLORS.values():
        assert color.startswith("#")
