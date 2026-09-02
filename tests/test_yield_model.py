"""Verify rim.yield_model reproduces Bio results!D23:D54 exactly.

Expected values are the workbook's own yield rows, carried in each fixture's
``reference.yields``. The whole chain runs from the strategy grid, so a yield
figure here is only right if every block before it was right too.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from rim.yield_model import (
    WORKBOOK_DEFECTS,
    load_parameters,
    management_adjustment,
    retained_fraction,
)
from tests.chain import YIELD_GROUPS, fixtures, walk

TOLERANCE = 1e-9


@pytest.mark.parametrize("fixture_path", fixtures(), ids=lambda p: p.stem)
def test_yield_rows_match_excel(fixture_path: Path) -> None:
    for year in walk(fixture_path):
        produced = year.result.yields
        for field, rows in YIELD_GROUPS.items():
            expected = sum(float(year.expected_yields[str(r)] or 0.0) for r in rows)
            assert getattr(produced, field) == pytest.approx(expected, abs=TOLERANCE), (
                f"{fixture_path.stem}, year {year.year}, {field} "
                f"(Bio results rows {rows.start}-{rows.stop - 1})"
            )


def test_competition_costs_yield_and_is_bounded() -> None:
    """Bio results!D38:D41 -- more ryegrass keeps less, but never below the floor.

    ``max_yield_loss`` is what bounds it: wheat can lose at most 60% to ryegrass
    however thick the stand, which is why the curve flattens rather than falling
    to zero.
    """
    clean = retained_fraction(0, 121.6, 0.0)
    heavy = retained_fraction(0, 121.6, 1000.0)
    floor = 1.0 - load_parameters()["yield_parameters"]["max_yield_loss"]["0"]

    assert clean > heavy
    assert heavy >= floor - 1e-9


def test_the_retained_fraction_is_capped_downstream_not_in_the_formula() -> None:
    """D38:D41 can exceed 1; D42:D45 caps it with IF(D38>1,1,D38).

    A weed-free paddock scores slightly over 1.0, which would otherwise hand the
    crop more than its weed-free yield.
    """
    from rim.yield_model import compute_yield

    raw = retained_fraction(0, 121.6, 0.0)
    result = compute_yield({}, crop_code=0, phase_code=0, weed_free_from_table8=1.8,
                           ryegrass_early_spring=0.0, herbicide_applications=0)

    assert raw > 1.0
    assert result.grain_yield == pytest.approx(result.weed_free_yield)


def test_a_denser_crop_keeps_more_of_its_yield() -> None:
    """The mechanism behind the high seeding rate option."""
    parameters = load_parameters()
    standard = parameters["yield_parameters"]["plant_density_standard"]["0"]
    high = parameters["yield_parameters"]["plant_density_high"]["0"]

    assert retained_fraction(0, high, 200.0) > retained_fraction(0, standard, 200.0)


def test_the_mouldboard_benefit_is_permanent() -> None:
    """Bio results!D27 widens its COUNTIF range each year, so it never lapses."""
    ploughed_now = management_adjustment(
        {17: 0}, crop_code=0, phase_code=0, herbicide_applications=0)
    ploughed_before = management_adjustment(
        {}, crop_code=0, phase_code=0, herbicide_applications=0, mouldboard_ever=True)
    never = management_adjustment(
        {}, crop_code=0, phase_code=0, herbicide_applications=0)

    assert ploughed_now == pytest.approx(ploughed_before)
    assert ploughed_before > never


def test_every_spray_costs_yield() -> None:
    """Bio results!D23 -- phytotoxicity scales with the number of applications."""
    none = management_adjustment({}, crop_code=0, phase_code=0, herbicide_applications=0)
    two = management_adjustment({}, crop_code=0, phase_code=0, herbicide_applications=2)
    per_spray = load_parameters()["yield_parameters"]["phytotoxicity_per_spray"]["3"]

    assert none - two == pytest.approx(2 * per_spray)


def test_a_sacrificed_crop_yields_no_grain() -> None:
    """Bio results!D42:D45 zero out when any spring option was taken."""
    from rim.yield_model import compute_yield

    kept = compute_yield({}, crop_code=0, phase_code=0, weed_free_from_table8=1.8,
                         ryegrass_early_spring=5.0, herbicide_applications=0)
    manured = compute_yield({34: 0}, crop_code=0, phase_code=0,
                            weed_free_from_table8=1.8, ryegrass_early_spring=5.0,
                            herbicide_applications=0)

    assert kept.grain_yield > 0
    assert manured.grain_yield == 0.0


def test_workbook_defects_are_recorded() -> None:
    """Both D29 defects are reproduced deliberately, so they must stay documented."""
    assert len(WORKBOOK_DEFECTS) == 2
    assert any("#REF!" in note for note in WORKBOOK_DEFECTS)


def test_parameters_are_generated_with_provenance() -> None:
    payload = json.loads((Path(__file__).resolve().parents[1]
                          / "data" / "economics.json").read_text(encoding="utf-8"))

    assert payload["_source"]["generated_by"] == "tools/extract_params.py"
    assert payload["mouldboard_yield_benefit"] > 0
