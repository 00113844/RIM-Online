"""The gate must open and close on exactly the right plans.

Results computed from a plan the model half-ignores look authoritative and
quietly answer a different question, so the simulation is withheld until the
plan is consistent. These pin when that happens.
"""
from __future__ import annotations

import pytest

from utils.applicability import neutralise
from utils.validation import REMEDY, problems


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


def test_a_consistent_plan_opens_the_gate() -> None:
    plan = [
        _year(year=1, crop="Wheat", seeding_timing="Delayed (1-2 wks)",
              knockdown="Single knock-down", pre_emergent="Yes",
              harvest_option="Narrow windrow burn"),
        _year(year=2, crop="Sub-Clover pasture", grazing_intensity="Standard"),
    ]

    assert problems(plan) == []


def test_the_shipped_default_plan_is_runnable() -> None:
    """The app must not open on a plan that trips its own gate.

    The default used to select a knock-down in every year with dry sowing, which
    the model ignores — so a new user met a wall of problems before touching
    anything. Pinned here because it is the first thing anyone sees.
    """
    from rim.defaults import build_default_strategy

    assert problems(build_default_strategy(10)) == []


def test_fixing_opens_the_gate_and_is_idempotent() -> None:
    """Pressing 'clear and run' must actually leave a runnable plan."""
    plan = [
        _year(year=1, crop="Canola", grazing_intensity="High"),
        _year(year=2, crop="Volunteer pasture", harvest_option="HSD"),
        _year(year=3, crop="Wheat", knockdown="Double knock-down", seeding_timing="Wet"),
    ]

    cleaned, changes = neutralise(plan)

    assert len(changes) == 3
    assert problems(cleaned) == []
    assert neutralise(cleaned)[1] == []


def test_every_problem_has_a_remedy_to_show() -> None:
    """The panel tells the user what to do, so no field may fall through."""
    plan = [
        _year(year=1, crop="Canola", grazing_intensity="Standard"),
        _year(year=2, crop="Volunteer pasture", harvest_option="HSD", pre_emergent="Yes"),
        _year(year=3, crop="Wheat", knockdown="Single knock-down"),
    ]

    for problem in problems(plan):
        assert problem["field"] in REMEDY, f"no remedy copy for {problem['field']}"


def test_every_problem_carries_its_excel_source() -> None:
    plan = [_year(crop="Canola", grazing_intensity="Standard", knockdown="Paraquat")]

    for problem in problems(plan):
        assert problem["source"], problem["field"]


def test_problems_are_reported_per_year() -> None:
    """Years matter: the panel names them, and the user has to find the row."""
    plan = [
        _year(year=1, crop="Wheat"),
        _year(year=2, crop="Canola", grazing_intensity="High"),
        _year(year=3, crop="Wheat"),
    ]

    found = problems(plan)

    assert [f["year"] for f in found] == [2]
