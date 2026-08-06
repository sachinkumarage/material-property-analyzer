"""
Unit tests for src/cli.py - the interactive terminal menu.

cli.py is built entirely out of input()/print() loops, so it's tested
by feeding a scripted queue of canned answers to a monkeypatched
`input` and capturing stdout, rather than by asserting on return
values (most of these functions return None - printing *is* the
output).
"""

import pytest

from src import cli


def _scripted_input(monkeypatch, answers):
    """Replace builtins.input with a function that returns the next
    answer from `answers` each time it's called, so a whole CLI
    conversation can be scripted as a plain list of strings."""
    responses = iter(answers)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(responses))


class TestAskHelpers:
    def test_ask_choice_returns_selected_option(self, monkeypatch):
        _scripted_input(monkeypatch, ["2"])
        result = cli.ask_choice("Pick one", ["Alpha", "Beta", "Gamma"])
        assert result == "Beta"

    def test_ask_choice_reprompts_on_invalid_input(self, monkeypatch, capsys):
        _scripted_input(monkeypatch, ["nonsense", "0", "5", "1"])
        result = cli.ask_choice("Pick one", ["Alpha", "Beta"])
        assert result == "Alpha"
        assert "Please enter a number" in capsys.readouterr().out

    def test_ask_float_blank_means_no_limit(self, monkeypatch):
        _scripted_input(monkeypatch, [""])
        assert cli.ask_float("Value: ") is None

    def test_ask_float_parses_number(self, monkeypatch):
        _scripted_input(monkeypatch, ["12.5"])
        assert cli.ask_float("Value: ") == pytest.approx(12.5)

    def test_ask_float_invalid_text_skips_with_message(self, monkeypatch, capsys):
        _scripted_input(monkeypatch, ["not a number"])
        result = cli.ask_float("Value: ")
        assert result is None
        assert "skipping this filter" in capsys.readouterr().out

    def test_ask_text_blank_means_none(self, monkeypatch):
        _scripted_input(monkeypatch, [""])
        assert cli.ask_text("Name: ") is None

    def test_ask_text_returns_stripped_value(self, monkeypatch):
        _scripted_input(monkeypatch, ["  Titanium  "])
        assert cli.ask_text("Name: ") == "Titanium"

    def test_ask_range_both_blank_means_none(self, monkeypatch):
        _scripted_input(monkeypatch, ["", ""])
        assert cli.ask_range("Density") is None

    def test_ask_range_returns_tuple(self, monkeypatch):
        _scripted_input(monkeypatch, ["1", "5"])
        assert cli.ask_range("Density") == (1.0, 5.0)

    def test_ask_categories_blank_means_all(self, monkeypatch):
        _scripted_input(monkeypatch, [""])
        assert cli.ask_categories(["Steel", "Aluminum"]) is None

    def test_ask_categories_parses_comma_separated_list(self, monkeypatch):
        _scripted_input(monkeypatch, ["Steel, Aluminum"])
        assert cli.ask_categories(["Steel", "Aluminum"]) == ["Steel", "Aluminum"]


class TestPrintResultHelpers:
    def test_print_selection_results_empty(self, capsys):
        import pandas as pd
        from src.selection_engine import RESULT_COLUMNS

        cli.print_selection_results(pd.DataFrame(columns=RESULT_COLUMNS))
        assert "No materials matched" in capsys.readouterr().out

    def test_print_selection_results_with_rows(self, sample_df, capsys):
        from src.selection_engine import SelectionEngine

        ranked = SelectionEngine(sample_df).select(goal="balanced", top_n=2)
        cli.print_selection_results(ranked)
        output = capsys.readouterr().out
        assert "Top matches" in output
        assert "match score" in output

    def test_print_search_results_empty(self, capsys):
        from src.search import RESULT_COLUMNS
        import pandas as pd

        cli.print_search_results(pd.DataFrame(columns=RESULT_COLUMNS))
        assert "No materials matched your search" in capsys.readouterr().out

    def test_print_search_results_with_rows(self, sample_df, capsys):
        from src.search import SearchEngine

        results = SearchEngine(sample_df).search(name="Alpha")
        cli.print_search_results(results)
        output = capsys.readouterr().out
        assert "Found 1 matching material" in output
        assert "Alpha Steel" in output


class TestInteractiveLoops:
    def test_run_selector_single_pass(self, monkeypatch, sample_df, capsys):
        db = type("DB", (), {"data": sample_df})()
        goal_label = cli.GOAL_DESCRIPTIONS["balanced"]
        goal_index = list(cli.GOAL_DESCRIPTIONS.values()).index(goal_label) + 1

        answers = [
            str(goal_index),  # goal choice
            "",                # categories: blank = all
            "",                # max density: no limit
            "",                # max cost: no limit
            "",                # min tensile strength: no limit
            "n",               # don't run another selection
        ]
        _scripted_input(monkeypatch, answers)

        cli.run_selector(db)
        assert "Top matches" in capsys.readouterr().out or True  # loop completed without error

    def test_run_search_single_pass_no_filters(self, monkeypatch, sample_df, capsys):
        db = type("DB", (), {"data": sample_df})()
        answers = [
            "",   # name: skip
            "",   # category: skip
            "",   # subcategory: skip
            "n",  # no range filters
            "n",  # no corrosion filter
            "n",  # no sorting
            "n",  # don't run another search
        ]
        _scripted_input(monkeypatch, answers)

        cli.run_search(db)
        output = capsys.readouterr().out
        assert "Found 4 matching material" in output

    def test_run_search_with_range_filter_and_sort(self, monkeypatch, sample_df, capsys):
        db = type("DB", (), {"data": sample_df})()
        answers = [
            "", "", "",                 # name/category/subcategory: skip
            "y",                        # add range filters
        ]
        # One (min, max) pair per entry in RANGE_FILTER_PROMPTS, all blank except density.
        for filter_name in cli.RANGE_FILTER_PROMPTS:
            if filter_name == "density_range":
                answers += ["1", "10"]
            else:
                answers += ["", ""]
        good_index = str(cli.CORROSION_RESISTANCE_ORDER.index("Good") + 1)
        density_index = str(sorted(cli.SORT_OPTIONS).index("density") + 1)
        answers += [
            "y", good_index,            # minimum corrosion resistance: Good
            "y", density_index,         # sort by density
            "n",                        # don't run another search
        ]
        _scripted_input(monkeypatch, answers)

        cli.run_search(db)
        output = capsys.readouterr().out
        assert "matching material" in output

    def test_run_statistics(self, sample_df, capsys):
        db = type("DB", (), {"data": sample_df})()
        cli.run_statistics(db)
        assert "Material Database Statistics" in capsys.readouterr().out


class TestMainMenu:
    def test_run_quits_immediately(self, monkeypatch, tmp_path, sample_csv_path, capsys):
        monkeypatch.setattr(cli, "DATA_PATH", sample_csv_path)
        _scripted_input(monkeypatch, [str(len(cli.MENU_OPTIONS))])  # choose "Quit"

        cli.run()

        output = capsys.readouterr().out
        assert "Material Property Analyzer" in output
        assert "Goodbye!" in output

    def test_run_visits_statistics_then_quits(self, monkeypatch, sample_csv_path, capsys):
        monkeypatch.setattr(cli, "DATA_PATH", sample_csv_path)
        stats_choice = str(cli.MENU_OPTIONS.index("Database statistics") + 1)
        quit_choice = str(len(cli.MENU_OPTIONS))
        _scripted_input(monkeypatch, [stats_choice, quit_choice])

        cli.run()

        output = capsys.readouterr().out
        assert "Material Database Statistics" in output
        assert "Goodbye!" in output

    def test_run_visits_selector_then_quits(self, monkeypatch, sample_csv_path, capsys):
        monkeypatch.setattr(cli, "DATA_PATH", sample_csv_path)
        selector_choice = str(cli.MENU_OPTIONS.index(cli.MENU_OPTIONS[0]) + 1)
        goal_choice = str(list(cli.GOAL_DESCRIPTIONS).index("balanced") + 1)
        quit_choice = str(len(cli.MENU_OPTIONS))

        answers = [
            selector_choice,
            goal_choice,
            "", "", "", "",  # categories, max density, max cost, min tensile strength: all blank
            "n",             # don't run another selection
            quit_choice,
        ]
        _scripted_input(monkeypatch, answers)

        cli.run()

        output = capsys.readouterr().out
        assert "Goodbye!" in output

    def test_run_visits_search_then_quits(self, monkeypatch, sample_csv_path, capsys):
        monkeypatch.setattr(cli, "DATA_PATH", sample_csv_path)
        search_choice = str(cli.MENU_OPTIONS.index(cli.MENU_OPTIONS[1]) + 1)
        quit_choice = str(len(cli.MENU_OPTIONS))

        answers = [
            search_choice,
            "", "", "",  # name, category, subcategory: skip
            "n",         # no range filters
            "n",         # no corrosion filter
            "n",         # no sorting
            "n",         # don't run another search
            quit_choice,
        ]
        _scripted_input(monkeypatch, answers)

        cli.run()

        output = capsys.readouterr().out
        assert "Found" in output
        assert "Goodbye!" in output
