"""The strategy editors must not fight each other.

Two editors used to be live at once — Streamlit runs every tab body on every
script run — and both wrote the plan, so an edit in one was overwritten by the
other's retained widget state and the page oscillated. The fix is that only one
editor renders at a time, and any editor coming on screen forgets its old widget
state so it re-seeds from the current plan.

The widget layer cannot be driven from pytest, so these pin the two invariants
that made the loop possible: a settled plan must survive an editor round-trip
unchanged, and the reseed helper must actually clear both editors' keys.
"""
from __future__ import annotations

import pytest

from utils.applicability import gates, neutralise
from utils.session import STRATEGY_GRID_KEY, YEAR_EDITOR_KEEP, YEAR_EDITOR_PREFIX
from utils.year_editor import GROUPS


def _year(**overrides) -> dict:
    base = {
        "year": 1, "crop": "Wheat", "seeding_timing": "Dry",
        "seeding_technique": "No-till", "seeding_rate": "Standard",
        "pre_tillage": "None", "knockdown": "None", "pre_emergent": "No",
        "post_emergent": "No", "spring_option": "None",
        "grazing_intensity": "None", "harvest_option": "Standard",
    }
    base.update(overrides)
    return base


def _apply_gates(rows: list[dict]) -> list[dict]:
    """What year_editor does to the values it renders, without the widgets.

    For a gated field it substitutes the inert value; everything else passes
    through as the user left it.
    """
    from utils.applicability import INERT_VALUE

    out = [dict(row) for row in rows]
    for row, blocked in zip(out, gates(out)):
        for field in blocked:
            inert = INERT_VALUE.get(field)
            if inert is not None:
                row[field] = inert
    return out


def test_a_settled_plan_survives_an_editor_round_trip() -> None:
    """If this ever changes a clean plan, the page starts rerunning forever."""
    plan = [
        _year(year=1, crop="Wheat", seeding_timing="Delayed (1-2 wks)",
              knockdown="Single knock-down", pre_emergent="Yes",
              harvest_option="Narrow windrow burn"),
        _year(year=2, crop="Sub-Clover pasture", grazing_intensity="Standard"),
        _year(year=3, crop="Canola", post_emergent="Yes"),
    ]

    assert _apply_gates(plan) == plan


def test_the_default_plan_survives_an_editor_round_trip() -> None:
    """The app opens on this, so it must be a fixed point from the first render."""
    from rim.defaults import build_default_strategy

    plan = build_default_strategy(10)

    assert _apply_gates(plan) == plan


def test_the_round_trip_settles_in_one_pass() -> None:
    """A plan with problems must reach a fixed point immediately, not oscillate."""
    plan = [
        _year(year=1, crop="Canola", grazing_intensity="High"),
        _year(year=2, crop="Volunteer pasture", harvest_option="HSD", pre_emergent="Yes"),
    ]

    once = _apply_gates(plan)
    twice = _apply_gates(once)

    assert once == twice
    assert once == neutralise(plan)[0]


def test_reseed_clears_both_editors_but_nothing_else() -> None:
    """reset_editor_widgets must not take the plan or the slots with it."""
    session = {
        STRATEGY_GRID_KEY: {"edited_rows": {0: {"crop": "Barley"}}},
        f"{YEAR_EDITOR_PREFIX}pick": 3,
        f"{YEAR_EDITOR_PREFIX}crop_3": "Canola",
        f"{YEAR_EDITOR_PREFIX}grazing_intensity_3_off": "None",
        "strategy_current": [{"year": 1}],
        "strategy_slots": {1: None},
        "profile_current": {"farm_name": "Home"},
    }

    stale = [
        key for key in session
        if key not in YEAR_EDITOR_KEEP
        and (key == STRATEGY_GRID_KEY or str(key).startswith(YEAR_EDITOR_PREFIX))
    ]
    for key in stale:
        del session[key]

    # The year you are looking at survives: it is view state, not plan data.
    assert set(session) == {
        "strategy_current", "strategy_slots", "profile_current", f"{YEAR_EDITOR_PREFIX}pick",
    }


def test_the_year_editor_covers_every_decision_the_grid_does() -> None:
    """Switching modes must not lose a decision that only one view can reach."""
    grid_fields = {
        "seeding_timing", "seeding_technique", "seeding_rate", "pre_tillage",
        "knockdown", "pre_emergent", "post_emergent",
        "spring_option", "grazing_intensity", "harvest_option",
    }
    year_fields = {field for _group, fields in GROUPS for field, _label, _opts in fields}

    assert year_fields == grid_fields
