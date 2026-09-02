"""A scenario must export with its inputs, not only its results.

A results table says what happened; it does not say what was asked for. The
Excel workbook used to carry only the yearly results, so a colleague opening it
could not see the paddock or the plan that produced them.
"""
from __future__ import annotations

import io

import pandas as pd
import pytest

from rim.defaults import (
    DEFAULT_OPTIONS,
    DEFAULT_PRICES,
    DEFAULT_PROFILE,
    build_default_strategy,
)
from utils.export import (
    scenario_to_excel_bytes,
    settings_to_frame,
    strategy_to_frame,
)


def _workbook(**overrides) -> pd.ExcelFile:
    payload = dict(
        strategy_rows=build_default_strategy(10),
        profile=DEFAULT_PROFILE,
        prices=DEFAULT_PRICES,
        options=DEFAULT_OPTIONS,
    )
    payload.update(overrides)
    return pd.ExcelFile(io.BytesIO(scenario_to_excel_bytes(**payload)))


def test_the_workbook_carries_the_inputs() -> None:
    sheets = _workbook().sheet_names

    assert sheets[:4] == ["Strategy", "Paddock profile", "Prices", "Options"], (
        "inputs come first: a reader wants the plan before the numbers"
    )


def test_results_are_included_when_present() -> None:
    frame = pd.DataFrame({"year": [1, 2], "gross_margin": [10.0, 20.0]})

    sheets = _workbook(results={"Current": frame, "Strategy A": frame}).sheet_names

    assert "Results Current" in sheets
    assert "Results Strategy A" in sheets


def test_a_scenario_with_no_results_still_exports() -> None:
    """Nothing is held yet, or the plan is not runnable — the inputs still travel."""
    assert _workbook(results=None).sheet_names == [
        "Strategy", "Paddock profile", "Prices", "Options"
    ]


def test_the_strategy_sheet_is_readable() -> None:
    """Column headings are the words the editor uses, not the model's field names."""
    frame = strategy_to_frame(build_default_strategy(10))

    assert list(frame.columns)[:3] == ["Year", "Crop", "Sowing time"]
    assert len(frame) == 10
    assert "seeding_timing" not in frame.columns


def test_nested_settings_are_flattened_with_their_group() -> None:
    """Per-crop yields and control effects keep the group they sat in."""
    frame = settings_to_frame("Paddock profile", DEFAULT_PROFILE)

    assert list(frame.columns) == ["Group", "Setting", "Value"]
    wheat = frame[(frame["Group"] == "base_yields") & (frame["Setting"] == "Wheat")]
    assert len(wheat) == 1
    assert wheat["Value"].iloc[0] == pytest.approx(DEFAULT_PROFILE["base_yields"]["Wheat"])


def test_deeply_nested_settings_survive() -> None:
    """Options nest two deep — control_effect / knockdown / Single knock-down."""
    frame = settings_to_frame("Options", DEFAULT_OPTIONS)
    groups = set(frame["Group"])

    assert any(group.startswith("control_effect / ") for group in groups)


def test_sheet_names_stay_within_the_excel_limit() -> None:
    """Excel refuses a sheet name over 31 characters."""
    frame = pd.DataFrame({"year": [1]})
    long_name = "A extremely long strategy label that Excel will not accept"

    for sheet in _workbook(results={long_name: frame}).sheet_names:
        assert len(sheet) <= 31
